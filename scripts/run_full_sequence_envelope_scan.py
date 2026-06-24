#!/usr/bin/env python3
"""Read-only full-sequence raw-coordinate envelope and G128 occupancy scan."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Iterable, TextIO


EXPECTED_FORMAT = "format ascii 1.0"
EXPECTED_PREFIX = "longdress_vox10_"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--frame-start", required=True, type=int)
    parser.add_argument("--frame-end", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pilot-frame-id", required=True, type=int)
    parser.add_argument("--grid-nx", required=True, type=int)
    parser.add_argument("--grid-ny", required=True, type=int)
    parser.add_argument("--grid-nz", required=True, type=int)
    parser.add_argument("--progress-every", required=True, type=int)
    return parser.parse_args(argv)


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def frame_ids(start: int, end: int) -> list[int]:
    if end < start:
        raise RuntimeError("--frame-end must be >= --frame-start")
    return list(range(start, end + 1))


def ply_path(raw_root: Path, frame_id: int) -> Path:
    return raw_root / f"{EXPECTED_PREFIX}{frame_id}.ply"


def parse_header(handle: TextIO, path: Path) -> dict:
    header_lines: list[str] = []
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

    if not header_lines or header_lines[0] != "ply":
        raise RuntimeError(f"not a PLY file: {path}")

    ply_format = None
    vertex_count = None
    vertex_properties: list[dict[str, str]] = []
    comments: list[str] = []
    obj_info: list[str] = []
    current_element = None
    element_names: list[str] = []

    for line in header_lines[1:]:
        if line == "end_header":
            break
        if line.startswith("format "):
            ply_format = line
        elif line.startswith("comment "):
            comments.append(line[len("comment ") :])
        elif line.startswith("obj_info "):
            obj_info.append(line[len("obj_info ") :])
        elif line.startswith("element "):
            pieces = line.split()
            if len(pieces) != 3:
                raise RuntimeError(f"malformed element line in {path}: {line}")
            current_element = pieces[1]
            element_names.append(current_element)
            if current_element != "vertex":
                raise RuntimeError(
                    f"unsupported PLY element {current_element!r}; only vertex is supported: {path}"
                )
            try:
                vertex_count = int(pieces[2])
            except ValueError as exc:
                raise RuntimeError(f"invalid vertex count in {path}: {line}") from exc
        elif line.startswith("property "):
            if current_element != "vertex":
                raise RuntimeError(
                    f"property outside supported vertex element in {path}: {line}"
                )
            pieces = line.split()
            if len(pieces) != 3:
                raise RuntimeError(f"unsupported property syntax in {path}: {line}")
            vertex_properties.append({"type": pieces[1], "name": pieces[2]})

    if ply_format != EXPECTED_FORMAT:
        raise RuntimeError(
            f"unsupported PLY format {ply_format!r}; expected {EXPECTED_FORMAT}: {path}"
        )
    if vertex_count is None:
        raise RuntimeError(f"missing element vertex: {path}")
    if element_names != ["vertex"]:
        raise RuntimeError(f"unexpected PLY elements {element_names}: {path}")

    property_names = [prop["name"] for prop in vertex_properties]
    for required in ("x", "y", "z"):
        if required not in property_names:
            raise RuntimeError(f"missing required vertex property {required}: {path}")

    comments_kv: dict[str, str] = {}
    for comment in comments:
        if comment.startswith("frame_to_world_scale "):
            comments_kv["frame_to_world_scale"] = comment.split(" ", 1)[1]
        elif comment.startswith("frame_to_world_translation "):
            comments_kv["frame_to_world_translation"] = comment.split(" ", 1)[1]

    return {
        "header_lines": header_lines,
        "ply_format": ply_format,
        "vertex_count": vertex_count,
        "vertex_properties": vertex_properties,
        "property_names": property_names,
        "comments": comments,
        "obj_info": obj_info,
        "frame_to_world_scale": comments_kv.get("frame_to_world_scale"),
        "frame_to_world_translation": comments_kv.get("frame_to_world_translation"),
    }


def open_ply(path: Path) -> tuple[TextIO, dict]:
    if not path.is_file():
        raise RuntimeError(f"missing input PLY: {path}")
    if path.name != f"{EXPECTED_PREFIX}{path.stem.rsplit('_', 1)[-1]}.ply":
        raise RuntimeError(f"unexpected file name: {path.name}")
    handle = path.open("r", encoding="ascii", errors="strict", newline="")
    try:
        header = parse_header(handle, path)
    except Exception:
        handle.close()
        raise
    return handle, header


def scan_frame_bbox(path: Path, frame_id: int) -> dict:
    handle, header = open_ply(path)
    try:
        property_names = header["property_names"]
        property_count = len(property_names)
        x_index = property_names.index("x")
        y_index = property_names.index("y")
        z_index = property_names.index("z")
        vertex_count = header["vertex_count"]

        mins = [math.inf, math.inf, math.inf]
        maxs = [-math.inf, -math.inf, -math.inf]
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
                coords = (
                    float(parts[x_index]),
                    float(parts[y_index]),
                    float(parts[z_index]),
                )
            except ValueError as exc:
                raise RuntimeError(f"non-numeric xyz at row {row_idx}: {path}") from exc
            if not all(math.isfinite(value) for value in coords):
                raise RuntimeError(f"non-finite xyz at row {row_idx}: {path}")
            for axis, value in enumerate(coords):
                if value < mins[axis]:
                    mins[axis] = value
                if value > maxs[axis]:
                    maxs[axis] = value
            parsed_count += 1

        trailing = handle.readline()
        if trailing != "":
            raise RuntimeError(f"extra data after declared vertex count: {path}")
    finally:
        handle.close()

    if parsed_count != vertex_count:
        raise RuntimeError(
            f"parsed point count {parsed_count} != header vertex count {vertex_count}: {path}"
        )

    extent = [maxs[axis] - mins[axis] for axis in range(3)]
    center = [(mins[axis] + maxs[axis]) / 2.0 for axis in range(3)]
    return {
        "frame_id": frame_id,
        "source_file": str(path),
        "source_file_name": path.name,
        "ply_format": header["ply_format"],
        "vertex_count": vertex_count,
        "parsed_point_count": parsed_count,
        "vertex_properties": header["vertex_properties"],
        "property_names": header["property_names"],
        "comments": header["comments"],
        "obj_info": header["obj_info"],
        "frame_to_world_scale": header["frame_to_world_scale"],
        "frame_to_world_translation": header["frame_to_world_translation"],
        "bbox_min": mins,
        "bbox_max": maxs,
        "bbox_center": center,
        "bbox_extent": extent,
    }


def assign_axis(value: float, axis_min: float, axis_max: float, bins: int) -> int:
    if bins <= 0:
        raise RuntimeError("grid dimensions must be positive")
    if axis_max <= axis_min:
        raise RuntimeError(f"invalid envelope range [{axis_min}, {axis_max}]")
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


def tile_id_from_linear(linear: int, dims: tuple[int, int, int]) -> str:
    _nx, ny, nz = dims
    ix = linear // (ny * nz)
    iy = (linear // nz) % ny
    iz = linear % nz
    return f"gx_{ix}_gy_{iy}_gz_{iz}"


def scan_frame_occupancy(
    path: Path,
    frame_id: int,
    envelope_min: list[float],
    envelope_max: list[float],
    dims: tuple[int, int, int],
) -> dict:
    handle, header = open_ply(path)
    try:
        property_names = header["property_names"]
        property_count = len(property_names)
        x_index = property_names.index("x")
        y_index = property_names.index("y")
        z_index = property_names.index("z")
        vertex_count = header["vertex_count"]
        nx, ny, nz = dims
        theoretical = nx * ny * nz
        counts = [0] * theoretical
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
            if not all(math.isfinite(value) for value in (x, y, z)):
                raise RuntimeError(f"non-finite xyz at row {row_idx}: {path}")

            ix = assign_axis(x, envelope_min[0], envelope_max[0], nx)
            iy = assign_axis(y, envelope_min[1], envelope_max[1], ny)
            iz = assign_axis(z, envelope_min[2], envelope_max[2], nz)
            counts[ix * ny * nz + iy * nz + iz] += 1
            parsed_count += 1

        trailing = handle.readline()
        if trailing != "":
            raise RuntimeError(f"extra data after declared vertex count: {path}")
    finally:
        handle.close()

    if parsed_count != vertex_count:
        raise RuntimeError(
            f"parsed point count {parsed_count} != header vertex count {vertex_count}: {path}"
        )
    if sum(counts) != parsed_count:
        raise RuntimeError(f"tile point sum mismatch for frame {frame_id}: {path}")
    if any(count < 0 for count in counts):
        raise RuntimeError(f"negative tile count for frame {frame_id}: {path}")

    non_empty_counts = [count for count in counts if count > 0]
    non_empty = len(non_empty_counts)
    empty = theoretical - non_empty
    if non_empty + empty != theoretical:
        raise RuntimeError(f"tile count invariant failure for frame {frame_id}: {path}")

    maximum = max(counts) if counts else 0
    minimum_nonzero = min(non_empty_counts) if non_empty_counts else 0
    return {
        "frame_id": frame_id,
        "source_file_name": path.name,
        "vertex_count": vertex_count,
        "parsed_point_count": parsed_count,
        "counts": counts,
        "non_empty_tile_count": non_empty,
        "empty_tile_count": empty,
        "minimum_nonzero_tile_point_count": minimum_nonzero,
        "maximum_tile_point_count": maximum,
        "maximum_tile_point_share": maximum / parsed_count if parsed_count else 0.0,
        "invariants": {
            "parsed_point_count_equals_header_vertex_count": parsed_count == vertex_count,
            "tile_point_count_sum_equals_frame_total": sum(counts) == parsed_count,
            "every_point_assigned_once": sum(counts) == parsed_count,
            "non_empty_plus_empty_equals_128": non_empty + empty == theoretical,
            "no_negative_tile_point_count": all(count >= 0 for count in counts),
        },
    }


def percentile(values: list[float], pct: float) -> float:
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


def summarize_numeric(values: list[float]) -> dict:
    if not values:
        return {"min": 0, "median": 0, "mean": 0, "max": 0}
    return {
        "min": min(values),
        "median": percentile(values, 0.5),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def update_extrema_frames(
    extrema_frames: dict[str, dict[str, list[int]]],
    frame: dict,
    sequence_min: list[float],
    sequence_max: list[float],
) -> None:
    for axis_name, axis in (("x", 0), ("y", 1), ("z", 2)):
        min_value = frame["bbox_min"][axis]
        max_value = frame["bbox_max"][axis]
        if min_value == sequence_min[axis]:
            extrema_frames[axis_name]["min_frames"].append(frame["frame_id"])
        if max_value == sequence_max[axis]:
            extrema_frames[axis_name]["max_frames"].append(frame["frame_id"])


def write_outputs(output_dir: Path, payload: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config_snapshot.json").write_text(
        json.dumps(payload["config"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "sequence_envelope.json").write_text(
        json.dumps(
            {
                "sequence_envelope": payload["sequence_envelope"],
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "scan_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with (output_dir / "frame_raw_bbox.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "frame_id",
                "source_file",
                "vertex_count",
                "parsed_point_count",
                "x_min",
                "y_min",
                "z_min",
                "x_max",
                "y_max",
                "z_max",
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
                    frame["vertex_count"],
                    frame["parsed_point_count"],
                    *frame["bbox_min"],
                    *frame["bbox_max"],
                    *frame["bbox_extent"],
                    frame.get("frame_to_world_scale") or "not_observed",
                    frame.get("frame_to_world_translation") or "not_observed",
                ]
            )

    with (output_dir / "frame_g128_occupancy.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "frame_id",
                "source_file",
                "vertex_count",
                "non_empty_tile_count",
                "empty_tile_count",
                "maximum_tile_point_count",
                "maximum_tile_point_share",
                "minimum_nonzero_tile_point_count",
            ]
        )
        for frame in payload["occupancy_frames"]:
            writer.writerow(
                [
                    frame["frame_id"],
                    frame["source_file_name"],
                    frame["vertex_count"],
                    frame["non_empty_tile_count"],
                    frame["empty_tile_count"],
                    frame["maximum_tile_point_count"],
                    f"{frame['maximum_tile_point_share']:.12f}",
                    frame["minimum_nonzero_tile_point_count"],
                ]
            )

    with (output_dir / "g128_tile_activity_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "tile_id",
                "linear_index",
                "active_frame_count",
                "total_point_count_across_scanned_frames",
                "minimum_nonzero_point_count",
                "maximum_point_count",
            ]
        )
        for row in payload["tile_activity_summary"]:
            writer.writerow(
                [
                    row["tile_id"],
                    row["linear_index"],
                    row["active_frame_count"],
                    row["total_point_count_across_scanned_frames"],
                    row["minimum_nonzero_point_count"],
                    row["maximum_point_count"],
                ]
            )

    invariant_lines = ["Full sequence envelope scan invariant checks"]
    for name, value in payload["invariants"].items():
        invariant_lines.append(f"{name} -> {value}")
    for frame in payload["frames"]:
        invariant_lines.append(
            f"stage A frame {frame['frame_id']}: parsed_point_count == header vertex_count -> "
            f"{frame['parsed_point_count'] == frame['vertex_count']}"
        )
    for frame in payload["occupancy_frames"]:
        for key, value in frame["invariants"].items():
            invariant_lines.append(f"stage B frame {frame['frame_id']}: {key} -> {value}")
    (output_dir / "invariants.txt").write_text(
        "\n".join(invariant_lines) + "\n", encoding="utf-8"
    )


def validate_inputs(
    raw_root: Path,
    output_dir: Path,
    frame_id_list: list[int],
    pilot_frame_id: int,
    dims: tuple[int, int, int],
) -> Path:
    if not raw_root.is_dir():
        raise RuntimeError(f"--raw-root is not a directory: {raw_root}")
    if pilot_frame_id not in frame_id_list:
        raise RuntimeError("--pilot-frame-id must be inside frame range")
    if any(dim <= 0 for dim in dims):
        raise RuntimeError("grid dimensions must be positive")

    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    output_dir = output_dir.resolve()
    allowed_output_root = (Path.cwd() / "outputs" / "full_sequence_envelope_scan").resolve()
    if output_dir != allowed_output_root and not is_relative_to(
        output_dir, allowed_output_root
    ):
        raise RuntimeError(
            "--output-dir must be inside this repository's outputs/full_sequence_envelope_scan"
        )

    seen_names = set()
    for frame_id in frame_id_list:
        path = ply_path(raw_root, frame_id)
        if path.name in seen_names:
            raise RuntimeError(f"duplicate expected frame file name: {path.name}")
        seen_names.add(path.name)
        if not path.is_file():
            raise RuntimeError(f"missing expected frame file: {path}")
    return output_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw_root = Path(args.raw_root)
    ids = frame_ids(args.frame_start, args.frame_end)
    dims = (args.grid_nx, args.grid_ny, args.grid_nz)
    theoretical = args.grid_nx * args.grid_ny * args.grid_nz
    output_dir = validate_inputs(
        raw_root, Path(args.output_dir), ids, args.pilot_frame_id, dims
    )
    if args.progress_every <= 0:
        raise RuntimeError("--progress-every must be positive")

    started_at = time.time()
    print(f"Stage A: scanning raw-coordinate bbox for {len(ids)} frames")
    frames = []
    property_signature = None
    comment_signature = None

    for index, frame_id in enumerate(ids, start=1):
        frame = scan_frame_bbox(ply_path(raw_root, frame_id), frame_id)
        if property_signature is None:
            property_signature = frame["vertex_properties"]
        elif frame["vertex_properties"] != property_signature:
            raise RuntimeError(f"vertex property order changed at frame {frame_id}")
        current_comments = {
            "frame_to_world_scale": frame.get("frame_to_world_scale"),
            "frame_to_world_translation": frame.get("frame_to_world_translation"),
        }
        if comment_signature is None:
            comment_signature = current_comments
        elif current_comments != comment_signature:
            raise RuntimeError(f"frame_to_world header values changed at frame {frame_id}")
        frames.append(frame)
        if index % args.progress_every == 0 or index == len(ids):
            print(f"  Stage A progress: {index}/{len(ids)} frames")

    stage_a_seconds = time.time() - started_at
    sequence_min = [
        min(frame["bbox_min"][axis] for frame in frames) for axis in range(3)
    ]
    sequence_max = [
        max(frame["bbox_max"][axis] for frame in frames) for axis in range(3)
    ]
    sequence_extent = [
        sequence_max[axis] - sequence_min[axis] for axis in range(3)
    ]
    if any(extent <= 0 for extent in sequence_extent):
        raise RuntimeError(f"invalid full-sequence envelope extent: {sequence_extent}")

    extrema_frames = {
        "x": {"min_frames": [], "max_frames": []},
        "y": {"min_frames": [], "max_frames": []},
        "z": {"min_frames": [], "max_frames": []},
    }
    for frame in frames:
        update_extrema_frames(extrema_frames, frame, sequence_min, sequence_max)

    for frame in frames:
        for axis in range(3):
            if frame["bbox_min"][axis] < sequence_min[axis] or frame["bbox_max"][axis] > sequence_max[axis]:
                raise RuntimeError(f"full-sequence envelope does not contain frame {frame['frame_id']}")

    print(f"Stage B: scanning G{theoretical} occupancy for {len(ids)} frames")
    stage_b_started_at = time.time()
    occupancy_frames = []
    tile_active_frames = [0] * theoretical
    tile_total_points = [0] * theoretical
    tile_min_nonzero = [None] * theoretical
    tile_max_points = [0] * theoretical

    for index, frame_id in enumerate(ids, start=1):
        occupancy = scan_frame_occupancy(
            ply_path(raw_root, frame_id), frame_id, sequence_min, sequence_max, dims
        )
        counts = occupancy.pop("counts")
        for linear, count in enumerate(counts):
            tile_total_points[linear] += count
            if count > 0:
                tile_active_frames[linear] += 1
                if tile_min_nonzero[linear] is None or count < tile_min_nonzero[linear]:
                    tile_min_nonzero[linear] = count
                if count > tile_max_points[linear]:
                    tile_max_points[linear] = count
        occupancy_frames.append(occupancy)
        if index % args.progress_every == 0 or index == len(ids):
            print(f"  Stage B progress: {index}/{len(ids)} frames")

    stage_b_seconds = time.time() - stage_b_started_at
    total_seconds = time.time() - started_at
    tile_activity_summary = []
    for linear in range(theoretical):
        tile_activity_summary.append(
            {
                "tile_id": tile_id_from_linear(linear, dims),
                "linear_index": linear,
                "active_frame_count": tile_active_frames[linear],
                "total_point_count_across_scanned_frames": tile_total_points[linear],
                "minimum_nonzero_point_count": tile_min_nonzero[linear] or 0,
                "maximum_point_count": tile_max_points[linear],
            }
        )

    non_empty_values = [
        frame["non_empty_tile_count"] for frame in occupancy_frames
    ]
    max_share_values = [
        frame["maximum_tile_point_share"] for frame in occupancy_frames
    ]
    vertex_counts = [frame["vertex_count"] for frame in frames]
    extents_by_axis = {
        axis_name: [frame["bbox_extent"][axis] for frame in frames]
        for axis_name, axis in (("x", 0), ("y", 1), ("z", 2))
    }
    pilot_occupancy = next(
        frame for frame in occupancy_frames if frame["frame_id"] == args.pilot_frame_id
    )

    invariants = {
        "scanned_frame_count_equals_expected": len(frames) == len(ids) == 300,
        "expected_frame_range_continuous": ids == list(range(args.frame_start, args.frame_end + 1)),
        "stage_a_all_parsed_counts_match_header": all(
            frame["parsed_point_count"] == frame["vertex_count"] for frame in frames
        ),
        "full_sequence_envelope_contains_every_frame_bbox": all(
            all(
                frame["bbox_min"][axis] >= sequence_min[axis]
                and frame["bbox_max"][axis] <= sequence_max[axis]
                for axis in range(3)
            )
            for frame in frames
        ),
        "stage_b_all_tile_sums_match_frame_total": all(
            frame["invariants"]["tile_point_count_sum_equals_frame_total"]
            for frame in occupancy_frames
        ),
        "stage_b_all_points_assigned_once": all(
            frame["invariants"]["every_point_assigned_once"]
            for frame in occupancy_frames
        ),
        "stage_b_all_non_empty_plus_empty_equals_theoretical": all(
            frame["invariants"]["non_empty_plus_empty_equals_128"]
            for frame in occupancy_frames
        ),
        "stage_b_no_negative_tile_point_count": all(
            frame["invariants"]["no_negative_tile_point_count"]
            for frame in occupancy_frames
        ),
    }
    if not all(invariants.values()):
        raise RuntimeError(f"invariant failure: {invariants}")

    payload = {
        "config": {
            "raw_root": str(raw_root),
            "frame_start": args.frame_start,
            "frame_end": args.frame_end,
            "expected_frame_count": len(ids),
            "pilot_frame_id": args.pilot_frame_id,
            "output_dir": str(output_dir),
            "grid": {"nx": args.grid_nx, "ny": args.grid_ny, "nz": args.grid_nz},
            "boundary_rule": "[min, max) per axis; points on max boundary assigned to final cell",
            "temporary_tile_id_format": "gx_<ix>_gy_<iy>_gz_<iz>",
            "progress_every": args.progress_every,
        },
        "frames": frames,
        "occupancy_frames": occupancy_frames,
        "tile_activity_summary": tile_activity_summary,
        "sequence_envelope": {
            "provenance": "derived from raw-coordinate bbox union across scanned frames",
            "bbox_min": sequence_min,
            "bbox_max": sequence_max,
            "bbox_center": [
                (sequence_min[axis] + sequence_max[axis]) / 2.0 for axis in range(3)
            ],
            "bbox_extent": sequence_extent,
            "extrema_frames": extrema_frames,
        },
        "g128_full_sequence_provisional_grid_parameters": {
            "grid_origin": sequence_min,
            "cell_size": [
                sequence_extent[0] / args.grid_nx,
                sequence_extent[1] / args.grid_ny,
                sequence_extent[2] / args.grid_nz,
            ],
            "dims": {"nx": args.grid_nx, "ny": args.grid_ny, "nz": args.grid_nz},
            "theoretical_cell_count": theoretical,
        },
        "summary": {
            "stage_a_seconds": stage_a_seconds,
            "stage_b_seconds": stage_b_seconds,
            "total_seconds": total_seconds,
            "scanned_frame_count": len(frames),
            "frame_range": [args.frame_start, args.frame_end],
            "vertex_count": summarize_numeric([float(value) for value in vertex_counts]),
            "bbox_extent": {
                axis_name: summarize_numeric([float(value) for value in values])
                for axis_name, values in extents_by_axis.items()
            },
            "g128_non_empty_tile_count": summarize_numeric(
                [float(value) for value in non_empty_values]
            ),
            "g128_maximum_tile_point_share": summarize_numeric(
                [float(value) for value in max_share_values]
            ),
            "g128_never_active_tile_count": sum(
                1 for value in tile_active_frames if value == 0
            ),
            "pilot_frame_occupancy": pilot_occupancy,
        },
        "invariants": invariants,
    }

    write_outputs(output_dir, payload)
    print(f"Completed successfully in {total_seconds:.2f}s")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
