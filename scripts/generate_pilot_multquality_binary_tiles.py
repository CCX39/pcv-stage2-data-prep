#!/usr/bin/env python3
"""Generate frame 1051 five-level tile-local binary PLY pilot assets.

This stage reads the existing Stage 1A PDL=1.0 tile baseline and the frozen
Stage 1C sampling profile. It never reads raw Longdress PLY and never generates
DRC, XML, asset catalog, or Stage2Input files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import sys
from datetime import datetime, timezone
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
EXPECTED_FRAME_ID = 1051
EXPECTED_TILE_COUNT = 128
EXPECTED_NON_EMPTY = 40
EXPECTED_EMPTY = 88
MASK32 = 0xFFFFFFFF
RNG_INCREMENT = 0x6D2B79F5
SEED_MIX_MULTIPLIER = 16777619


class MultiPdlGenerationError(RuntimeError):
    pass


def as_posix(path: Path) -> str:
    return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MultiPdlGenerationError(f"Required JSON file not found: {path}")
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def uint32(value: int) -> int:
    return value & MASK32


def imul32(left: int, right: int) -> int:
    return uint32((left & MASK32) * (right & MASK32))


def derive_quality_seed(base_seed: int, seed_identity: str) -> int:
    value = uint32(base_seed)
    for byte in seed_identity.encode("utf-8"):
        value = imul32(value ^ byte, SEED_MIX_MULTIPLIER)
    return value


def create_seeded_rng(seed: int):
    state = uint32(seed)

    def next_random() -> float:
        nonlocal state
        state = uint32(state + RNG_INCREMENT)
        value = state
        value = imul32(value ^ (value >> 15), value | 1)
        value ^= uint32(value + imul32(value ^ (value >> 7), value | 61))
        return uint32(value ^ (value >> 14)) / 4294967296

    return next_random


def fisher_yates_indices(count: int, seed: int) -> list[int]:
    indices = list(range(count))
    random = create_seeded_rng(seed)
    for index in range(count - 1, 0, -1):
        swap_index = math.floor(random() * (index + 1))
        indices[index], indices[swap_index] = indices[swap_index], indices[index]
    return indices


def quality_label(quality: float) -> str:
    return f"{quality:.1f}"


def pdl_filename(quality: float) -> str:
    return f"pdl_{quality_label(quality)}.ply"


def target_count(source_point_count: int, quality: float) -> int:
    if quality == 1.0:
        return source_point_count
    return max(1, math.floor(source_point_count * quality))


def canonical_seed_identity(profile: dict[str, Any], tile_id: str) -> str:
    values = {
        "sampling_profile_id": profile["sampling_profile_id"],
        "dataset_id": profile["dataset_id"],
        "frame_id": profile["frame_id"],
        "grid_profile_id": profile["grid_profile_id"],
        "tile_id": tile_id,
    }
    return "|".join(f"{field}={values[field]}" for field in profile["seed_identity_fields"])


def selected_indices(source_point_count: int, quality: float, permutation: list[int]) -> list[int]:
    if quality == 1.0:
        return list(range(source_point_count))
    return sorted(permutation[: target_count(source_point_count, quality)])


def parse_binary_ply(path: Path) -> tuple[int, bytes, list[bytes]]:
    header = bytearray()
    with path.open("rb") as handle:
        while True:
            byte = handle.read(1)
            if not byte:
                raise MultiPdlGenerationError(f"Missing end_header in binary PLY: {path}")
            header.extend(byte)
            if header.endswith(b"end_header\n"):
                break
        data = handle.read()

    try:
        text = header.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MultiPdlGenerationError(f"Non-ASCII PLY header: {path}") from exc

    lines = [line.strip("\r") for line in text.split("\n") if line.strip("\r")]
    if not lines or lines[0] != "ply":
        raise MultiPdlGenerationError(f"Invalid PLY magic: {path}")
    fmt = None
    vertex_count = None
    properties: list[tuple[str, str]] = []
    in_vertex = False
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = " ".join(parts[1:])
        elif parts[0] == "element":
            if len(parts) != 3 or parts[1] != "vertex":
                raise MultiPdlGenerationError(f"Unsupported PLY element in {path}: {line}")
            vertex_count = int(parts[2])
            in_vertex = True
        elif parts[0] == "property":
            if not in_vertex or len(parts) != 3:
                raise MultiPdlGenerationError(f"Unsupported PLY property in {path}: {line}")
            properties.append((parts[1], parts[2]))
        elif parts[0] in {"comment", "end_header"}:
            continue
    if fmt != "binary_little_endian 1.0":
        raise MultiPdlGenerationError(f"Expected binary_little_endian 1.0 in {path}, got {fmt}")
    if vertex_count is None:
        raise MultiPdlGenerationError(f"Missing vertex count in {path}")
    if properties != EXPECTED_VERTEX_PROPERTIES:
        raise MultiPdlGenerationError(f"Unexpected PLY schema in {path}: {properties}")
    expected_data_len = vertex_count * RECORD_STRUCT.size
    if len(data) != expected_data_len:
        raise MultiPdlGenerationError(f"Unexpected PLY data length in {path}: {len(data)} != {expected_data_len}")
    records = [data[index : index + RECORD_STRUCT.size] for index in range(0, len(data), RECORD_STRUCT.size)]
    return vertex_count, bytes(header), records


def binary_ply_header(
    sampling_profile_id: str,
    grid_profile_id: str,
    frame_id: int,
    tile_id: str,
    quality: float,
    count: int,
    provenance_kind: str,
) -> bytes:
    lines = [
        "ply",
        "format binary_little_endian 1.0",
        f"comment sampling_profile_id {sampling_profile_id}",
        f"comment grid_profile_id {grid_profile_id}",
        f"comment source_frame_id {frame_id}",
        f"comment tile_id {tile_id}",
        f"comment pdl {quality_label(quality)}",
        f"comment provenance_kind {provenance_kind}",
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


def all_tile_ids(grid_profile: dict[str, Any]) -> list[str]:
    dims = grid_profile["grid_dimensions"]
    return [
        f"gx_{ix}_gy_{iy}_gz_{iz}"
        for ix in range(int(dims["nx"]))
        for iy in range(int(dims["ny"]))
        for iz in range(int(dims["nz"]))
    ]


def load_and_check_inputs(
    baseline_root: Path,
    grid_profile_path: Path,
    sampling_profile_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not baseline_root.is_dir():
        raise MultiPdlGenerationError(f"Baseline root is not readable: {baseline_root}")
    baseline_manifest = load_json(baseline_root / "generation_manifest.json")
    baseline_tile_index = load_json(baseline_root / "frame_1051_tile_index.json")
    grid_profile = load_json(grid_profile_path)
    sampling_profile = load_json(sampling_profile_path)
    baseline_validation = load_json(baseline_root / "validation_report.json")

    if int(baseline_manifest["source_frame_id"]) != EXPECTED_FRAME_ID:
        raise MultiPdlGenerationError("Baseline manifest is not for frame 1051")
    if not baseline_validation.get("passed"):
        raise MultiPdlGenerationError("Baseline validation_report.json is not marked passed")
    if int(baseline_manifest["non_empty_tile_count"]) != EXPECTED_NON_EMPTY:
        raise MultiPdlGenerationError("Baseline non-empty tile count is not 40")
    if int(baseline_manifest["empty_tile_count"]) != EXPECTED_EMPTY:
        raise MultiPdlGenerationError("Baseline empty tile count is not 88")
    if int(baseline_tile_index["tile_count"]) != EXPECTED_TILE_COUNT:
        raise MultiPdlGenerationError("Baseline tile index does not contain 128 tiles")
    if grid_profile["profile_id"] != sampling_profile["grid_profile_id"]:
        raise MultiPdlGenerationError("Sampling profile grid_profile_id does not match grid profile")
    if grid_profile["dataset_id"] != sampling_profile["dataset_id"]:
        raise MultiPdlGenerationError("Sampling profile dataset_id does not match grid profile")
    if int(grid_profile["source_frame_id"]) != int(sampling_profile["frame_id"]):
        raise MultiPdlGenerationError("Sampling profile frame_id does not match grid profile")
    if sampling_profile["quality_levels"] != [0.2, 0.4, 0.6, 0.8, 1.0]:
        raise MultiPdlGenerationError("Unexpected sampling profile quality_levels")
    if sampling_profile["sampling_scope"] != "tile_local":
        raise MultiPdlGenerationError("Sampling profile must be tile_local")
    return baseline_manifest, baseline_tile_index, baseline_validation, grid_profile, sampling_profile


def file_record(
    path: Path,
    artifact_root: Path,
    quality: float,
    source_point_count: int,
    retained_count: int,
    sampling_profile: dict[str, Any],
    tile_id: str,
    seed_identity: str,
    derived_seed: int,
    provenance_kind: str,
    baseline_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "sampling_profile_id": sampling_profile["sampling_profile_id"],
        "sampling_scope": sampling_profile["sampling_scope"],
        "dataset_id": sampling_profile["dataset_id"],
        "frame_id": sampling_profile["frame_id"],
        "grid_profile_id": sampling_profile["grid_profile_id"],
        "tile_id": tile_id,
        "target_pdl": quality,
        "source_point_count": source_point_count,
        "retained_point_count": retained_count,
        "actual_retained_ratio": retained_count / source_point_count,
        "base_seed": sampling_profile["base_seed"],
        "seed_identity": seed_identity,
        "derived_quality_seed": derived_seed,
        "sampling_method": sampling_profile["sampling_method"],
        "permutation_algorithm": sampling_profile["permutation_algorithm"]["name"],
        "source_order_policy": sampling_profile["source_order_policy"],
        "nested_group_id": seed_identity,
        "relative_path": as_posix(path.relative_to(artifact_root)),
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "provenance_kind": provenance_kind,
    }
    if baseline_source is not None:
        record["baseline_source"] = baseline_source
    return record


def publish_staging(staging_root: Path, artifact_root: Path) -> None:
    last_error: Exception | None = None
    for _ in range(20):
        try:
            staging_root.rename(artifact_root)
            return
        except PermissionError as exc:
            last_error = exc
    raise MultiPdlGenerationError(f"Could not publish staging root {staging_root}: {last_error}")


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline_root = Path(args.baseline_root)
    artifact_root = Path(args.artifact_root)
    grid_profile_path = Path(args.grid_profile)
    sampling_profile_path = Path(args.sampling_profile)

    if artifact_root.exists():
        raise MultiPdlGenerationError(f"Target artifact root already exists; refusing overwrite: {artifact_root}")

    baseline_manifest, baseline_tile_index, baseline_validation, grid_profile, sampling_profile = load_and_check_inputs(
        baseline_root, grid_profile_path, sampling_profile_path
    )

    parent = artifact_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging_root = parent / f".{artifact_root.name}.staging_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
    if staging_root.exists():
        raise MultiPdlGenerationError(f"Staging root already exists: {staging_root}")
    staging_root.mkdir(parents=True)

    try:
        grid_profile_sha256 = sha256_file(grid_profile_path)
        sampling_profile_sha256 = sha256_file(sampling_profile_path)
        baseline_manifest_sha256 = sha256_file(baseline_root / "generation_manifest.json")
        baseline_tile_index_sha256 = sha256_file(baseline_root / "frame_1051_tile_index.json")

        write_json(
            staging_root / "grid_profile_snapshot.json",
            {"grid_profile_sha256": grid_profile_sha256, "grid_profile": grid_profile},
        )
        write_json(
            staging_root / "sampling_profile_snapshot.json",
            {"sampling_profile_sha256": sampling_profile_sha256, "sampling_profile": sampling_profile},
        )

        tile_records: list[dict[str, Any]] = []
        expected_tile_ids = set(all_tile_ids(grid_profile))
        baseline_tiles = baseline_tile_index["tiles"]
        if {tile["tile_id"] for tile in baseline_tiles} != expected_tile_ids:
            raise MultiPdlGenerationError("Baseline tile index tile universe differs from grid profile")

        non_empty_count = 0
        empty_count = 0
        generated_file_count = 0
        pdl1_copy_count = 0
        low_pdl_file_count = 0
        output_point_counts_by_pdl = {quality_label(q): 0 for q in sampling_profile["quality_levels"]}

        for baseline_tile in baseline_tiles:
            tile_id = baseline_tile["tile_id"]
            point_count = int(baseline_tile["point_count"])
            common_record = {
                "tile_id": tile_id,
                "grid_index": baseline_tile["grid_index"],
                "tile_bbox_min": baseline_tile["tile_bbox_min"],
                "tile_bbox_max": baseline_tile["tile_bbox_max"],
                "is_empty": bool(baseline_tile["is_empty"]),
                "point_count": point_count,
            }
            if point_count == 0:
                empty_count += 1
                if not baseline_tile["is_empty"] or baseline_tile["asset_status"] != "not_generated_empty":
                    raise MultiPdlGenerationError(f"Baseline empty tile metadata invalid: {tile_id}")
                tile_records.append(
                    {
                        **common_record,
                        "asset_status": "not_generated_empty",
                        "quality_assets": [],
                    }
                )
                continue

            non_empty_count += 1
            if baseline_tile["is_empty"]:
                raise MultiPdlGenerationError(f"Baseline non-empty tile marked empty: {tile_id}")
            baseline_relpath = baseline_tile["pdl_1_0_ply_relpath"]
            if not baseline_relpath:
                raise MultiPdlGenerationError(f"Baseline non-empty tile missing PDL=1.0 relpath: {tile_id}")
            baseline_ply = baseline_root / baseline_relpath
            if not baseline_ply.is_file():
                raise MultiPdlGenerationError(f"Baseline PLY missing for {tile_id}: {baseline_ply}")
            if sha256_file(baseline_ply) != baseline_tile["pdl_1_0_ply_sha256"]:
                raise MultiPdlGenerationError(f"Baseline PLY sha256 mismatch before generation: {tile_id}")
            if baseline_ply.stat().st_size != int(baseline_tile["pdl_1_0_ply_file_size_bytes"]):
                raise MultiPdlGenerationError(f"Baseline PLY file size mismatch before generation: {tile_id}")

            source_count, _, source_records = parse_binary_ply(baseline_ply)
            if source_count != point_count:
                raise MultiPdlGenerationError(f"Baseline PLY vertex count mismatch for {tile_id}")

            tile_dir = staging_root / "tiles" / tile_id
            tile_dir.mkdir(parents=True, exist_ok=False)
            seed_identity = canonical_seed_identity(sampling_profile, tile_id)
            derived_seed = derive_quality_seed(int(sampling_profile["base_seed"]), seed_identity)
            permutation = fisher_yates_indices(source_count, derived_seed)
            quality_assets: list[dict[str, Any]] = []

            for quality in sampling_profile["quality_levels"]:
                quality = float(quality)
                retained_count = target_count(source_count, quality)
                target_path = tile_dir / pdl_filename(quality)
                if quality == 1.0:
                    shutil.copyfile(baseline_ply, target_path)
                    pdl1_copy_count += 1
                    provenance_kind = "byte_exact_copy_of_stage1a_baseline"
                    baseline_source = {
                        "baseline_root": as_posix(baseline_root),
                        "baseline_tile_id": tile_id,
                        "baseline_relative_path": baseline_relpath,
                        "baseline_sha256": baseline_tile["pdl_1_0_ply_sha256"],
                        "baseline_file_size_bytes": baseline_tile["pdl_1_0_ply_file_size_bytes"],
                    }
                else:
                    provenance_kind = "derived_adaptation_of_calibration_sampling_rule"
                    indices = selected_indices(source_count, quality, permutation)
                    if len(indices) != retained_count:
                        raise MultiPdlGenerationError(f"Retained count mismatch for {tile_id} PDL {quality}")
                    with target_path.open("wb") as handle:
                        handle.write(
                            binary_ply_header(
                                sampling_profile["sampling_profile_id"],
                                sampling_profile["grid_profile_id"],
                                int(sampling_profile["frame_id"]),
                                tile_id,
                                quality,
                                retained_count,
                                provenance_kind,
                            )
                        )
                        for source_index in indices:
                            handle.write(source_records[source_index])
                    baseline_source = None
                    low_pdl_file_count += 1

                generated_file_count += 1
                output_point_counts_by_pdl[quality_label(quality)] += retained_count
                quality_assets.append(
                    file_record(
                        target_path,
                        staging_root,
                        quality,
                        source_count,
                        retained_count,
                        sampling_profile,
                        tile_id,
                        seed_identity,
                        derived_seed,
                        provenance_kind,
                        baseline_source,
                    )
                )

            tile_records.append(
                {
                    **common_record,
                    "asset_status": "generated_pdl_5",
                    "quality_assets": quality_assets,
                }
            )

        if non_empty_count != EXPECTED_NON_EMPTY or empty_count != EXPECTED_EMPTY:
            raise MultiPdlGenerationError(f"Expected 40 non-empty / 88 empty, got {non_empty_count}/{empty_count}")
        expected_files = EXPECTED_NON_EMPTY * len(sampling_profile["quality_levels"])
        if generated_file_count != expected_files:
            raise MultiPdlGenerationError(f"Expected {expected_files} PLY files, generated {generated_file_count}")

        generation_manifest = {
            "artifact_profile_id": sampling_profile["sampling_profile_id"],
            "generation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "stage": "1D",
            "dataset_id": sampling_profile["dataset_id"],
            "frame_id": sampling_profile["frame_id"],
            "baseline_root": as_posix(baseline_root),
            "target_artifact_root": as_posix(artifact_root),
            "baseline_generation_manifest_sha256": baseline_manifest_sha256,
            "baseline_tile_index_sha256": baseline_tile_index_sha256,
            "baseline_validation_report_passed": bool(baseline_validation.get("passed")),
            "source_file_name": baseline_manifest["source_file_name"],
            "source_file_sha256": baseline_manifest["source_file_sha256"],
            "source_vertex_count": baseline_manifest["source_vertex_count"],
            "grid_profile_path": as_posix(grid_profile_path),
            "grid_profile_sha256": grid_profile_sha256,
            "sampling_profile_path": as_posix(sampling_profile_path),
            "sampling_profile_sha256": sampling_profile_sha256,
            "quality_levels": sampling_profile["quality_levels"],
            "sampling_scope": sampling_profile["sampling_scope"],
            "sampling_method": sampling_profile["sampling_method"],
            "pdl_1_0_policy": "byte_exact_copy_of_stage1a_baseline",
            "low_pdl_provenance_kind": "derived_adaptation_of_calibration_sampling_rule",
            "non_empty_tile_count": non_empty_count,
            "empty_tile_count": empty_count,
            "total_tile_count": EXPECTED_TILE_COUNT,
            "generated_ply_file_count": generated_file_count,
            "generated_low_pdl_ply_file_count": low_pdl_file_count,
            "generated_pdl_1_0_copy_count": pdl1_copy_count,
            "output_point_counts_by_pdl": output_point_counts_by_pdl,
            "generation_script_path": as_posix(Path(__file__).resolve()),
            "generation_script_sha256": sha256_file(Path(__file__).resolve()),
            "python_version": sys.version,
            "non_claims": [
                "not Draco DRC",
                "not XML or player manifest",
                "not formal asset catalog",
                "not Stage2Input",
                "not decoder latency or network overhead measurement",
                "not tile-level calibrated visual-quality evidence",
            ],
        }
        frame_index = {
            "artifact_profile_id": sampling_profile["sampling_profile_id"],
            "grid_profile_id": sampling_profile["grid_profile_id"],
            "sampling_profile_id": sampling_profile["sampling_profile_id"],
            "dataset_id": sampling_profile["dataset_id"],
            "frame_id": sampling_profile["frame_id"],
            "quality_levels": sampling_profile["quality_levels"],
            "tile_count": EXPECTED_TILE_COUNT,
            "non_empty_tile_count": non_empty_count,
            "empty_tile_count": empty_count,
            "tiles": tile_records,
        }

        write_json(staging_root / "generation_manifest.json", generation_manifest)
        write_json(staging_root / "frame_1051_tile_index.json", frame_index)
        publish_staging(staging_root, artifact_root)
        return generation_manifest
    except Exception:
        if staging_root.exists() and not artifact_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", default=str(DEFAULT_BASELINE_ROOT))
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--grid-profile", default=str(DEFAULT_GRID_PROFILE))
    parser.add_argument("--sampling-profile", default=str(DEFAULT_SAMPLING_PROFILE))
    return parser.parse_args()


def main() -> int:
    try:
        manifest = run(parse_args())
    except MultiPdlGenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "target_artifact_root": manifest["target_artifact_root"],
                "non_empty_tile_count": manifest["non_empty_tile_count"],
                "empty_tile_count": manifest["empty_tile_count"],
                "generated_ply_file_count": manifest["generated_ply_file_count"],
                "generated_low_pdl_ply_file_count": manifest["generated_low_pdl_ply_file_count"],
                "generated_pdl_1_0_copy_count": manifest["generated_pdl_1_0_copy_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
