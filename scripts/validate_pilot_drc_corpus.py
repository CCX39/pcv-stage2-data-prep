#!/usr/bin/env python3
"""Validate the frame 1051 pilot DRC corpus artifact.

This validator is intended for phase 2C.1 after the researcher has manually
generated the corpus. It decodes all DRC files to temporary PLY files for basic
integrity checks and applies the stronger order-independent round-trip checks
to canary variants only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_draco_roundtrip_probe import (
    DracoProbeValidationError,
    parse_ply_points,
    rgb_tuple,
    sha256_file,
    validate_roundtrip_point_sets,
)


DEFAULT_PROFILE_PATH = Path("configs/pilot_drc_corpus.longdress_1051_g128_pdl5_qp3_cl10_v1.json")
EXPECTED_VARIANT_COUNT = 600
EXPECTED_NON_EMPTY_TILE_COUNT = 40
STDIO_LIMIT = 2000


class DrcCorpusValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def qlabel(value: float) -> str:
    return f"{value:.1f}"


def variant_id(tile_id: str, source_pdl: float, compression_level: int, qp: int) -> str:
    return f"{tile_id}__pdl_{qlabel(source_pdl)}__cl{compression_level}__qp{qp}"


def drc_filename(source_pdl: float, compression_level: int, qp: int) -> str:
    return f"pdl_{qlabel(source_pdl)}_cl{compression_level}_qp{qp}.drc"


def non_empty_tiles(tile_index: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = [tile for tile in tile_index.get("tiles", []) if not tile.get("is_empty")]
    tiles.sort(key=lambda item: str(item["tile_id"]))
    return tiles


def build_expected_variants(tile_index: dict[str, Any], profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    cl = int(profile["compression_level"])
    for tile in non_empty_tiles(tile_index):
        tile_id = str(tile["tile_id"])
        for source_pdl in profile["source_pdls"]:
            for qp in profile["qp_values"]:
                vid = variant_id(tile_id, float(source_pdl), cl, int(qp))
                expected[vid] = {
                    "variant_id": vid,
                    "tile_id": tile_id,
                    "source_pdl": float(source_pdl),
                    "compression_level": cl,
                    "qp": int(qp),
                    "drc_relpath": f"tiles/{tile_id}/{drc_filename(float(source_pdl), cl, int(qp))}",
                }
    return expected


def select_canary_variants(tile_index: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = non_empty_tiles(tile_index)
    if not tiles:
        raise DrcCorpusValidationError("No non-empty tiles available for canary selection")
    min_tile = min(tiles, key=lambda tile: (int(tile["point_count"]), str(tile["tile_id"])))
    max_tile = min(tiles, key=lambda tile: (-int(tile["point_count"]), str(tile["tile_id"])))
    if str(min_tile["tile_id"]) == str(max_tile["tile_id"]):
        raise DrcCorpusValidationError("Canary min/max tile selection collapsed to one tile")
    cl = int(profile["compression_level"])
    source_pdl = float(profile["canary_selection"]["source_pdl"])
    canaries: list[dict[str, Any]] = []
    for reason, tile in (("min_nonempty", min_tile), ("max_nonempty", max_tile)):
        for qp in profile["canary_selection"]["qp_values"]:
            vid = variant_id(str(tile["tile_id"]), source_pdl, cl, int(qp))
            canaries.append(
                {
                    "variant_id": vid,
                    "selection_reason": reason,
                    "tile_id": str(tile["tile_id"]),
                    "source_pdl": source_pdl,
                    "compression_level": cl,
                    "qp": int(qp),
                }
            )
    return canaries


def manifest_variants_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = manifest.get("variants", [])
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for variant in variants:
        vid = str(variant.get("variant_id", ""))
        if vid in by_id:
            duplicates.append(vid)
        by_id[vid] = variant
    if duplicates:
        raise DrcCorpusValidationError(f"Duplicate variant records: {duplicates[:5]}")
    return by_id


def validate_manifest_variant_matrix(manifest: dict[str, Any], expected: dict[str, dict[str, Any]]) -> None:
    observed = manifest_variants_by_id(manifest)
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    if missing or extra:
        raise DrcCorpusValidationError(f"Variant matrix mismatch; missing={missing[:5]}, extra={extra[:5]}")
    if len(observed) != EXPECTED_VARIANT_COUNT:
        raise DrcCorpusValidationError(f"Variant count mismatch: {len(observed)} != {EXPECTED_VARIANT_COUNT}")
    for vid, exp in expected.items():
        obs = observed[vid]
        for key in ("tile_id", "source_pdl", "compression_level", "qp", "drc_relpath"):
            if obs.get(key) != exp.get(key):
                raise DrcCorpusValidationError(f"{vid}: manifest {key} mismatch: {obs.get(key)} != {exp.get(key)}")


def assert_no_runtime_cost_claims(data: Any, path: str = "$") -> None:
    forbidden = {"D(i,v)", "decode_ms", "d_ms", "target_side_decode_cost", "target-side decode cost"}
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key) in forbidden:
                raise DrcCorpusValidationError(f"Forbidden runtime-cost claim key at {path}.{key}")
            assert_no_runtime_cost_claims(value, f"{path}.{key}")
    elif isinstance(data, list):
        for index, value in enumerate(data):
            assert_no_runtime_cost_claims(value, f"{path}[{index}]")


def quality_asset_for(tile_index: dict[str, Any], tile_id: str, source_pdl: float) -> dict[str, Any]:
    for tile in tile_index.get("tiles", []):
        if str(tile.get("tile_id")) != tile_id:
            continue
        for asset in tile.get("quality_assets", []):
            if float(asset.get("target_pdl")) == float(source_pdl):
                return asset
    raise DrcCorpusValidationError(f"Missing source asset for tile={tile_id} pdl={source_pdl}")


def run_decoder(decoder_path: Path, drc_path: Path, decoded_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(decoder_path), "-i", str(drc_path), "-o", str(decoded_path)],
        capture_output=True,
        text=True,
        shell=False,
    )
    return {
        "exit_code": completed.returncode,
        "stdout_summary": completed.stdout[-STDIO_LIMIT:],
        "stderr_summary": completed.stderr[-STDIO_LIMIT:],
    }


def validate_basic_decoded_pair(variant_id_value: str, source_ply: Path, decoded_ply: Path) -> dict[str, Any]:
    source = parse_ply_points(source_ply)
    decoded = parse_ply_points(decoded_ply)
    if decoded["vertex_count"] != source["vertex_count"]:
        raise DrcCorpusValidationError(f"{variant_id_value}: decoded vertex count mismatch")
    for index, point in enumerate(decoded["points"]):
        coords = (float(point["x"]), float(point["y"]), float(point["z"]))
        if not all(value == value and abs(value) != float("inf") for value in coords):
            raise DrcCorpusValidationError(f"{variant_id_value}: non-finite decoded coordinate at point {index}")
    if Counter(rgb_tuple(point) for point in source["points"]) != Counter(rgb_tuple(point) for point in decoded["points"]):
        raise DrcCorpusValidationError(f"{variant_id_value}: RGB triplet multiset mismatch")
    return {
        "decoded_vertex_count": int(decoded["vertex_count"]),
        "rgb_multiset_exact": True,
        "decoded_schema_fields": [name for _, name in decoded["properties"]],
    }


def validate(args: argparse.Namespace) -> dict[str, Any]:
    profile_path = Path(args.profile)
    profile = load_json(profile_path)
    artifact_root = Path(args.artifact_root or profile["output_root"])
    source_root = Path(profile["source_artifact_root"])
    manifest = load_json(artifact_root / "generation_manifest.json")
    source_tile_index = load_json(source_root / "frame_1051_tile_index.json")
    expected = build_expected_variants(source_tile_index, profile)
    if len(non_empty_tiles(source_tile_index)) != EXPECTED_NON_EMPTY_TILE_COUNT:
        raise DrcCorpusValidationError("Unexpected non-empty tile count in source tile index")
    validate_manifest_variant_matrix(manifest, expected)
    assert_no_runtime_cost_claims(manifest)

    if sha256_file(artifact_root / "profile_snapshot.json") == "":
        raise DrcCorpusValidationError("Unreachable empty hash check")
    profile_snapshot = load_json(artifact_root / "profile_snapshot.json")
    if str(profile_snapshot.get("profile_sha256", "")).upper() != sha256_file(profile_path):
        raise DrcCorpusValidationError("Profile snapshot hash mismatch")
    if profile_snapshot.get("profile") != profile:
        raise DrcCorpusValidationError("Profile snapshot content mismatch")

    observed_drc_files = {path.relative_to(artifact_root).as_posix() for path in artifact_root.rglob("*.drc")}
    expected_drc_files = {item["drc_relpath"] for item in expected.values()}
    if observed_drc_files != expected_drc_files:
        raise DrcCorpusValidationError(
            f"DRC file set mismatch; missing={sorted(expected_drc_files - observed_drc_files)[:5]}, "
            f"extra={sorted(observed_drc_files - expected_drc_files)[:5]}"
        )

    decoder_path = Path(manifest["decoder_path"])
    temp_dir = Path(tempfile.mkdtemp(prefix="pilot_drc_corpus_validate_"))
    variants_by_id = manifest_variants_by_id(manifest)
    canary_ids = {item["variant_id"] for item in select_canary_variants(source_tile_index, profile)}
    canary_hashes: dict[tuple[str, float], dict[int, str]] = {}
    report_variants: list[dict[str, Any]] = []
    try:
        for vid, exp in expected.items():
            variant = variants_by_id[vid]
            drc_path = artifact_root / variant["drc_relpath"]
            source_asset = quality_asset_for(source_tile_index, str(variant["tile_id"]), float(variant["source_pdl"]))
            source_ply = source_root / source_asset["relative_path"]
            if not drc_path.exists():
                raise DrcCorpusValidationError(f"{vid}: DRC missing: {drc_path}")
            if sha256_file(drc_path) != str(variant["drc_sha256"]).upper():
                raise DrcCorpusValidationError(f"{vid}: DRC SHA-256 mismatch")
            if drc_path.stat().st_size != int(variant["drc_file_size_bytes"]):
                raise DrcCorpusValidationError(f"{vid}: DRC file size mismatch")
            if sha256_file(source_ply) != str(variant["source_ply_sha256"]).upper():
                raise DrcCorpusValidationError(f"{vid}: source PLY SHA-256 mismatch")

            decoded_tmp = temp_dir / f"{vid}.decoded.ply"
            decoder_result = run_decoder(decoder_path, drc_path, decoded_tmp)
            if decoder_result["exit_code"] != 0:
                raise DrcCorpusValidationError(f"{vid}: decoder failed: {decoder_result['stderr_summary']}")
            basic = validate_basic_decoded_pair(vid, source_ply, decoded_tmp)
            record: dict[str, Any] = {"variant_id": vid, **basic}
            if vid in canary_ids:
                canary_result = validate_roundtrip_point_sets(
                    variant,
                    parse_ply_points(source_ply),
                    parse_ply_points(decoded_tmp),
                )
                record["canary_roundtrip"] = canary_result
                key = (str(variant["tile_id"]), float(variant["source_pdl"]))
                canary_hashes.setdefault(key, {})[int(variant["qp"])] = str(variant["drc_sha256"]).upper()
            decoded_tmp.unlink(missing_ok=True)
            report_variants.append(record)
        for key, hashes_by_qp in canary_hashes.items():
            values = [hashes_by_qp[qp] for qp in sorted(hashes_by_qp)]
            if len(values) != len(set(values)):
                raise DrcCorpusValidationError(f"Canary QP effect not observed for {key}: {hashes_by_qp}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    report = {
        "validation_passed": True,
        "artifact_root": artifact_root.as_posix(),
        "variant_count": len(report_variants),
        "canary_variant_count": len(canary_ids),
        "checks": [
            "manifest_matrix_complete",
            "drc_hash_and_size",
            "decode_all_drc",
            "decoded_schema_point_count_rgb_multiset",
            "canary_order_independent_geometry_and_local_rgb",
            "canary_qp_hash_effect",
        ],
    }
    write_json(artifact_root / "validation_report.json", report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate frame 1051 pilot DRC corpus.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE_PATH), help="DRC corpus profile JSON path.")
    parser.add_argument("--artifact-root", default=None, help="Override artifact root; defaults to profile output_root.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        report = validate(args)
    except (DrcCorpusValidationError, DracoProbeValidationError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"DRC corpus validation passed: {report['variant_count']} variants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
