#!/usr/bin/env python3
"""Read-only raw-coordinate grid probe for selected Longdress PLY frames."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Iterable


GRID_PROFILES = {
    "G54": (3, 6, 3),
    "G128": (4, 8, 4),
}


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def parse_frame_ids(value: str) -> list[int]:
    parts: list[str] = []
    for chunk in value.replace(";", ",").split(","):
        parts.extend(chunk.split())
    try:
        frame_ids = [int(part) for part in parts if part]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid frame id list: {value}") from exc
    if not frame_ids:
        raise argparse.ArgumentTypeError("at least one frame id is required")
    return frame_ids


def ply_path(raw_root: Path, frame_id: int) -> Path:
    return raw_root / f"longdress_vox10_{frame_id}.ply"


def parse_ply_frame(path: Path, store_points: bool) -> dict:
    if not path.is_file():
        raise RuntimeError(f"missing input PLY: {path}")

    header_lines: list[str] = []
    with path.open("r", encoding="ascii", errors="strict", newline="") as handle:
        while True:
            line = handle.readline()
            if line == "":
                raise RuntimeError(f"unexpected EOF before end_header: {path}")
            stripped = line.rstrip("\r\n")
            header_lines.append(stripped)
            if stripped == "end_header":
                break
            if len(header_lines) > 200:
                raise RuntimeError(f"header too long or malformed: {path}")

        header = parse_header(header_lines, path)
        property_count = len(header["vertex_properties"])
        x_index = header["vertex_properties"].index("x")
        y_index = header["vertex_properties"].index("y")
        z_index = header["vertex_properties"].index("z")
        vertex_count = header["vertex_count"]

        mins = [math.inf, math.inf, math.inf]
        maxs = [-math.inf, -math.inf, -math.inf]
        points: list[tuple[float, float, float]] = []
        parsed_count = 0

        for row_idx in range(vertex_count):
            line = handle.readline()
            if line == "":
                raise RuntimeError(
                    f"unexpected EOF in vertex data at row {row_idx}: {path}"
                )
            parts = line.split()
            if len(parts) != property_count:
                raise RuntimeError(
                    f"vertex row {row_idx} has {len(parts)} fields; expected {property_count}: {path}"
                )
            try:
                x = float(parts[x_index])
                y = float(parts[y_index])
                z = float(parts[z_index])
            except ValueError as exc:
                raise RuntimeError(f"non-numeric xyz at row {row_idx}: {path}") from exc

            coords = (x, y, z)
            for axis, value in enumerate(coords):
                if value < mins[axis]:
                    mins[axis] = value
                if value > maxs[axis]:
                    maxs[axis] = value
            if store_points:
                points.append(coords)
            parsed_count += 1

        trailing = handle.readline()
        if trailing != "":
            raise RuntimeError(f"extra data after declared vertex count: {path}")

    if parsed_count != vertex_count:
        raise RuntimeError(
            f"parsed point count {parsed_count} != header vertex count {vertex_count}: {path}"
        )

    bbox_center = [(mins[i] + maxs[i]) / 2.0 for i in range(3)]
    bbox_extent = [maxs[i] - mins[i] for i in range(3)]
    return {
        "source_file": str(path),
        "source_file_name": path.name,
        "ply_format": header["format"],
        "vertex_count": vertex_count,
        "parsed_point_count": parsed_count,
        "xyz_property_names": ["x", "y", "z"],
        "vertex_properties": header["vertex_properties"],
        "comments": header["comments"],
        "obj_info": header["obj_info"],
        "frame_to_world_scale": header["comments_kv"].get("frame_to_world_scale"),
        "frame_to_world_translation": header["comments_kv"].get(
            "frame_to_world_translation"
        ),
        "bbox_min": mins,
        "bbox_max": maxs,
        "bbox_center": bbox_center,
        "bbox_extent": bbox_extent,
        "points": points,
    }


def parse_header(header_lines: list[str], path: Path) -> dict:
    if not header_lines or header_lines[0] != "ply":
        raise RuntimeError(f"not a PLY file: {path}")

    fmt = None
    vertex_count = None
    vertex_properties: list[str] = []
    comments: list[str] = []
    obj_info: list[str] = []
    current_element = None

    for line in header_lines[1:]:
        if line == "end_header":
            break
        if line.startswith("format "):
            fmt = line
        elif line.startswith("comment "):
            comments.append(line[len("comment ") :])
        elif line.startswith("obj_info "):
            obj_info.append(line[len("obj_info ") :])
        elif line.startswith("element "):
            pieces = line.split()
            if len(pieces) != 3:
                raise RuntimeError(f"malformed element line in {path}: {line}")
            current_element = pieces[1]
            if current_element == "vertex":
                try:
                    vertex_count = int(pieces[2])
                except ValueError as exc:
                    raise RuntimeError(f"invalid vertex count in {path}: {line}") from exc
            else:
                raise RuntimeError(
                    f"unsupported PLY element {current_element!r}; only vertex is supported: {path}"
                )
        elif line.startswith("property "):
            if current_element != "vertex":
                raise RuntimeError(
                    f"property outside supported vertex element in {path}: {line}"
                )
            pieces = line.split()
            if len(pieces) != 3:
                raise RuntimeError(f"unsupported property syntax in {path}: {line}")
            vertex_properties.append(pieces[2])

    if fmt != "format ascii 1.0":
        raise RuntimeError(f"unsupported PLY format {fmt!r}; expected ascii 1.0: {path}")
    if vertex_count is None:
        raise RuntimeError(f"missing vertex element: {path}")
    for required in ("x", "y", "z"):
        if required not in vertex_properties:
            raise RuntimeError(f"missing required vertex property {required}: {path}")

    comments_kv = {}
    for comment in comments:
        if comment.startswith("frame_to_world_scale "):
            comments_kv["frame_to_world_scale"] = comment.split(" ", 1)[1]
        elif comment.startswith("frame_to_world_translation "):
            comments_kv["frame_to_world_translation"] = comment.split(" ", 1)[1]

    return {
        "format": fmt,
        "vertex_count": vertex_count,
        "vertex_properties": vertex_properties,
        "comments": comments,
        "obj_info": obj_info,
        "comments_kv": comments_kv,
    }


def percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * pct
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return float(sorted_values[low])
    weight = pos - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def assign_axis(value: float, axis_min: float, axis_max: float, bins: int) -> int:
    if axis_max <= axis_min:
        raise RuntimeError("invalid envelope extent")
    tolerance = max(abs(axis_min), abs(axis_max), 1.0) * 1e-12
    if value < axis_min - tolerance or value > axis_max + tolerance:
        raise RuntimeError(
            f"point value {value} outside provisional envelope [{axis_min}, {axis_max}]"
        )
    if value >= axis_max:
        return bins - 1
    idx = int(math.floor(((value - axis_min) / (axis_max - axis_min)) * bins))
    if idx < 0:
        return 0
    if idx >= bins:
        return bins - 1
    return idx


def probe_grid(
    points: Iterable[tuple[float, float, float]],
    envelope_min: list[float],
    envelope_max: list[float],
    dims: tuple[int, int, int],
    expected_total: int,
) -> dict:
    nx, ny, nz = dims
    theoretical = nx * ny * nz
    counts = [0] * theoretical
    assigned = 0

    for x, y, z in points:
        ix = assign_axis(x, envelope_min[0], envelope_max[0], nx)
        iy = assign_axis(y, envelope_min[1], envelope_max[1], ny)
        iz = assign_axis(z, envelope_min[2], envelope_max[2], nz)
        linear = ix * ny * nz + iy * nz + iz
        counts[linear] += 1
        assigned += 1

    total = expected_total
    non_empty = [count for count in counts if count > 0]
    empty_count = theoretical - len(non_empty)
    descending = sorted(
        (
            {
                "tile_id": tile_id_from_linear(linear, dims),
                "linear_index": linear,
                "point_count": count,
                "point_share": count / total if total else 0.0,
            }
            for linear, count in enumerate(counts)
        ),
        key=lambda row: (-row["point_count"], row["linear_index"]),
    )

    invariants = {
        "assigned_point_count": assigned,
        "expected_point_count": expected_total,
        "tile_point_count_sum": sum(counts),
        "every_point_assigned_once": assigned == expected_total
        and sum(counts) == expected_total,
        "tile_sum_equals_pilot_total": sum(counts) == expected_total,
        "non_empty_plus_empty_equals_theoretical": len(non_empty) + empty_count
        == theoretical,
    }
    return {
        "dims": {"nx": nx, "ny": ny, "nz": nz},
        "theoretical_cell_count": theoretical,
        "total_point_count": total,
        "non_empty_tile_count": len(non_empty),
        "empty_tile_count": empty_count,
        "minimum_non_empty_tile_point_count": min(non_empty) if non_empty else 0,
        "p10_non_empty_tile_point_count": percentile(non_empty, 0.10),
        "median_non_empty_tile_point_count": percentile(non_empty, 0.50),
        "p90_non_empty_tile_point_count": percentile(non_empty, 0.90),
        "maximum_non_empty_tile_point_count": max(non_empty) if non_empty else 0,
        "maximum_tile_point_share": (max(counts) / total) if total else 0.0,
        "minimum_tile_point_share_all_cells": (min(counts) / total) if total else 0.0,
        "minimum_non_empty_tile_point_share": (min(non_empty) / total)
        if non_empty and total
        else 0.0,
        "tile_counts_descending": descending,
        "invariants": invariants,
    }


def tile_id_from_linear(linear: int, dims: tuple[int, int, int]) -> str:
    _nx, ny, nz = dims
    ix = linear // (ny * nz)
    iy = (linear // nz) % ny
    iz = linear % nz
    return f"gx_{ix}_gy_{iy}_gz_{iz}"


def write_outputs(output_dir: Path, payload: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "config_snapshot.json").write_text(
        json.dumps(payload["config"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "grid_stats.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with (output_dir / "frame_bbox.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "frame_id",
                "source_file_name",
                "ply_format",
                "vertex_count",
                "parsed_point_count",
                "x_min",
                "y_min",
                "z_min",
                "x_max",
                "y_max",
                "z_max",
                "x_center",
                "y_center",
                "z_center",
                "x_extent",
                "y_extent",
                "z_extent",
                "frame_to_world_scale",
                "frame_to_world_translation",
            ]
        )
        for frame in payload["frames"]:
            writer.writerow(
                [
                    frame["frame_id"],
                    frame["source_file_name"],
                    frame["ply_format"],
                    frame["vertex_count"],
                    frame["parsed_point_count"],
                    *frame["bbox_min"],
                    *frame["bbox_max"],
                    *frame["bbox_center"],
                    *frame["bbox_extent"],
                    frame.get("frame_to_world_scale") or "not_observed",
                    frame.get("frame_to_world_translation") or "not_observed",
                ]
            )

    for profile_name, stats in payload["grid_profiles"].items():
        with (output_dir / f"tile_counts_{profile_name}.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["tile_id", "linear_index", "point_count", "point_share"])
            for row in stats["tile_counts_descending"]:
                writer.writerow(
                    [
                        row["tile_id"],
                        row["linear_index"],
                        row["point_count"],
                        f"{row['point_share']:.12f}",
                    ]
                )

    lines = ["Grid probe invariant checks"]
    for frame in payload["frames"]:
        ok = frame["vertex_count"] == frame["parsed_point_count"]
        lines.append(
            f"frame {frame['frame_id']}: parsed_point_count == header vertex_count -> {ok}"
        )
    for profile_name, stats in payload["grid_profiles"].items():
        for key, value in stats["invariants"].items():
            lines.append(f"{profile_name}: {key} -> {value}")
    (output_dir / "invariants.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--frame-ids", required=True, type=parse_frame_ids)
    parser.add_argument("--pilot-frame-id", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    raw_root = Path(args.raw_root)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    output_dir = output_dir.resolve()
    allowed_output_root = (Path.cwd() / "outputs" / "grid_probe").resolve()
    if not raw_root.is_dir():
        raise RuntimeError(f"--raw-root is not a directory: {raw_root}")
    if output_dir != allowed_output_root and not is_relative_to(
        output_dir, allowed_output_root
    ):
        raise RuntimeError(
            "--output-dir must be inside this repository's outputs/grid_probe"
        )
    if args.pilot_frame_id not in args.frame_ids:
        raise RuntimeError("--pilot-frame-id must be included in --frame-ids")

    frames = []
    pilot_points: list[tuple[float, float, float]] | None = None
    for frame_id in args.frame_ids:
        frame = parse_ply_frame(
            ply_path(raw_root, frame_id), store_points=(frame_id == args.pilot_frame_id)
        )
        frame["frame_id"] = frame_id
        if frame_id == args.pilot_frame_id:
            pilot_points = frame.pop("points")
        else:
            frame.pop("points")
        frames.append(frame)

    if pilot_points is None:
        raise RuntimeError("pilot frame was not parsed")

    envelope_min = [min(frame["bbox_min"][axis] for frame in frames) for axis in range(3)]
    envelope_max = [max(frame["bbox_max"][axis] for frame in frames) for axis in range(3)]
    envelope_center = [
        (envelope_min[axis] + envelope_max[axis]) / 2.0 for axis in range(3)
    ]
    envelope_extent = [envelope_max[axis] - envelope_min[axis] for axis in range(3)]

    if any(extent <= 0 for extent in envelope_extent):
        raise RuntimeError(f"invalid provisional envelope extent: {envelope_extent}")

    grid_profiles = {}
    for name, dims in GRID_PROFILES.items():
        total = len(pilot_points)
        grid_profiles[name] = probe_grid(
            pilot_points, envelope_min, envelope_max, dims, total
        )
        checks = grid_profiles[name]["invariants"]
        if not all(
            value
            for key, value in checks.items()
            if key
            not in {
                "assigned_point_count",
                "expected_point_count",
                "tile_point_count_sum",
            }
        ):
            raise RuntimeError(f"invariant failure for {name}: {checks}")

    payload = {
        "config": {
            "raw_root": str(raw_root),
            "frame_ids": args.frame_ids,
            "pilot_frame_id": args.pilot_frame_id,
            "output_dir": str(output_dir),
            "grid_profiles": {
                name: {"nx": dims[0], "ny": dims[1], "nz": dims[2]}
                for name, dims in GRID_PROFILES.items()
            },
            "boundary_rule": "[min, max) per axis; points on max boundary assigned to final cell",
            "temporary_tile_id_format": "gx_<ix>_gy_<iy>_gz_<iz>",
        },
        "frames": frames,
        "provisional_envelope": {
            "definition": "union of raw-coordinate bbox over scanned frames only",
            "bbox_min": envelope_min,
            "bbox_max": envelope_max,
            "bbox_center": envelope_center,
            "bbox_extent": envelope_extent,
        },
        "grid_profiles": grid_profiles,
    }
    write_outputs(output_dir, payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
