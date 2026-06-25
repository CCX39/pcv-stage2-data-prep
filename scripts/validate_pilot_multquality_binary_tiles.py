#!/usr/bin/env python3
"""Validate frame 1051 five-level tile-local binary PLY pilot assets.

The sampling checks in this validator are implemented independently from the
generation script. It does not import or call generation helpers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_ROOT = ROOT / "artifacts" / "pilot_1051_g128_raw_v1"
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "pilot_1051_g128_tilelocal_pdl5_v1"
DEFAULT_GRID_PROFILE = ROOT / "configs" / "pilot_grid_profile.longdress_1051_g128_raw_v1.json"
DEFAULT_SAMPLING_PROFILE = ROOT / "configs" / "pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json"

EXPECTED_VERTEX_PROPERTIES = [
    ("float", "x"),
    ("float", "y"),
    ("float", "z"),
    ("uchar", "red"),
    ("uchar", "green"),
    ("uchar", "blue"),
]
RECORD_STRUCT = struct.Struct("<fffBBB")
EXPECTED_TILE_COUNT = 128
EXPECTED_NON_EMPTY = 40
EXPECTED_EMPTY = 88
MASK32 = 0xFFFFFFFF


class MultiPdlValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MultiPdlValidationError(f"Required JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def u32(value: int) -> int:
    return value & MASK32


def mul32(left: int, right: int) -> int:
    return u32((left & MASK32) * (right & MASK32))


def tile_seed(base_seed: int, identity: str) -> int:
    current = u32(base_seed)
    for b in identity.encode("utf-8"):
        current = mul32(current ^ b, 16777619)
    return current


class DeterministicRng:
    def __init__(self, seed: int) -> None:
        self.state = u32(seed)

    def next(self) -> float:
        self.state = u32(self.state + 0x6D2B79F5)
        value = self.state
        value = mul32(value ^ (value >> 15), value | 1)
        value ^= u32(value + mul32(value ^ (value >> 7), value | 61))
        return u32(value ^ (value >> 14)) / 4294967296


def make_permutation(count: int, seed: int) -> list[int]:
    values = [index for index in range(count)]
    rng = DeterministicRng(seed)
    for cursor in range(count - 1, 0, -1):
        other = math.floor(rng.next() * (cursor + 1))
        values[cursor], values[other] = values[other], values[cursor]
    return values


def qlabel(quality: float) -> str:
    return f"{quality:.1f}"


def qfile(quality: float) -> str:
    return f"pdl_{qlabel(quality)}.ply"


def expected_count(n: int, quality: float) -> int:
    return n if quality == 1.0 else max(1, math.floor(n * quality))


def seed_identity_from_profile(profile: dict[str, Any], tile_id: str) -> str:
    values = {
        "sampling_profile_id": profile["sampling_profile_id"],
        "dataset_id": profile["dataset_id"],
        "frame_id": profile["frame_id"],
        "grid_profile_id": profile["grid_profile_id"],
        "tile_id": tile_id,
    }
    return "|".join(f"{name}={values[name]}" for name in profile["seed_identity_fields"])


def read_binary_ply(path: Path) -> tuple[int, bytes, list[bytes], bytes]:
    raw = path.read_bytes()
    marker = b"end_header\n"
    offset = raw.find(marker)
    if offset < 0:
        raise MultiPdlValidationError(f"Missing end_header in {path}")
    header_end = offset + len(marker)
    header = raw[:header_end]
    payload = raw[header_end:]
    try:
        header_text = header.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MultiPdlValidationError(f"Non-ASCII PLY header in {path}") from exc
    lines = [line.strip("\r") for line in header_text.split("\n") if line.strip("\r")]
    if not lines or lines[0] != "ply":
        raise MultiPdlValidationError(f"Invalid PLY magic in {path}")
    fmt = None
    vertex_count = None
    props: list[tuple[str, str]] = []
    in_vertex = False
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = " ".join(parts[1:])
        elif parts[0] == "element":
            if len(parts) != 3 or parts[1] != "vertex":
                raise MultiPdlValidationError(f"Unsupported element in {path}: {line}")
            vertex_count = int(parts[2])
            in_vertex = True
        elif parts[0] == "property":
            if not in_vertex or len(parts) != 3:
                raise MultiPdlValidationError(f"Unsupported property in {path}: {line}")
            props.append((parts[1], parts[2]))
        elif parts[0] in {"comment", "end_header"}:
            continue
    if fmt != "binary_little_endian 1.0":
        raise MultiPdlValidationError(f"{path} is not binary_little_endian 1.0")
    if vertex_count is None:
        raise MultiPdlValidationError(f"Missing vertex count in {path}")
    if props != EXPECTED_VERTEX_PROPERTIES:
        raise MultiPdlValidationError(f"Unexpected vertex schema in {path}: {props}")
    expected_payload_len = vertex_count * RECORD_STRUCT.size
    if len(payload) != expected_payload_len:
        raise MultiPdlValidationError(f"Unexpected data length in {path}: {len(payload)} != {expected_payload_len}")
    records = [payload[index : index + RECORD_STRUCT.size] for index in range(0, len(payload), RECORD_STRUCT.size)]
    return vertex_count, header, records, raw


def all_tile_ids(grid_profile: dict[str, Any]) -> set[str]:
    dims = grid_profile["grid_dimensions"]
    return {
        f"gx_{ix}_gy_{iy}_gz_{iz}"
        for ix in range(int(dims["nx"]))
        for iy in range(int(dims["ny"]))
        for iz in range(int(dims["nz"]))
    }


def validate_asset_metadata(
    asset: dict[str, Any],
    expected_relpath: str,
    artifact_root: Path,
    sampling_profile: dict[str, Any],
    tile_id: str,
    quality: float,
    source_count: int,
    retained_count: int,
    seed_identity: str,
    derived_seed: int,
    provenance_kind: str,
) -> None:
    checks = {
        "sampling_profile_id": sampling_profile["sampling_profile_id"],
        "sampling_scope": sampling_profile["sampling_scope"],
        "dataset_id": sampling_profile["dataset_id"],
        "frame_id": sampling_profile["frame_id"],
        "grid_profile_id": sampling_profile["grid_profile_id"],
        "tile_id": tile_id,
        "target_pdl": quality,
        "source_point_count": source_count,
        "retained_point_count": retained_count,
        "base_seed": sampling_profile["base_seed"],
        "seed_identity": seed_identity,
        "derived_quality_seed": derived_seed,
        "sampling_method": sampling_profile["sampling_method"],
        "permutation_algorithm": sampling_profile["permutation_algorithm"]["name"],
        "source_order_policy": sampling_profile["source_order_policy"],
        "nested_group_id": seed_identity,
        "relative_path": expected_relpath,
        "provenance_kind": provenance_kind,
    }
    for key, expected in checks.items():
        observed = asset.get(key)
        if observed != expected:
            raise MultiPdlValidationError(
                f"{tile_id} PDL {quality}: metadata {key} expected {expected!r}, observed {observed!r}"
            )
    ratio = retained_count / source_count
    if not math.isclose(float(asset["actual_retained_ratio"]), ratio, rel_tol=0.0, abs_tol=1e-15):
        raise MultiPdlValidationError(f"{tile_id} PDL {quality}: actual_retained_ratio mismatch")
    path = artifact_root / expected_relpath
    if not path.is_file():
        raise MultiPdlValidationError(f"{tile_id} PDL {quality}: metadata path missing {path}")
    if int(asset["file_size_bytes"]) != path.stat().st_size:
        raise MultiPdlValidationError(f"{tile_id} PDL {quality}: metadata file_size_bytes mismatch")
    if asset["sha256"] != sha256_file(path):
        raise MultiPdlValidationError(f"{tile_id} PDL {quality}: metadata sha256 mismatch")


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline_root = Path(args.baseline_root)
    artifact_root = Path(args.artifact_root)
    grid_profile_path = Path(args.grid_profile)
    sampling_profile_path = Path(args.sampling_profile)
    if not baseline_root.is_dir():
        raise MultiPdlValidationError(f"Baseline root missing: {baseline_root}")
    if not artifact_root.is_dir():
        raise MultiPdlValidationError(f"Artifact root missing: {artifact_root}")
    grid_profile = load_json(grid_profile_path)
    sampling_profile = load_json(sampling_profile_path)
    manifest = load_json(artifact_root / "generation_manifest.json")
    tile_index = load_json(artifact_root / "frame_1051_tile_index.json")
    baseline_index = load_json(baseline_root / "frame_1051_tile_index.json")
    baseline_manifest = load_json(baseline_root / "generation_manifest.json")

    if manifest["artifact_profile_id"] != sampling_profile["sampling_profile_id"]:
        raise MultiPdlValidationError("generation_manifest artifact_profile_id mismatch")
    if tile_index["sampling_profile_id"] != sampling_profile["sampling_profile_id"]:
        raise MultiPdlValidationError("tile index sampling_profile_id mismatch")
    if sampling_profile["quality_levels"] != [0.2, 0.4, 0.6, 0.8, 1.0]:
        raise MultiPdlValidationError("unexpected quality_levels")
    if set(tile["tile_id"] for tile in tile_index["tiles"]) != all_tile_ids(grid_profile):
        raise MultiPdlValidationError("tile index does not cover G128 tile universe")
    if len(tile_index["tiles"]) != EXPECTED_TILE_COUNT:
        raise MultiPdlValidationError("tile index length is not 128")

    baseline_by_id = {tile["tile_id"]: tile for tile in baseline_index["tiles"]}
    expected_metadata_relpaths: set[str] = set()
    generated_file_count = 0
    low_pdl_file_count = 0
    pdl1_copy_count = 0
    non_empty = 0
    empty = 0
    output_counts_by_pdl = {qlabel(q): 0 for q in sampling_profile["quality_levels"]}

    for tile in tile_index["tiles"]:
        tile_id = tile["tile_id"]
        if tile_id not in baseline_by_id:
            raise MultiPdlValidationError(f"Unknown tile id in artifact metadata: {tile_id}")
        baseline_tile = baseline_by_id[tile_id]
        if int(tile["point_count"]) != int(baseline_tile["point_count"]):
            raise MultiPdlValidationError(f"{tile_id}: point_count differs from baseline")
        if tile["is_empty"]:
            empty += 1
            if int(tile["point_count"]) != 0 or tile["asset_status"] != "not_generated_empty":
                raise MultiPdlValidationError(f"{tile_id}: invalid empty tile metadata")
            if tile.get("quality_assets") != []:
                raise MultiPdlValidationError(f"{tile_id}: empty tile has quality assets")
            tile_dir = artifact_root / "tiles" / tile_id
            if tile_dir.exists() and list(tile_dir.glob("*.ply")):
                raise MultiPdlValidationError(f"{tile_id}: empty tile has PLY files")
            continue

        non_empty += 1
        if tile["asset_status"] != "generated_pdl_5":
            raise MultiPdlValidationError(f"{tile_id}: unexpected asset_status {tile['asset_status']!r}")
        assets = tile.get("quality_assets")
        if not isinstance(assets, list) or len(assets) != 5:
            raise MultiPdlValidationError(f"{tile_id}: expected exactly five quality asset metadata records")
        assets_by_pdl = {float(asset["target_pdl"]): asset for asset in assets}
        if set(assets_by_pdl) != set(float(q) for q in sampling_profile["quality_levels"]):
            raise MultiPdlValidationError(f"{tile_id}: unknown or missing PDL metadata")

        baseline_relpath = baseline_tile["pdl_1_0_ply_relpath"]
        baseline_ply = baseline_root / baseline_relpath
        baseline_count, _, baseline_records, baseline_raw = read_binary_ply(baseline_ply)
        source_count = int(tile["point_count"])
        if baseline_count != source_count:
            raise MultiPdlValidationError(f"{tile_id}: baseline PLY count mismatch")
        seed_identity = seed_identity_from_profile(sampling_profile, tile_id)
        if any(part.split("=", 1)[0] in {"target_pdl", "quality_level"} for part in seed_identity.split("|")):
            raise MultiPdlValidationError(f"{tile_id}: seed identity includes quality field")
        derived_seed = tile_seed(int(sampling_profile["base_seed"]), seed_identity)
        permutation = make_permutation(source_count, derived_seed)
        previous_set: set[int] | None = None

        for quality in [0.2, 0.4, 0.6, 0.8, 1.0]:
            retained_count = expected_count(source_count, quality)
            if quality == 1.0:
                expected_indices = list(range(source_count))
                provenance_kind = "byte_exact_copy_of_stage1a_baseline"
            else:
                expected_indices = sorted(permutation[:retained_count])
                provenance_kind = "derived_adaptation_of_calibration_sampling_rule"
            if expected_indices != sorted(expected_indices):
                raise MultiPdlValidationError(f"{tile_id} PDL {quality}: expected indices not sorted")
            if len(expected_indices) != len(set(expected_indices)):
                raise MultiPdlValidationError(f"{tile_id} PDL {quality}: duplicate expected indices")
            if any(index < 0 or index >= source_count for index in expected_indices):
                raise MultiPdlValidationError(f"{tile_id} PDL {quality}: expected index out of range")
            current_set = set(expected_indices)
            if previous_set is not None and not previous_set.issubset(current_set):
                raise MultiPdlValidationError(f"{tile_id} PDL {quality}: nested property failed")
            previous_set = current_set

            expected_relpath = f"tiles/{tile_id}/{qfile(quality)}"
            output_ply = artifact_root / expected_relpath
            asset = assets_by_pdl[quality]
            validate_asset_metadata(
                asset,
                expected_relpath,
                artifact_root,
                sampling_profile,
                tile_id,
                quality,
                source_count,
                retained_count,
                seed_identity,
                derived_seed,
                provenance_kind,
            )
            output_count, _, output_records, output_raw = read_binary_ply(output_ply)
            if output_count != retained_count:
                raise MultiPdlValidationError(f"{tile_id} PDL {quality}: PLY vertex count mismatch")
            if quality == 1.0:
                if output_raw != baseline_raw:
                    raise MultiPdlValidationError(f"{tile_id} PDL 1.0: output is not byte-exact baseline copy")
                if asset.get("baseline_source", {}).get("baseline_sha256") != baseline_tile["pdl_1_0_ply_sha256"]:
                    raise MultiPdlValidationError(f"{tile_id} PDL 1.0: baseline source sha mismatch")
                pdl1_copy_count += 1
            else:
                expected_records = [baseline_records[index] for index in expected_indices]
                if output_records != expected_records:
                    raise MultiPdlValidationError(f"{tile_id} PDL {quality}: output record sequence mismatch")
                low_pdl_file_count += 1
            generated_file_count += 1
            output_counts_by_pdl[qlabel(quality)] += retained_count
            expected_metadata_relpaths.add(expected_relpath)

    if non_empty != EXPECTED_NON_EMPTY or empty != EXPECTED_EMPTY:
        raise MultiPdlValidationError(f"expected 40 non-empty / 88 empty, got {non_empty}/{empty}")
    expected_ply_count = EXPECTED_NON_EMPTY * len(sampling_profile["quality_levels"])
    if generated_file_count != expected_ply_count:
        raise MultiPdlValidationError(f"expected {expected_ply_count} PLY files, validated {generated_file_count}")
    if pdl1_copy_count != EXPECTED_NON_EMPTY or low_pdl_file_count != EXPECTED_NON_EMPTY * 4:
        raise MultiPdlValidationError("unexpected PDL=1.0 copy count or low-PDL file count")

    actual_relpaths = {
        path.relative_to(artifact_root).as_posix()
        for path in (artifact_root / "tiles").rglob("*.ply")
    }
    if actual_relpaths != expected_metadata_relpaths:
        extra = sorted(actual_relpaths - expected_metadata_relpaths)
        missing = sorted(expected_metadata_relpaths - actual_relpaths)
        raise MultiPdlValidationError(f"metadata/file mismatch; extra={extra}, missing={missing}")

    if int(manifest["generated_ply_file_count"]) != generated_file_count:
        raise MultiPdlValidationError("manifest generated_ply_file_count mismatch")
    if int(manifest["generated_low_pdl_ply_file_count"]) != low_pdl_file_count:
        raise MultiPdlValidationError("manifest generated_low_pdl_ply_file_count mismatch")
    if int(manifest["generated_pdl_1_0_copy_count"]) != pdl1_copy_count:
        raise MultiPdlValidationError("manifest generated_pdl_1_0_copy_count mismatch")
    if manifest["source_file_sha256"] != baseline_manifest["source_file_sha256"]:
        raise MultiPdlValidationError("manifest source file sha does not match baseline")

    report = {
        "passed": True,
        "artifact_profile_id": sampling_profile["sampling_profile_id"],
        "frame_id": sampling_profile["frame_id"],
        "quality_levels": sampling_profile["quality_levels"],
        "tile_count": EXPECTED_TILE_COUNT,
        "non_empty_tile_count": non_empty,
        "empty_tile_count": empty,
        "generated_ply_file_count": generated_file_count,
        "generated_low_pdl_ply_file_count": low_pdl_file_count,
        "generated_pdl_1_0_copy_count": pdl1_copy_count,
        "output_point_counts_by_pdl": output_counts_by_pdl,
        "checks": {
            "forty_non_empty_tiles_have_five_ply": True,
            "eighty_eight_empty_tiles_have_no_ply": True,
            "pdl_1_0_files_are_byte_exact_baseline_copies": True,
            "all_ply_binary_little_endian_schema": True,
            "low_pdl_counts_match_max_1_floor_Np": True,
            "pdl_1_0_counts_match_N": True,
            "actual_retained_ratios_match_counts": True,
            "nested_property_holds_for_each_tile": True,
            "selected_indices_match_independent_permutation_prefix": True,
            "output_records_match_source_records_exactly": True,
            "metadata_matches_files_and_derived_values": True,
            "metadata_file_universe_matches_actual_ply_files": True,
        },
        "non_claims": [
            "not Draco DRC validation",
            "not XML or player manifest validation",
            "not Stage2Input validation",
            "not decoder latency or network overhead measurement",
            "not tile-level calibrated visual quality evidence",
        ],
    }
    write_json(artifact_root / "validation_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", default=str(DEFAULT_BASELINE_ROOT))
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--grid-profile", default=str(DEFAULT_GRID_PROFILE))
    parser.add_argument("--sampling-profile", default=str(DEFAULT_SAMPLING_PROFILE))
    return parser.parse_args()


def main() -> int:
    try:
        report = run(parse_args())
    except MultiPdlValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "artifact_profile_id": report["artifact_profile_id"],
                "non_empty_tile_count": report["non_empty_tile_count"],
                "empty_tile_count": report["empty_tile_count"],
                "generated_ply_file_count": report["generated_ply_file_count"],
                "generated_low_pdl_ply_file_count": report["generated_low_pdl_ply_file_count"],
                "generated_pdl_1_0_copy_count": report["generated_pdl_1_0_copy_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
