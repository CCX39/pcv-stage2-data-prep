#!/usr/bin/env python3
"""Independently validate frame 1051 PDL=1.0 binary PLY pilot tiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
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
EXPECTED_NON_EMPTY_1051 = 40
EXPECTED_EMPTY_1051 = 88


class PilotValidationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_ascii_header(path: Path) -> Dict[str, object]:
    comments: List[str] = []
    vertex_count = None
    properties: List[Tuple[str, str]] = []
    fmt = None
    in_vertex = False
    saw_vertex = False

    with path.open("r", encoding="utf-8", newline="") as f:
        first = f.readline()
        if first.strip() != "ply":
            raise PilotValidationError(f"Not a PLY file: {path}")
        for line_number, raw_line in enumerate(f, start=2):
            line = raw_line.rstrip("\r\n")
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "format":
                fmt = " ".join(parts[1:])
            elif parts[0] == "comment":
                comments.append(line)
            elif parts[0] == "element":
                if len(parts) != 3 or parts[1] != "vertex":
                    raise PilotValidationError(f"Unsupported element line in {path}: {line}")
                if saw_vertex:
                    raise PilotValidationError(f"Duplicate vertex element in {path}")
                vertex_count = int(parts[2])
                in_vertex = True
                saw_vertex = True
            elif parts[0] == "property":
                if not in_vertex or len(parts) != 3:
                    raise PilotValidationError(f"Unsupported property line in {path}: {line}")
                properties.append((parts[1], parts[2]))
            elif parts[0] == "end_header":
                if fmt != "ascii 1.0":
                    raise PilotValidationError(f"Unsupported source PLY format: {fmt}")
                if vertex_count is None:
                    raise PilotValidationError("Missing source vertex count")
                if properties != EXPECTED_VERTEX_PROPERTIES:
                    raise PilotValidationError(f"Unexpected source schema: {properties}")
                return {
                    "format": fmt,
                    "vertex_count": vertex_count,
                    "properties": properties,
                    "comments": comments,
                    "data_start_line": line_number + 1,
                }
    raise PilotValidationError(f"Missing source end_header: {path}")


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
                    raise PilotValidationError(f"Extra source data at line {line_number}")
                continue
            parts = raw_line.split()
            if len(parts) != 6:
                raise PilotValidationError(f"Malformed source vertex record at line {line_number}")
            try:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                red, green, blue = int(parts[3]), int(parts[4]), int(parts[5])
            except ValueError as exc:
                raise PilotValidationError(f"Unparseable source vertex at line {line_number}") from exc
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                raise PilotValidationError(f"Non-finite source coordinate at line {line_number}")
            if not all(0 <= c <= 255 for c in (red, green, blue)):
                raise PilotValidationError(f"Invalid source RGB at line {line_number}")
            parsed += 1
            yield x, y, z, red, green, blue
        if parsed != vertex_count:
            raise PilotValidationError(f"Parsed {parsed} source vertices, expected {vertex_count}")


def load_profile(path: Path) -> Dict[str, object]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    dims = profile["grid_dimensions"]
    if (int(dims["nx"]), int(dims["ny"]), int(dims["nz"])) != (4, 8, 4):
        raise PilotValidationError("Expected G128 dimensions 4 x 8 x 4")
    if int(profile["theoretical_cell_count"]) != 128:
        raise PilotValidationError("Expected theoretical_cell_count = 128")
    return profile


def tile_id(ix: int, iy: int, iz: int) -> str:
    return f"gx_{ix}_gy_{iy}_gz_{iz}"


def all_tile_ids(profile: Dict[str, object]) -> List[str]:
    dims = profile["grid_dimensions"]
    return [
        tile_id(ix, iy, iz)
        for ix in range(int(dims["nx"]))
        for iy in range(int(dims["ny"]))
        for iz in range(int(dims["nz"]))
    ]


def assign_axis(value: float, origin: float, max_value: float, cell_size: float, n: int, axis_name: str) -> int:
    if value < origin or value > max_value:
        raise PilotValidationError(f"{axis_name} coordinate {value} outside grid [{origin}, {max_value}]")
    if value == max_value:
        return n - 1
    idx = int(math.floor((value - origin) / cell_size))
    if idx < 0 or idx >= n:
        raise PilotValidationError(f"{axis_name} coordinate {value} produced invalid cell index {idx}")
    return idx


def assign_tile(point: Sequence[float], profile: Dict[str, object]) -> Tuple[int, int, int, str]:
    origin = [float(v) for v in profile["grid_origin"]]
    grid_max = [float(v) for v in profile["grid_max"]]
    cell = [float(v) for v in profile["cell_size"]]
    dims = profile["grid_dimensions"]
    ix = assign_axis(float(point[0]), origin[0], grid_max[0], cell[0], int(dims["nx"]), "x")
    iy = assign_axis(float(point[1]), origin[1], grid_max[1], cell[1], int(dims["ny"]), "y")
    iz = assign_axis(float(point[2]), origin[2], grid_max[2], cell[2], int(dims["nz"]), "z")
    return ix, iy, iz, tile_id(ix, iy, iz)


def parse_binary_header(path: Path) -> Tuple[int, int]:
    header_bytes = bytearray()
    with path.open("rb") as f:
        while True:
            b = f.read(1)
            if not b:
                raise PilotValidationError(f"Missing binary PLY end_header: {path}")
            header_bytes.extend(b)
            if header_bytes.endswith(b"end_header\n"):
                break
    try:
        header_text = header_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise PilotValidationError(f"Non-ASCII binary PLY header: {path}") from exc
    lines = [line.strip("\r") for line in header_text.split("\n") if line.strip("\r") != ""]
    if not lines or lines[0] != "ply":
        raise PilotValidationError(f"Invalid binary PLY magic: {path}")
    fmt = None
    vertex_count = None
    properties: List[Tuple[str, str]] = []
    in_vertex = False
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = " ".join(parts[1:])
        elif parts[0] == "element":
            if len(parts) != 3 or parts[1] != "vertex":
                raise PilotValidationError(f"Unsupported binary PLY element in {path}: {line}")
            vertex_count = int(parts[2])
            in_vertex = True
        elif parts[0] == "property":
            if not in_vertex or len(parts) != 3:
                raise PilotValidationError(f"Unsupported binary property in {path}: {line}")
            properties.append((parts[1], parts[2]))
        elif parts[0] in {"comment", "end_header"}:
            continue
    if fmt != "binary_little_endian 1.0":
        raise PilotValidationError(f"Expected binary_little_endian 1.0 in {path}, got {fmt}")
    if vertex_count is None:
        raise PilotValidationError(f"Missing binary PLY vertex count: {path}")
    if properties != EXPECTED_VERTEX_PROPERTIES:
        raise PilotValidationError(f"Unexpected binary PLY schema in {path}: {properties}")
    return vertex_count, len(header_bytes)


def validate_binary_tile(path: Path, expected_count: int, expected_tile_id: str, profile: Dict[str, object]) -> str:
    vertex_count, data_offset = parse_binary_header(path)
    if vertex_count != expected_count:
        raise PilotValidationError(f"{path} declares {vertex_count}, tile index expects {expected_count}")
    h = hashlib.sha256()
    parsed = 0
    with path.open("rb") as f:
        f.seek(data_offset)
        while parsed < vertex_count:
            rec = f.read(CANONICAL_STRUCT.size)
            if len(rec) != CANONICAL_STRUCT.size:
                raise PilotValidationError(f"Short binary point record in {path}")
            x, y, z, red, green, blue = CANONICAL_STRUCT.unpack(rec)
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                raise PilotValidationError(f"Non-finite output coordinate in {path}")
            if not all(0 <= c <= 255 for c in (red, green, blue)):
                raise PilotValidationError(f"Invalid output RGB in {path}")
            _, _, _, actual_tile_id = assign_tile((x, y, z), profile)
            if actual_tile_id != expected_tile_id:
                raise PilotValidationError(f"Point in {path} assigned to {actual_tile_id}, expected {expected_tile_id}")
            h.update(rec)
            parsed += 1
        trailing = f.read(1)
        if trailing:
            raise PilotValidationError(f"Unexpected trailing bytes in {path}")
    return h.hexdigest()


def run(args: argparse.Namespace) -> Dict[str, object]:
    raw_root = Path(args.raw_root)
    frame_id = int(args.frame_id)
    source_file = raw_root / f"longdress_vox10_{frame_id}.ply"
    profile_path = Path(args.grid_profile)
    artifact_dir = Path(args.artifact_dir)
    if not source_file.is_file():
        raise PilotValidationError(f"Source file missing: {source_file}")
    if not artifact_dir.is_dir():
        raise PilotValidationError(f"Artifact directory missing: {artifact_dir}")

    profile = load_profile(profile_path)
    tile_ids = all_tile_ids(profile)
    source_header = parse_ascii_header(source_file)
    source_counts = {tid: 0 for tid in tile_ids}
    source_hashes = {tid: hashlib.sha256() for tid in tile_ids}
    parsed = 0
    for point in iter_ascii_points(source_file, source_header):
        _, _, _, tid = assign_tile(point[:3], profile)
        source_counts[tid] += 1
        source_hashes[tid].update(CANONICAL_STRUCT.pack(*point))
        parsed += 1
    if parsed != int(source_header["vertex_count"]):
        raise PilotValidationError("Source parsed count mismatch")

    tile_index_path = artifact_dir / f"frame_{frame_id}_tile_index.json"
    manifest_path = artifact_dir / "generation_manifest.json"
    if not tile_index_path.is_file():
        raise PilotValidationError(f"Missing tile index: {tile_index_path}")
    if not manifest_path.is_file():
        raise PilotValidationError(f"Missing generation manifest: {manifest_path}")
    tile_index = json.loads(tile_index_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tiles = tile_index.get("tiles", [])
    if len(tiles) != 128:
        raise PilotValidationError(f"Expected 128 tile records, got {len(tiles)}")

    index_counts = {record["tile_id"]: int(record["point_count"]) for record in tiles}
    if set(index_counts) != set(tile_ids):
        raise PilotValidationError("Tile index does not contain the expected G128 tile id universe")
    if index_counts != source_counts:
        raise PilotValidationError("Tile index counts differ from independently computed source counts")
    if sum(index_counts.values()) != parsed:
        raise PilotValidationError("Tile index point counts do not sum to source count")

    non_empty = sum(1 for count in index_counts.values() if count > 0)
    empty = len(tile_ids) - non_empty
    if non_empty != EXPECTED_NON_EMPTY_1051 or empty != EXPECTED_EMPTY_1051:
        raise PilotValidationError(f"Expected 40 non-empty / 88 empty tiles, got {non_empty}/{empty}")

    output_total = 0
    output_hashes: Dict[str, str] = {}
    binary_little_endian_files = 0
    for record in tiles:
        tid = record["tile_id"]
        count = int(record["point_count"])
        relpath = record["pdl_1_0_ply_relpath"]
        if count == 0:
            if not record["is_empty"]:
                raise PilotValidationError(f"Empty tile not marked is_empty: {tid}")
            if record["asset_status"] != "not_generated_empty":
                raise PilotValidationError(f"Unexpected empty tile status for {tid}")
            tile_dir = artifact_dir / "tiles" / tid
            if tile_dir.exists() and any(tile_dir.glob("*.ply")):
                raise PilotValidationError(f"Empty tile has PLY file(s): {tid}")
            if relpath is not None:
                raise PilotValidationError(f"Empty tile has non-null relpath: {tid}")
            continue
        if record["is_empty"]:
            raise PilotValidationError(f"Non-empty tile marked empty: {tid}")
        if record["asset_status"] != "generated_pdl_1_0":
            raise PilotValidationError(f"Unexpected non-empty tile status for {tid}")
        if not relpath:
            raise PilotValidationError(f"Non-empty tile missing relpath: {tid}")
        ply_path = artifact_dir / relpath
        if not ply_path.is_file():
            raise PilotValidationError(f"Non-empty tile PLY missing: {ply_path}")
        output_digest = validate_binary_tile(ply_path, count, tid, profile)
        binary_little_endian_files += 1
        output_total += count
        output_hashes[tid] = output_digest
        if sha256_file(ply_path) != record["pdl_1_0_ply_sha256"]:
            raise PilotValidationError(f"File sha256 mismatch for {tid}")
        if ply_path.stat().st_size != int(record["pdl_1_0_ply_file_size_bytes"]):
            raise PilotValidationError(f"File size mismatch for {tid}")
        if output_digest != source_hashes[tid].hexdigest():
            raise PilotValidationError(f"Canonical digest mismatch for {tid}")

    if output_total != parsed:
        raise PilotValidationError("Output binary PLY vertex sum does not match source point count")
    if int(manifest["source_vertex_count"]) != parsed:
        raise PilotValidationError("Manifest source_vertex_count mismatch")
    if int(manifest["total_output_point_count"]) != parsed:
        raise PilotValidationError("Manifest total_output_point_count mismatch")

    report = {
        "passed": True,
        "frame_id": frame_id,
        "source_file_name": source_file.name,
        "source_vertex_count": parsed,
        "tile_count": len(tile_ids),
        "non_empty_tile_count": non_empty,
        "empty_tile_count": empty,
        "generated_binary_ply_file_count": binary_little_endian_files,
        "pdl": 1.0,
        "checks": {
            "source_header_count_equals_parsed_count": True,
            "source_count_equals_tile_index_sum": True,
            "source_count_equals_binary_ply_vertex_sum": True,
            "non_empty_plus_empty_equals_128": True,
            "expected_frame_1051_non_empty_count_40": True,
            "expected_frame_1051_empty_count_88": True,
            "non_empty_tiles_have_one_ply": True,
            "empty_tiles_have_no_ply": True,
            "all_output_ply_binary_little_endian": True,
            "output_schema_matches_contract": True,
            "all_output_points_within_tile_bounds": True,
            "source_output_canonical_record_digest_match": True,
        },
        "canonical_record_format": "<fffBBB",
    }
    write_json(artifact_dir / "validation_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--frame-id", required=True, type=int)
    parser.add_argument("--grid-profile", required=True)
    parser.add_argument("--artifact-dir", required=True)
    return parser.parse_args()


def main() -> int:
    try:
        report = run(parse_args())
    except PilotValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "ok",
        "source_vertex_count": report["source_vertex_count"],
        "non_empty_tile_count": report["non_empty_tile_count"],
        "empty_tile_count": report["empty_tile_count"],
        "generated_binary_ply_file_count": report["generated_binary_ply_file_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
