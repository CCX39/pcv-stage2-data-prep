#!/usr/bin/env python3
"""Independently validate the stage 2B Draco round-trip probe artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "configs" / "draco_roundtrip_probe.longdress_1051_g128_pdl5_qp3_cl10_v1.json"
DEFAULT_SOURCE_ROOT = ROOT / "artifacts" / "pilot_1051_g128_tilelocal_pdl5_v1"
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "draco_roundtrip_probe_1051_g128_pdl5_qp3_cl10_v1"

EXPECTED_PDLS = [0.2, 0.4, 0.6, 0.8, 1.0]
EXPECTED_QPS = [8, 10, 12]
EXPECTED_VARIANT_COUNT = 30
SOURCE_RECORD_STRUCT = struct.Struct("<fffBBB")
FLOAT_TOLERANCE_FACTOR = 1e-6
NEAREST_TIE_EPSILON_FACTOR = 1e-12


class DracoProbeValidationError(RuntimeError):
    pass


PLY_SCALAR_FORMATS = {
    "char": ("b", 1),
    "int8": ("b", 1),
    "uchar": ("B", 1),
    "uint8": ("B", 1),
    "short": ("h", 2),
    "int16": ("h", 2),
    "ushort": ("H", 2),
    "uint16": ("H", 2),
    "int": ("i", 4),
    "int32": ("i", 4),
    "uint": ("I", 4),
    "uint32": ("I", 4),
    "float": ("f", 4),
    "float32": ("f", 4),
    "double": ("d", 8),
    "float64": ("d", 8),
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DracoProbeValidationError(f"Required JSON file not found: {path}")
    if path.stat().st_size == 0:
        raise DracoProbeValidationError(f"Required JSON file is empty: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def qlabel(value: float) -> str:
    return f"{value:.1f}"


def variant_id(tile_id: str, source_pdl: float, compression_level: int, qp: int) -> str:
    return f"{tile_id}__pdl_{qlabel(source_pdl)}__cl{compression_level}__qp{qp}"


def drc_filename(source_pdl: float, compression_level: int, qp: int) -> str:
    return f"pdl_{qlabel(source_pdl)}_cl{compression_level}_qp{qp}.drc"


def decoded_filename(source_pdl: float, compression_level: int, qp: int) -> str:
    return f"pdl_{qlabel(source_pdl)}_cl{compression_level}_qp{qp}.decoded.ply"


def select_representative_tiles(tile_index: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = [tile for tile in tile_index["tiles"] if not tile.get("is_empty")]
    min_tile = sorted(tiles, key=lambda tile: (int(tile["point_count"]), tile["tile_id"]))[0]
    max_tile = sorted(tiles, key=lambda tile: (-int(tile["point_count"]), tile["tile_id"]))[0]
    if min_tile["tile_id"] == max_tile["tile_id"]:
        raise DracoProbeValidationError("representative tile selection resolved to the same tile")
    return [
        {
            "selection_reason": "min_nonempty",
            "tile_id": min_tile["tile_id"],
            "source_point_count": int(min_tile["point_count"]),
        },
        {
            "selection_reason": "max_nonempty",
            "tile_id": max_tile["tile_id"],
            "source_point_count": int(max_tile["point_count"]),
        },
    ]


def parse_header(raw: bytes, path: Path) -> tuple[str, int, list[tuple[str, str]], int]:
    marker = b"end_header"
    marker_pos = raw.find(marker)
    if marker_pos < 0:
        raise DracoProbeValidationError(f"Missing end_header in PLY: {path}")
    newline_pos = raw.find(b"\n", marker_pos)
    if newline_pos < 0:
        raise DracoProbeValidationError(f"PLY header does not end with newline: {path}")
    header_end = newline_pos + 1
    header = raw[:header_end]
    try:
        text = header.decode("ascii")
    except UnicodeDecodeError as exc:
        raise DracoProbeValidationError(f"Non-ASCII PLY header: {path}") from exc
    lines = [line.strip("\r") for line in text.split("\n") if line.strip("\r")]
    if not lines or lines[0] != "ply":
        raise DracoProbeValidationError(f"Invalid PLY magic: {path}")

    fmt = None
    vertex_count = None
    props: list[tuple[str, str]] = []
    current_element = None
    seen_vertex = False
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = " ".join(parts[1:])
        elif parts[0] == "element":
            current_element = parts[1]
            if current_element == "vertex":
                if len(parts) != 3:
                    raise DracoProbeValidationError(f"Invalid vertex element line in {path}: {line}")
                vertex_count = int(parts[2])
                seen_vertex = True
            elif seen_vertex:
                raise DracoProbeValidationError(f"Unsupported non-vertex element after vertex data in {path}: {line}")
        elif parts[0] == "property":
            if current_element == "vertex":
                if len(parts) != 3 or parts[1] == "list":
                    raise DracoProbeValidationError(f"Unsupported vertex property in {path}: {line}")
                props.append((parts[1], parts[2]))
        elif parts[0] in {"comment", "obj_info", "end_header"}:
            continue
    if fmt is None or vertex_count is None:
        raise DracoProbeValidationError(f"PLY format or vertex count missing: {path}")
    for required in ("x", "y", "z", "red", "green", "blue"):
        if required not in [name for _, name in props]:
            raise DracoProbeValidationError(f"PLY missing required property {required}: {path}")
    return fmt, vertex_count, props, header_end


def parse_ply_points(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    fmt, vertex_count, props, header_end = parse_header(raw, path)
    payload = raw[header_end:]
    points: list[dict[str, Any]] = []
    prop_names = [name for _, name in props]
    if fmt == "binary_little_endian 1.0":
        struct_format = "<" + "".join(PLY_SCALAR_FORMATS[prop_type][0] for prop_type, _ in props)
        record_struct = struct.Struct(struct_format)
        expected_len = vertex_count * record_struct.size
        if len(payload) != expected_len:
            raise DracoProbeValidationError(f"Binary PLY payload length mismatch in {path}: {len(payload)} != {expected_len}")
        for offset in range(0, len(payload), record_struct.size):
            values = record_struct.unpack(payload[offset : offset + record_struct.size])
            record = dict(zip(prop_names, values))
            points.append(
                {
                    "x": float(record["x"]),
                    "y": float(record["y"]),
                    "z": float(record["z"]),
                    "red": int(record["red"]),
                    "green": int(record["green"]),
                    "blue": int(record["blue"]),
                }
            )
    elif fmt == "ascii 1.0":
        text = payload.decode("ascii")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < vertex_count:
            raise DracoProbeValidationError(f"ASCII PLY has fewer vertex lines than header count: {path}")
        for line in lines[:vertex_count]:
            parts = line.split()
            if len(parts) < len(props):
                raise DracoProbeValidationError(f"ASCII PLY vertex line has too few fields in {path}: {line}")
            record: dict[str, Any] = {}
            for (prop_type, name), value in zip(props, parts):
                if prop_type in {"float", "float32", "double", "float64"}:
                    record[name] = float(value)
                else:
                    record[name] = int(value)
            points.append(
                {
                    "x": float(record["x"]),
                    "y": float(record["y"]),
                    "z": float(record["z"]),
                    "red": int(record["red"]),
                    "green": int(record["green"]),
                    "blue": int(record["blue"]),
                }
            )
    else:
        raise DracoProbeValidationError(f"Unsupported PLY format in {path}: {fmt}")
    return {"format": fmt, "vertex_count": vertex_count, "properties": props, "points": points}


def axis_stats(points: list[dict[str, Any]], axis: str) -> tuple[float, float, float]:
    values = [float(point[axis]) for point in points]
    return min(values), max(values), max(values) - min(values)


def quantization_bin(span: float, qp: int) -> float:
    if span <= 0:
        return 0.0
    return span / ((1 << qp) - 1)


def point_xyz(point: dict[str, Any]) -> tuple[float, float, float]:
    return (float(point["x"]), float(point["y"]), float(point["z"]))


def rgb_tuple(point: dict[str, Any]) -> tuple[int, int, int]:
    return (int(point["red"]), int(point["green"]), int(point["blue"]))


def squared_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax, ay, az = point_xyz(a)
    bx, by, bz = point_xyz(b)
    dx = ax - bx
    dy = ay - by
    dz = az - bz
    return dx * dx + dy * dy + dz * dz


def compute_geometry_tolerance(source_points: list[dict[str, Any]], qp: int) -> dict[str, Any]:
    spans = {axis: axis_stats(source_points, axis)[2] for axis in ("x", "y", "z")}
    steps = {axis: quantization_bin(spans[axis], qp) for axis in ("x", "y", "z")}
    max_span = max(spans.values()) if spans else 0.0
    float_tolerance = FLOAT_TOLERANCE_FACTOR * max(1.0, max_span)
    geometry_tolerance = math.sqrt(sum(step * step for step in steps.values())) + float_tolerance
    if not math.isfinite(geometry_tolerance) or geometry_tolerance <= 0:
        raise DracoProbeValidationError(f"invalid geometry tolerance for qp={qp}: {geometry_tolerance}")
    return {
        "axis_spans": spans,
        "quantization_steps": steps,
        "float_tolerance": float_tolerance,
        "geometry_tolerance": geometry_tolerance,
        "definition": "sqrt(step_x^2 + step_y^2 + step_z^2) + 1e-6 * max(1.0, max_axis_span)",
    }


def assert_finite_positions(label: str, points: list[dict[str, Any]]) -> None:
    for index, point in enumerate(points):
        values = point_xyz(point)
        if not all(math.isfinite(value) for value in values):
            raise DracoProbeValidationError(f"{label}: non-finite position at point index {index}: {values}")


def spatial_cell_key(point: dict[str, Any], cell_size: float) -> tuple[int, int, int]:
    x, y, z = point_xyz(point)
    return (
        math.floor(x / cell_size),
        math.floor(y / cell_size),
        math.floor(z / cell_size),
    )


def build_spatial_index(points: list[dict[str, Any]], cell_size: float) -> dict[tuple[int, int, int], list[int]]:
    buckets: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for index, point in enumerate(points):
        buckets[spatial_cell_key(point, cell_size)].append(index)
    return buckets


def nearest_within_tolerance(
    query: dict[str, Any],
    candidates: list[dict[str, Any]],
    buckets: dict[tuple[int, int, int], list[int]],
    cell_size: float,
    tolerance: float,
) -> dict[str, Any]:
    key = spatial_cell_key(query, cell_size)
    tolerance_sq = tolerance * tolerance
    tie_epsilon = max(1e-24, tolerance_sq * NEAREST_TIE_EPSILON_FACTOR)
    best_distance_sq = math.inf
    best_indices: list[int] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for candidate_index in buckets.get((key[0] + dx, key[1] + dy, key[2] + dz), []):
                    distance_sq = squared_distance(query, candidates[candidate_index])
                    if distance_sq > tolerance_sq + tie_epsilon:
                        continue
                    if distance_sq < best_distance_sq - tie_epsilon:
                        best_distance_sq = distance_sq
                        best_indices = [candidate_index]
                    elif abs(distance_sq - best_distance_sq) <= tie_epsilon:
                        best_indices.append(candidate_index)
    if not best_indices:
        return {"found": False, "index": None, "distance": math.inf, "unique": False, "tie_count": 0}
    return {
        "found": True,
        "index": best_indices[0],
        "distance": math.sqrt(best_distance_sq),
        "unique": len(best_indices) == 1,
        "tie_count": len(best_indices),
    }


def nearest_map(
    query_points: list[dict[str, Any]],
    candidate_points: list[dict[str, Any]],
    candidate_index: dict[tuple[int, int, int], list[int]],
    cell_size: float,
    tolerance: float,
) -> list[dict[str, Any]]:
    return [
        nearest_within_tolerance(query_point, candidate_points, candidate_index, cell_size, tolerance)
        for query_point in query_points
    ]


def summarize_distances(nearest: list[dict[str, Any]], label: str, variant_id_value: str) -> dict[str, float]:
    missing = [index for index, item in enumerate(nearest) if not item["found"]]
    if missing:
        first = missing[0]
        raise DracoProbeValidationError(
            f"{variant_id_value}: order-independent geometry check failed; "
            f"{label} point index {first} has no counterpart within tolerance"
        )
    distances = [float(item["distance"]) for item in nearest]
    if not all(math.isfinite(distance) for distance in distances):
        raise DracoProbeValidationError(f"{variant_id_value}: non-finite nearest-neighbor distance in {label}")
    count = max(1, len(distances))
    return {
        "max_distance": max(distances) if distances else 0.0,
        "mean_distance": sum(distances) / count,
    }


def validate_roundtrip_point_sets(
    variant: dict[str, Any],
    source: dict[str, Any],
    decoded: dict[str, Any],
) -> dict[str, Any]:
    variant_id_value = str(variant["variant_id"])
    if decoded["vertex_count"] != source["vertex_count"]:
        raise DracoProbeValidationError(
            f"{variant_id_value}: decoded vertex count mismatch: "
            f"expected {source['vertex_count']}, observed {decoded['vertex_count']}"
        )
    source_points = source["points"]
    decoded_points = decoded["points"]
    assert_finite_positions(f"{variant_id_value} source", source_points)
    assert_finite_positions(f"{variant_id_value} decoded", decoded_points)

    qp = int(variant["qp"])
    tolerance_info = compute_geometry_tolerance(source_points, qp)
    tolerance = float(tolerance_info["geometry_tolerance"])
    cell_size = tolerance
    source_index = build_spatial_index(source_points, cell_size)
    decoded_index = build_spatial_index(decoded_points, cell_size)
    decoded_to_source = nearest_map(decoded_points, source_points, source_index, cell_size, tolerance)
    source_to_decoded = nearest_map(source_points, decoded_points, decoded_index, cell_size, tolerance)
    decoded_to_source_summary = summarize_distances(decoded_to_source, "decoded_to_source", variant_id_value)
    source_to_decoded_summary = summarize_distances(source_to_decoded, "source_to_decoded", variant_id_value)

    if Counter(rgb_tuple(point) for point in source_points) != Counter(rgb_tuple(point) for point in decoded_points):
        source_counter = Counter(rgb_tuple(point) for point in source_points)
        decoded_counter = Counter(rgb_tuple(point) for point in decoded_points)
        changed = sorted((source_counter - decoded_counter).items())[:3]
        added = sorted((decoded_counter - source_counter).items())[:3]
        raise DracoProbeValidationError(
            f"{variant_id_value}: RGB triplet multiset mismatch; missing_or_reduced={changed}, added_or_increased={added}"
        )

    mutual_pairs: list[tuple[int, int, float]] = []
    source_mutual_indices: set[int] = set()
    decoded_mutual_indices: set[int] = set()
    local_rgb_mismatches: list[tuple[int, int, tuple[int, int, int], tuple[int, int, int]]] = []
    for decoded_index_value, nearest_source in enumerate(decoded_to_source):
        if not nearest_source["found"] or not nearest_source["unique"]:
            continue
        source_index_value = int(nearest_source["index"])
        nearest_decoded = source_to_decoded[source_index_value]
        if not nearest_decoded["found"] or not nearest_decoded["unique"]:
            continue
        if int(nearest_decoded["index"]) != decoded_index_value:
            continue
        source_rgb = rgb_tuple(source_points[source_index_value])
        decoded_rgb = rgb_tuple(decoded_points[decoded_index_value])
        mutual_pairs.append((source_index_value, decoded_index_value, float(nearest_source["distance"])))
        source_mutual_indices.add(source_index_value)
        decoded_mutual_indices.add(decoded_index_value)
        if source_rgb != decoded_rgb:
            local_rgb_mismatches.append((source_index_value, decoded_index_value, source_rgb, decoded_rgb))
    if local_rgb_mismatches:
        source_index_value, decoded_index_value, source_rgb, decoded_rgb = local_rgb_mismatches[0]
        raise DracoProbeValidationError(
            f"{variant_id_value}: high-confidence mutual-nearest RGB mismatch; "
            f"source_index={source_index_value}, decoded_index={decoded_index_value}, "
            f"expected={source_rgb}, observed={decoded_rgb}"
        )

    for axis in ("x", "y", "z"):
        source_min, source_max, _ = axis_stats(source_points, axis)
        decoded_min, decoded_max, _ = axis_stats(decoded_points, axis)
        if decoded_min < source_min - tolerance or decoded_max > source_max + tolerance:
            raise DracoProbeValidationError(
                f"{variant_id_value}: decoded bbox exceeds source bbox tolerance on {axis}; "
                f"source=({source_min},{source_max}), decoded=({decoded_min},{decoded_max}), tolerance={tolerance}"
            )

    vertex_count = max(1, int(source["vertex_count"]))
    mutual_unique_pair_count = len(mutual_pairs)
    ambiguous_decoded_count = int(source["vertex_count"]) - len(decoded_mutual_indices)
    ambiguous_source_count = int(source["vertex_count"]) - len(source_mutual_indices)
    return {
        "source_ply_format": source["format"],
        "decoded_ply_format": decoded["format"],
        "vertex_count": source["vertex_count"],
        "source_properties": source["properties"],
        "decoded_properties": decoded["properties"],
        "geometry_tolerance": tolerance,
        "geometry_tolerance_definition": tolerance_info["definition"],
        "quantization_steps": tolerance_info["quantization_steps"],
        "axis_spans": tolerance_info["axis_spans"],
        "float_tolerance": tolerance_info["float_tolerance"],
        "geometry_point_set_error": {
            "source_to_decoded_max_distance": source_to_decoded_summary["max_distance"],
            "source_to_decoded_mean_distance": source_to_decoded_summary["mean_distance"],
            "decoded_to_source_max_distance": decoded_to_source_summary["max_distance"],
            "decoded_to_source_mean_distance": decoded_to_source_summary["mean_distance"],
        },
        "rgb_multiset_exact": True,
        "point_order_status": "not_required_for_draco_roundtrip",
        "local_rgb_association": {
            "mutual_unique_pair_count": mutual_unique_pair_count,
            "mutual_unique_pair_coverage": mutual_unique_pair_count / vertex_count,
            "mutual_unique_rgb_exact_match_count": mutual_unique_pair_count,
            "mutual_unique_rgb_exact_match_rate": 1.0 if mutual_unique_pair_count else None,
            "ambiguous_or_nonmutual_point_count": ambiguous_decoded_count,
            "ambiguous_or_nonmutual_decoded_point_count": ambiguous_decoded_count,
            "ambiguous_or_nonmutual_source_point_count": ambiguous_source_count,
            "interpretation": (
                "RGB triplet multiset is exact globally; high-confidence mutual-nearest spatial pairs "
                "match exactly, while ambiguous/nonmutual points are not claimed as point-identity proof."
            ),
        },
    }


def validate_roundtrip_records(
    variant: dict[str, Any],
    source_ply: Path,
    decoded_ply: Path,
) -> dict[str, Any]:
    source = parse_ply_points(source_ply)
    decoded = parse_ply_points(decoded_ply)
    return validate_roundtrip_point_sets(variant, source, decoded)




def expected_variants(profile: dict[str, Any], selected_tiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    cl = int(profile["compression_level"])
    for tile in selected_tiles:
        for pdl in profile["candidate_source_pdls"]:
            for qp in profile["candidate_qp_values"]:
                vid = variant_id(tile["tile_id"], float(pdl), cl, int(qp))
                expected[vid] = {
                    "variant_id": vid,
                    "selection_reason": tile["selection_reason"],
                    "tile_id": tile["tile_id"],
                    "source_pdl": float(pdl),
                    "compression_level": cl,
                    "qp": int(qp),
                    "drc_relpath": f"tiles/{tile['tile_id']}/{drc_filename(float(pdl), cl, int(qp))}",
                    "decoded_ply_relpath": f"tiles/{tile['tile_id']}/{decoded_filename(float(pdl), cl, int(qp))}",
                }
    return expected


def compare_json_snapshot(label: str, snapshot: dict[str, Any], hash_key: str, content_key: str, source_path: Path, source_data: dict[str, Any]) -> None:
    observed_hash = str(snapshot.get(hash_key, "")).upper()
    expected_hash = sha256_file(source_path)
    if observed_hash != expected_hash:
        raise DracoProbeValidationError(
            f"{label} snapshot hash mismatch: expected {expected_hash}, observed {observed_hash}"
        )
    if snapshot.get(content_key) != source_data:
        raise DracoProbeValidationError(f"{label} snapshot content mismatch")


def run(args: argparse.Namespace) -> dict[str, Any]:
    profile_path = Path(args.probe_profile)
    source_root = Path(args.source_root)
    artifact_root = Path(args.artifact_root)
    profile = load_json(profile_path)
    source_manifest_path = source_root / "generation_manifest.json"
    source_tile_index_path = source_root / "frame_1051_tile_index.json"
    source_manifest = load_json(source_manifest_path)
    source_tile_index = load_json(source_tile_index_path)
    manifest = load_json(artifact_root / "generation_manifest.json")

    compare_json_snapshot(
        "probe profile",
        load_json(artifact_root / "probe_profile_snapshot.json"),
        "probe_profile_sha256",
        "probe_profile",
        profile_path,
        profile,
    )
    compare_json_snapshot(
        "source artifact manifest",
        load_json(artifact_root / "source_artifact_manifest_snapshot.json"),
        "source_artifact_manifest_sha256",
        "source_artifact_manifest",
        source_manifest_path,
        source_manifest,
    )
    compare_json_snapshot(
        "source tile index",
        load_json(artifact_root / "source_tile_index_snapshot.json"),
        "source_tile_index_sha256",
        "source_tile_index",
        source_tile_index_path,
        source_tile_index,
    )

    selected_tiles = select_representative_tiles(source_tile_index)
    selection_doc = load_json(artifact_root / "probe_tile_selection.json")
    if selection_doc.get("selected_tiles") != selected_tiles:
        raise DracoProbeValidationError("probe_tile_selection.json does not match independently selected min/max tiles")
    if manifest.get("selected_tiles") != selected_tiles:
        raise DracoProbeValidationError("generation manifest selected_tiles mismatch")
    if str(manifest.get("source_artifact_manifest_sha256", "")).upper() != sha256_file(source_manifest_path):
        raise DracoProbeValidationError("generation manifest source_artifact_manifest_sha256 mismatch")
    if str(manifest.get("source_tile_index_sha256", "")).upper() != sha256_file(source_tile_index_path):
        raise DracoProbeValidationError("generation manifest source_tile_index_sha256 mismatch")
    if str(manifest.get("probe_profile_sha256", "")).upper() != sha256_file(profile_path):
        raise DracoProbeValidationError("generation manifest probe_profile_sha256 mismatch")

    expected = expected_variants(profile, selected_tiles)
    observed_by_id = {variant["variant_id"]: variant for variant in manifest["variants"]}
    if set(observed_by_id) != set(expected):
        raise DracoProbeValidationError("manifest variant set does not match expected 2 x 5 x 3 matrix")
    if int(manifest.get("generated_drc_file_count")) != EXPECTED_VARIANT_COUNT:
        raise DracoProbeValidationError("manifest generated_drc_file_count is not 30")
    if int(manifest.get("generated_decoded_ply_file_count")) != EXPECTED_VARIANT_COUNT:
        raise DracoProbeValidationError("manifest generated_decoded_ply_file_count is not 30")

    actual_drc = {path.relative_to(artifact_root).as_posix() for path in (artifact_root / "tiles").rglob("*.drc")}
    actual_decoded = {path.relative_to(artifact_root).as_posix() for path in (artifact_root / "tiles").rglob("*.decoded.ply")}
    expected_drc = {item["drc_relpath"] for item in expected.values()}
    expected_decoded = {item["decoded_ply_relpath"] for item in expected.values()}
    if actual_drc != expected_drc:
        raise DracoProbeValidationError(f"DRC file universe mismatch: extra={sorted(actual_drc - expected_drc)}, missing={sorted(expected_drc - actual_drc)}")
    if actual_decoded != expected_decoded:
        raise DracoProbeValidationError(
            f"decoded PLY file universe mismatch: extra={sorted(actual_decoded - expected_decoded)}, "
            f"missing={sorted(expected_decoded - actual_decoded)}"
        )

    source_tiles_by_id = {tile["tile_id"]: tile for tile in source_tile_index["tiles"]}
    variant_reports: list[dict[str, Any]] = []
    drc_hash_by_qp_for_max_pdl1: dict[int, str] = {}
    drc_bytes_by_qp: dict[str, list[int]] = {str(qp): [] for qp in profile["candidate_qp_values"]}
    aggregate_geometry = {
        "source_to_decoded_max_distance": 0.0,
        "source_to_decoded_mean_distance_max_across_variants": 0.0,
        "decoded_to_source_max_distance": 0.0,
        "decoded_to_source_mean_distance_max_across_variants": 0.0,
        "geometry_tolerance_max": 0.0,
    }
    aggregate_rgb = {
        "rgb_multiset_exact_for_all_variants": True,
        "mutual_unique_pair_coverage_min": 1.0,
        "mutual_unique_rgb_exact_match_rate_min": 1.0,
        "ambiguous_or_nonmutual_point_count_max": 0,
        "ambiguous_or_nonmutual_decoded_point_count_sum": 0,
        "ambiguous_or_nonmutual_source_point_count_sum": 0,
    }

    for vid, expected_variant in expected.items():
        observed = observed_by_id[vid]
        for key in ("tile_id", "source_pdl", "compression_level", "qp", "selection_reason"):
            if observed.get(key) != expected_variant[key]:
                raise DracoProbeValidationError(f"{vid}: manifest {key} mismatch")
        if observed.get("point_cloud_flag") != profile["point_cloud_flag"] or observed.get("point_cloud_mode") is not True:
            raise DracoProbeValidationError(f"{vid}: point-cloud metadata mismatch")
        tile = source_tiles_by_id[observed["tile_id"]]
        assets_by_pdl = {qlabel(float(asset["target_pdl"])): asset for asset in tile["quality_assets"]}
        source_asset = assets_by_pdl[qlabel(float(observed["source_pdl"]))]
        source_ply = source_root / source_asset["relative_path"]
        if observed.get("source_ply_relpath") != source_asset["relative_path"]:
            raise DracoProbeValidationError(f"{vid}: source_ply_relpath mismatch")
        if str(observed.get("source_ply_sha256", "")).upper() != sha256_file(source_ply):
            raise DracoProbeValidationError(f"{vid}: source PLY SHA-256 mismatch")
        if int(observed.get("source_ply_file_size_bytes")) != source_ply.stat().st_size:
            raise DracoProbeValidationError(f"{vid}: source PLY file size mismatch")
        drc_path = artifact_root / expected_variant["drc_relpath"]
        decoded_path = artifact_root / expected_variant["decoded_ply_relpath"]
        if observed.get("drc_relpath") != expected_variant["drc_relpath"]:
            raise DracoProbeValidationError(f"{vid}: drc_relpath mismatch")
        if observed.get("decoded_ply_relpath") != expected_variant["decoded_ply_relpath"]:
            raise DracoProbeValidationError(f"{vid}: decoded_ply_relpath mismatch")
        if str(observed.get("drc_sha256", "")).upper() != sha256_file(drc_path):
            raise DracoProbeValidationError(f"{vid}: DRC SHA-256 mismatch")
        if int(observed.get("drc_file_size_bytes")) != drc_path.stat().st_size:
            raise DracoProbeValidationError(f"{vid}: DRC file size mismatch")
        if str(observed.get("decoded_ply_sha256", "")).upper() != sha256_file(decoded_path):
            raise DracoProbeValidationError(f"{vid}: decoded PLY SHA-256 mismatch")
        if int(observed.get("decoded_ply_file_size_bytes")) != decoded_path.stat().st_size:
            raise DracoProbeValidationError(f"{vid}: decoded PLY file size mismatch")
        if int(observed["encoder"]["exit_code"]) != 0 or int(observed["decoder"]["exit_code"]) != 0:
            raise DracoProbeValidationError(f"{vid}: recorded encoder/decoder exit code is non-zero")
        if any(arg in {"-qc", "-qg"} for arg in observed["encoder"]["argv"]):
            raise DracoProbeValidationError(f"{vid}: forbidden color quantization flag present in recorded encoder argv")

        roundtrip = validate_roundtrip_records(observed, source_ply, decoded_path)
        drc_bytes_by_qp[str(observed["qp"])].append(int(observed["drc_file_size_bytes"]))
        geometry_error = roundtrip["geometry_point_set_error"]
        aggregate_geometry["source_to_decoded_max_distance"] = max(
            aggregate_geometry["source_to_decoded_max_distance"],
            float(geometry_error["source_to_decoded_max_distance"]),
        )
        aggregate_geometry["source_to_decoded_mean_distance_max_across_variants"] = max(
            aggregate_geometry["source_to_decoded_mean_distance_max_across_variants"],
            float(geometry_error["source_to_decoded_mean_distance"]),
        )
        aggregate_geometry["decoded_to_source_max_distance"] = max(
            aggregate_geometry["decoded_to_source_max_distance"],
            float(geometry_error["decoded_to_source_max_distance"]),
        )
        aggregate_geometry["decoded_to_source_mean_distance_max_across_variants"] = max(
            aggregate_geometry["decoded_to_source_mean_distance_max_across_variants"],
            float(geometry_error["decoded_to_source_mean_distance"]),
        )
        aggregate_geometry["geometry_tolerance_max"] = max(
            aggregate_geometry["geometry_tolerance_max"],
            float(roundtrip["geometry_tolerance"]),
        )
        local_rgb = roundtrip["local_rgb_association"]
        aggregate_rgb["mutual_unique_pair_coverage_min"] = min(
            aggregate_rgb["mutual_unique_pair_coverage_min"],
            float(local_rgb["mutual_unique_pair_coverage"]),
        )
        match_rate = local_rgb["mutual_unique_rgb_exact_match_rate"]
        if match_rate is not None:
            aggregate_rgb["mutual_unique_rgb_exact_match_rate_min"] = min(
                aggregate_rgb["mutual_unique_rgb_exact_match_rate_min"],
                float(match_rate),
            )
        aggregate_rgb["ambiguous_or_nonmutual_point_count_max"] = max(
            aggregate_rgb["ambiguous_or_nonmutual_point_count_max"],
            int(local_rgb["ambiguous_or_nonmutual_point_count"]),
        )
        aggregate_rgb["ambiguous_or_nonmutual_decoded_point_count_sum"] += int(
            local_rgb["ambiguous_or_nonmutual_decoded_point_count"]
        )
        aggregate_rgb["ambiguous_or_nonmutual_source_point_count_sum"] += int(
            local_rgb["ambiguous_or_nonmutual_source_point_count"]
        )
        if observed["selection_reason"] == "max_nonempty" and float(observed["source_pdl"]) == 1.0:
            drc_hash_by_qp_for_max_pdl1[int(observed["qp"])] = str(observed["drc_sha256"]).upper()
        variant_reports.append(
            {
                "variant_id": vid,
                "tile_id": observed["tile_id"],
                "source_pdl": observed["source_pdl"],
                "qp": observed["qp"],
                "drc_file_size_bytes": observed["drc_file_size_bytes"],
                **roundtrip,
            }
        )

    if sorted(drc_hash_by_qp_for_max_pdl1) != EXPECTED_QPS:
        raise DracoProbeValidationError("missing max_nonempty PDL=1.0 QP effect hashes")
    if len(set(drc_hash_by_qp_for_max_pdl1.values())) != len(EXPECTED_QPS):
        raise DracoProbeValidationError(
            "QP_EFFECT_NOT_OBSERVED: max_nonempty tile source_pdl=1.0 qp=8/10/12 DRC SHA-256 values are not all distinct"
        )

    report = {
        "passed": True,
        "artifact_profile_id": profile["profile_id"],
        "source_artifact_profile_id": profile["source_artifact_profile_id"],
        "selected_tiles": selected_tiles,
        "variant_count": EXPECTED_VARIANT_COUNT,
        "drc_file_count": EXPECTED_VARIANT_COUNT,
        "decoded_ply_file_count": EXPECTED_VARIANT_COUNT,
        "qp_effect_check": {
            "max_nonempty_pdl_1_0_drc_sha256_by_qp": {str(k): v for k, v in sorted(drc_hash_by_qp_for_max_pdl1.items())},
            "all_three_qp_hashes_distinct": True,
        },
        "drc_bytes_by_qp": {qp: {"min": min(values), "max": max(values), "sum": sum(values)} for qp, values in drc_bytes_by_qp.items()},
        "aggregate_geometry_error": aggregate_geometry,
        "aggregate_rgb_validation": aggregate_rgb,
        "checks": {
            "probe_profile_snapshot_matches_versioned_config": True,
            "source_artifact_snapshots_match_current_source": True,
            "representative_tiles_match_min_max_metadata_rule": True,
            "thirty_drc_and_thirty_decoded_ply_exist": True,
            "manifest_file_hashes_and_sizes_match_actual_files": True,
            "decoded_ply_contains_xyz_rgb": True,
            "decoded_vertex_count_matches_source": True,
            "point_order_status_not_required_for_draco_roundtrip": True,
            "order_independent_bidirectional_geometry_point_set_check": True,
            "rgb_triplet_multiset_exact": True,
            "high_confidence_mutual_pairs_rgb_exact": True,
            "geometry_errors_finite_and_within_quantization_cell_diagonal": True,
            "qp_effect_observed_for_max_tile_pdl_1_0": True,
            "local_cli_elapsed_not_interpreted_as_D": True,
        },
        "variant_reports": variant_reports,
        "non_claims": [
            "not the full 600-file DRC corpus",
            "not target-side decode-cost measurement",
            "not DRC-aware rendered Q_base measurement",
            "not Pareto pruning",
            "not Stage2Input",
        ],
    }
    write_json(artifact_root / "validation_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    return parser.parse_args()


def main() -> int:
    try:
        report = run(parse_args())
    except DracoProbeValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "variant_count": report["variant_count"],
                "selected_tiles": report["selected_tiles"],
                "qp_effect_check": report["qp_effect_check"],
                "aggregate_geometry_error": report["aggregate_geometry_error"],
                "aggregate_rgb_validation": report["aggregate_rgb_validation"],
                "drc_bytes_by_qp": report["drc_bytes_by_qp"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
