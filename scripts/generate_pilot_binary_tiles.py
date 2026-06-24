#!/usr/bin/env python3
"""Generate frame 1051 PDL=1.0 binary PLY pilot tiles.

This script is intentionally narrow: it supports the observed Longdress ASCII
PLY schema and writes only non-empty PDL=1.0 binary little-endian tile PLY files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


EXPECTED_VERTEX_PROPERTIES: List[Tuple[str, str]] = [
    ("float", "x"),
    ("float", "y"),
    ("float", "z"),
    ("uchar", "red"),
    ("uchar", "green"),
    ("uchar", "blue"),
]
CANONICAL_STRUCT = struct.Struct("<fffBBB")


class PilotGenerationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_ply_header(path: Path) -> Dict[str, object]:
    comments: List[str] = []
    vertex_count = None
    properties: List[Tuple[str, str]] = []
    fmt = None
    in_vertex = False
    saw_vertex = False
    header_lines: List[str] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        first = f.readline()
        if first == "":
            raise PilotGenerationError(f"Empty PLY file: {path}")
        if first.strip() != "ply":
            raise PilotGenerationError(f"Not a PLY file: {path}")
        header_lines.append(first.rstrip("\r\n"))

        for line_number, raw_line in enumerate(f, start=2):
            line = raw_line.rstrip("\r\n")
            header_lines.append(line)
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "format":
                fmt = " ".join(parts[1:])
            elif parts[0] == "comment":
                comments.append(line)
            elif parts[0] == "element":
                if len(parts) != 3:
                    raise PilotGenerationError(f"Malformed element line {line_number}: {line}")
                if parts[1] != "vertex":
                    raise PilotGenerationError(f"Unsupported PLY element '{parts[1]}' in {path}")
                if saw_vertex:
                    raise PilotGenerationError(f"Duplicate element vertex in {path}")
                vertex_count = int(parts[2])
                in_vertex = True
                saw_vertex = True
            elif parts[0] == "property":
                if not in_vertex:
                    raise PilotGenerationError(f"Property outside vertex element in {path}: {line}")
                if len(parts) != 3:
                    raise PilotGenerationError(f"Unsupported property declaration in {path}: {line}")
                properties.append((parts[1], parts[2]))
            elif parts[0] == "end_header":
                if fmt != "ascii 1.0":
                    raise PilotGenerationError(f"Unsupported PLY format in {path}: {fmt}")
                if vertex_count is None:
                    raise PilotGenerationError(f"Missing element vertex in {path}")
                if properties != EXPECTED_VERTEX_PROPERTIES:
                    raise PilotGenerationError(
                        f"Unsupported vertex schema in {path}: {properties}; expected {EXPECTED_VERTEX_PROPERTIES}"
                    )
                return {
                    "format": fmt,
                    "vertex_count": vertex_count,
                    "properties": properties,
                    "comments": comments,
                    "header_lines": header_lines,
                    "data_start_line": line_number + 1,
                }

    raise PilotGenerationError(f"Missing end_header in {path}")


def iter_ascii_points(path: Path, header: Dict[str, object]) -> Iterable[Tuple[float, float, float, int, int, int]]:
    vertex_count = int(header["vertex_count"])
    with path.open("r", encoding="utf-8", newline="") as f:
        for raw_line in f:
            if raw_line.rstrip("\r\n") == "end_header":
                break
        parsed = 0
        for line_number, raw_line in enumerate(f, start=int(header["data_start_line"])):
            if parsed >= vertex_count:
                if raw_line.strip():
                    raise PilotGenerationError(f"Extra non-empty data after vertex records at line {line_number}")
                continue
            parts = raw_line.split()
            if len(parts) != 6:
                raise PilotGenerationError(f"Malformed vertex record at line {line_number}: expected 6 fields")
            try:
                x, y, z = (float(parts[0]), float(parts[1]), float(parts[2]))
                red, green, blue = (int(parts[3]), int(parts[4]), int(parts[5]))
            except ValueError as exc:
                raise PilotGenerationError(f"Unparseable vertex record at line {line_number}") from exc
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                raise PilotGenerationError(f"Non-finite coordinate at line {line_number}")
            if not all(0 <= c <= 255 for c in (red, green, blue)):
                raise PilotGenerationError(f"Invalid RGB value at line {line_number}")
            parsed += 1
            yield x, y, z, red, green, blue
        if parsed != vertex_count:
            raise PilotGenerationError(f"Parsed {parsed} vertices, header declares {vertex_count}")


def load_grid_profile(path: Path) -> Dict[str, object]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    dims = profile.get("grid_dimensions", {})
    if (dims.get("nx"), dims.get("ny"), dims.get("nz")) != (4, 8, 4):
        raise PilotGenerationError(f"Unexpected grid dimensions in {path}: {dims}")
    if int(profile.get("theoretical_cell_count")) != 128:
        raise PilotGenerationError("Expected theoretical_cell_count = 128")
    if float(profile.get("pdl_baseline")) != 1.0:
        raise PilotGenerationError("Expected pdl_baseline = 1.0")
    return profile


def all_tile_ids(profile: Dict[str, object]) -> List[str]:
    dims = profile["grid_dimensions"]
    tile_ids: List[str] = []
    for ix in range(int(dims["nx"])):
        for iy in range(int(dims["ny"])):
            for iz in range(int(dims["nz"])):
                tile_ids.append(tile_id(ix, iy, iz))
    return tile_ids


def tile_id(ix: int, iy: int, iz: int) -> str:
    return f"gx_{ix}_gy_{iy}_gz_{iz}"


def assign_axis(value: float, origin: float, max_value: float, cell_size: float, n: int, axis_name: str) -> int:
    if value < origin or value > max_value:
        raise PilotGenerationError(f"{axis_name} coordinate {value} outside grid [{origin}, {max_value}]")
    if value == max_value:
        return n - 1
    idx = int(math.floor((value - origin) / cell_size))
    if idx < 0 or idx >= n:
        raise PilotGenerationError(f"{axis_name} coordinate {value} produced invalid cell index {idx}")
    return idx


def assign_tile(point: Sequence[float], profile: Dict[str, object]) -> Tuple[int, int, int, str]:
    origin = [float(v) for v in profile["grid_origin"]]
    grid_max = [float(v) for v in profile["grid_max"]]
    cell = [float(v) for v in profile["cell_size"]]
    dims = profile["grid_dimensions"]
    nx, ny, nz = int(dims["nx"]), int(dims["ny"]), int(dims["nz"])
    ix = assign_axis(float(point[0]), origin[0], grid_max[0], cell[0], nx, "x")
    iy = assign_axis(float(point[1]), origin[1], grid_max[1], cell[1], ny, "y")
    iz = assign_axis(float(point[2]), origin[2], grid_max[2], cell[2], nz, "z")
    return ix, iy, iz, tile_id(ix, iy, iz)


def tile_bbox(profile: Dict[str, object], ix: int, iy: int, iz: int) -> Tuple[List[float], List[float]]:
    origin = [float(v) for v in profile["grid_origin"]]
    grid_max = [float(v) for v in profile["grid_max"]]
    cell = [float(v) for v in profile["cell_size"]]
    dims = profile["grid_dimensions"]
    indexes = [ix, iy, iz]
    ns = [int(dims["nx"]), int(dims["ny"]), int(dims["nz"])]
    bbox_min = [origin[a] + indexes[a] * cell[a] for a in range(3)]
    bbox_max = [
        grid_max[a] if indexes[a] == ns[a] - 1 else origin[a] + (indexes[a] + 1) * cell[a]
        for a in range(3)
    ]
    return bbox_min, bbox_max


def binary_ply_header(profile_id: str, source_frame_id: int, source_file: str, tid: str, count: int) -> bytes:
    lines = [
        "ply",
        "format binary_little_endian 1.0",
        f"comment profile_id {profile_id}",
        f"comment source_frame_id {source_frame_id}",
        f"comment source_file {source_file}",
        f"comment tile_id {tid}",
        "comment pdl 1.0",
        f"element vertex {count}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header",
        "",
    ]
    return "\n".join(lines).encode("ascii")


def publish_staging_directory(staging_dir: Path, output_dir: Path) -> None:
    last_error: Exception | None = None
    for _ in range(20):
        try:
            staging_dir.rename(output_dir)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.5)
    raise PilotGenerationError(f"Could not publish staging directory {staging_dir} to {output_dir}: {last_error}")


def build_tile_index(profile: Dict[str, object], counts: Dict[str, int], tile_files: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    dims = profile["grid_dimensions"]
    for ix in range(int(dims["nx"])):
        for iy in range(int(dims["ny"])):
            for iz in range(int(dims["nz"])):
                tid = tile_id(ix, iy, iz)
                count = counts[tid]
                bbox_min, bbox_max = tile_bbox(profile, ix, iy, iz)
                tile_file = tile_files.get(tid)
                records.append(
                    {
                        "tile_id": tid,
                        "grid_index": {"ix": ix, "iy": iy, "iz": iz},
                        "tile_bbox_min": bbox_min,
                        "tile_bbox_max": bbox_max,
                        "is_empty": count == 0,
                        "point_count": count,
                        "asset_status": "not_generated_empty" if count == 0 else "generated_pdl_1_0",
                        "pdl_1_0_ply_relpath": None if tile_file is None else tile_file["relpath"],
                        "pdl_1_0_ply_sha256": None if tile_file is None else tile_file["sha256"],
                        "pdl_1_0_ply_file_size_bytes": None if tile_file is None else tile_file["file_size_bytes"],
                    }
                )
    return records


def run(args: argparse.Namespace) -> Dict[str, object]:
    raw_root = Path(args.raw_root)
    grid_profile_path = Path(args.grid_profile)
    output_dir = Path(args.output_dir)
    source_file = raw_root / f"longdress_vox10_{args.frame_id}.ply"

    if not source_file.is_file():
        raise PilotGenerationError(f"Source file does not exist: {source_file}")
    if output_dir.exists():
        raise PilotGenerationError(f"Output directory already exists; refusing to overwrite: {output_dir}")

    profile = load_grid_profile(grid_profile_path)
    if int(profile["source_frame_id"]) != int(args.frame_id):
        raise PilotGenerationError("Grid profile source_frame_id does not match --frame-id")

    output_parent = output_dir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = output_parent / f".{output_dir.name}.staging_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
    if staging_dir.exists():
        raise PilotGenerationError(f"Staging directory already exists: {staging_dir}")
    staging_dir.mkdir(parents=True)

    source_header = parse_ply_header(source_file)
    tile_ids = all_tile_ids(profile)
    counts = {tid: 0 for tid in tile_ids}

    parsed_count = 0
    for point in iter_ascii_points(source_file, source_header):
        _, _, _, tid = assign_tile(point[:3], profile)
        counts[tid] += 1
        parsed_count += 1
    if parsed_count != int(source_header["vertex_count"]):
        raise PilotGenerationError("Parsed point count mismatch after first pass")
    if sum(counts.values()) != parsed_count:
        raise PilotGenerationError("Tile point counts do not sum to source vertex count")

    tile_files: Dict[str, Dict[str, object]] = {}
    handles = {}
    try:
        for tid in tile_ids:
            count = counts[tid]
            if count == 0:
                continue
            tile_dir = staging_dir / "tiles" / tid
            tile_dir.mkdir(parents=True, exist_ok=False)
            ply_path = tile_dir / "pdl_1.0.ply"
            f = ply_path.open("wb")
            f.write(binary_ply_header(str(profile["profile_id"]), int(args.frame_id), source_file.name, tid, count))
            handles[tid] = f

        written_counts = {tid: 0 for tid in tile_ids}
        for point in iter_ascii_points(source_file, source_header):
            _, _, _, tid = assign_tile(point[:3], profile)
            handles[tid].write(CANONICAL_STRUCT.pack(*point))
            written_counts[tid] += 1
    finally:
        for f in handles.values():
            f.close()

    if written_counts != counts:
        raise PilotGenerationError(f"Written counts do not match first pass counts: {written_counts} vs {counts}")

    for tid, count in counts.items():
        if count == 0:
            continue
        ply_path = staging_dir / "tiles" / tid / "pdl_1.0.ply"
        tile_files[tid] = {
            "relpath": str(ply_path.relative_to(staging_dir)).replace("\\", "/"),
            "sha256": sha256_file(ply_path),
            "file_size_bytes": ply_path.stat().st_size,
        }

    non_empty = sum(1 for count in counts.values() if count > 0)
    empty = len(tile_ids) - non_empty
    if non_empty + empty != int(profile["theoretical_cell_count"]):
        raise PilotGenerationError("Tile count invariant failed")

    tile_index = build_tile_index(profile, counts, tile_files)
    grid_profile_sha256 = sha256_file(grid_profile_path)
    script_path = Path(__file__).resolve()

    source_header_observations = {
        "format": source_header["format"],
        "vertex_count": source_header["vertex_count"],
        "vertex_properties": [{"type": t, "name": n} for t, n in source_header["properties"]],
        "comments": source_header["comments"],
    }

    manifest = {
        "artifact_profile_id": profile["profile_id"],
        "generation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_file_name": source_file.name,
        "source_file_sha256": sha256_file(source_file),
        "source_frame_id": int(args.frame_id),
        "source_header_observations": source_header_observations,
        "source_vertex_count": parsed_count,
        "grid_profile_path": str(grid_profile_path).replace("\\", "/"),
        "grid_profile_sha256": grid_profile_sha256,
        "coordinate_basis": profile["coordinate_basis"],
        "grid_dimensions": profile["grid_dimensions"],
        "grid_origin": profile["grid_origin"],
        "grid_max": profile["grid_max"],
        "cell_size": profile["cell_size"],
        "tile_id_format": profile["tile_id_format"],
        "boundary_rule": profile["boundary_rule"],
        "max_boundary_assignment_rule": profile["max_boundary_assignment_rule"],
        "pdl": 1.0,
        "generation_script_path": str(script_path).replace("\\", "/"),
        "generation_script_sha256": sha256_file(script_path),
        "python_version": sys.version,
        "non_empty_tile_count": non_empty,
        "empty_tile_count": empty,
        "total_tile_count": len(tile_ids),
        "total_output_point_count": sum(counts.values()),
        "output_root": str(output_dir).replace("\\", "/"),
    }
    if manifest["source_vertex_count"] != manifest["total_output_point_count"]:
        raise PilotGenerationError("Source/output point conservation invariant failed")

    write_json(staging_dir / "generation_manifest.json", manifest)
    write_json(
        staging_dir / "grid_profile_snapshot.json",
        {"grid_profile_sha256": grid_profile_sha256, "grid_profile": profile},
    )
    write_json(
        staging_dir / f"frame_{args.frame_id}_tile_index.json",
        {
            "profile_id": profile["profile_id"],
            "frame_id": int(args.frame_id),
            "tile_count": len(tile_ids),
            "non_empty_tile_count": non_empty,
            "empty_tile_count": empty,
            "tiles": tile_index,
        },
    )

    publish_staging_directory(staging_dir, output_dir)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--frame-id", required=True, type=int)
    parser.add_argument("--grid-profile", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    try:
        manifest = run(parse_args())
    except PilotGenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "ok",
        "source_vertex_count": manifest["source_vertex_count"],
        "non_empty_tile_count": manifest["non_empty_tile_count"],
        "empty_tile_count": manifest["empty_tile_count"],
        "output_root": manifest["output_root"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
