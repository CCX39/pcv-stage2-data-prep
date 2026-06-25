#!/usr/bin/env python3
"""Run the stage 2B Draco round-trip probe for two representative tiles.

The runner reads the existing frame 1051 multi-PDL binary PLY artifact root,
selects the min/max non-empty tiles from metadata, and performs 30 controlled
PLY -> DRC -> PLY round-trips. It does not generate the full DRC corpus,
asset catalog, XML, BIN, or Stage2Input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "configs" / "draco_roundtrip_probe.longdress_1051_g128_pdl5_qp3_cl10_v1.json"
DEFAULT_SOURCE_ROOT = ROOT / "artifacts" / "pilot_1051_g128_tilelocal_pdl5_v1"
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "draco_roundtrip_probe_1051_g128_pdl5_qp3_cl10_v1"

EXPECTED_PDLS = [0.2, 0.4, 0.6, 0.8, 1.0]
EXPECTED_QPS = [8, 10, 12]
EXPECTED_VARIANT_COUNT = 30
STDIO_SUMMARY_LIMIT = 4000
PUBLISH_MAX_ATTEMPTS = 20
PUBLISH_RETRY_DELAY_SECONDS = 0.25


class DracoProbeError(RuntimeError):
    pass


def as_posix(path: Path) -> str:
    return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DracoProbeError(f"Required JSON file not found: {path}")
    if path.stat().st_size == 0:
        raise DracoProbeError(f"Required JSON file is empty: {path}")
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


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def qlabel(value: float) -> str:
    return f"{value:.1f}"


def pdl_asset_key(value: float) -> str:
    return qlabel(value)


def sanitize_stdio(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= STDIO_SUMMARY_LIMIT:
        return text
    return text[:STDIO_SUMMARY_LIMIT] + "\n...[truncated]"


def load_and_check_profile(profile_path: Path) -> dict[str, Any]:
    profile = load_json(profile_path)
    if profile.get("candidate_source_pdls") != EXPECTED_PDLS:
        raise DracoProbeError("probe profile candidate_source_pdls must be [0.2, 0.4, 0.6, 0.8, 1.0]")
    if profile.get("candidate_qp_values") != EXPECTED_QPS:
        raise DracoProbeError("probe profile candidate_qp_values must be [8, 10, 12]")
    if profile.get("point_cloud_flag") != "-point_cloud":
        raise DracoProbeError("probe profile point_cloud_flag must be -point_cloud")
    if int(profile.get("compression_level")) != 10:
        raise DracoProbeError("probe profile compression_level must be 10")
    forbidden_fields = {"qc", "color_quantization_bits"}
    forbidden_values = {"-qc", "-qg"}

    def check_no_forbidden_color_controls(value: Any, path: str = "profile") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in forbidden_fields:
                    raise DracoProbeError(f"probe profile must not contain forbidden field: {path}.{key}")
                check_no_forbidden_color_controls(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check_no_forbidden_color_controls(child, f"{path}[{index}]")
        elif isinstance(value, str) and value.lower() in forbidden_values:
            raise DracoProbeError(f"probe profile must not contain forbidden CLI value: {path}={value}")

    check_no_forbidden_color_controls(profile)
    return profile


def resolve_command(command_name: str) -> Path:
    resolved = shutil.which(command_name)
    if resolved is None:
        raise DracoProbeError(f"Could not resolve command on PATH: {command_name}")
    return Path(resolved).resolve()


def assert_toolchain_hashes(
    profile: dict[str, Any],
    encoder_path: Path,
    decoder_path: Path,
    observed_encoder_sha256: str,
    observed_decoder_sha256: str,
) -> None:
    expected_encoder = str(profile["expected_encoder_sha256"]).upper()
    expected_decoder = str(profile["expected_decoder_sha256"]).upper()
    if observed_encoder_sha256.upper() != expected_encoder:
        raise DracoProbeError(
            "draco_encoder SHA-256 drift: "
            f"path={encoder_path}; expected={expected_encoder}; observed={observed_encoder_sha256.upper()}"
        )
    if observed_decoder_sha256.upper() != expected_decoder:
        raise DracoProbeError(
            "draco_decoder SHA-256 drift: "
            f"path={decoder_path}; expected={expected_decoder}; observed={observed_decoder_sha256.upper()}"
        )


def resolve_and_check_toolchain(profile: dict[str, Any]) -> dict[str, Any]:
    encoder_path = resolve_command(profile["encoder_command"])
    decoder_path = resolve_command(profile["decoder_command"])
    encoder_sha = sha256_file(encoder_path)
    decoder_sha = sha256_file(decoder_path)
    assert_toolchain_hashes(profile, encoder_path, decoder_path, encoder_sha, decoder_sha)
    return {
        "encoder": {
            "command": profile["encoder_command"],
            "path": str(encoder_path),
            "sha256": encoder_sha,
            "file_size_bytes": encoder_path.stat().st_size,
        },
        "decoder": {
            "command": profile["decoder_command"],
            "path": str(decoder_path),
            "sha256": decoder_sha,
            "file_size_bytes": decoder_path.stat().st_size,
        },
    }


def non_empty_tiles(tile_index: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = [tile for tile in tile_index["tiles"] if not tile.get("is_empty")]
    if len(tiles) != int(tile_index.get("non_empty_tile_count", -1)):
        raise DracoProbeError("tile index non-empty count does not match tile records")
    return tiles


def select_representative_tiles(tile_index: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = non_empty_tiles(tile_index)
    if not tiles:
        raise DracoProbeError("tile index contains no non-empty tile")
    min_tile = sorted(tiles, key=lambda tile: (int(tile["point_count"]), tile["tile_id"]))[0]
    max_tile = sorted(tiles, key=lambda tile: (-int(tile["point_count"]), tile["tile_id"]))[0]
    if min_tile["tile_id"] == max_tile["tile_id"]:
        raise DracoProbeError("representative tile selection resolved to the same tile")
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


def asset_by_pdl(tile_record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets = tile_record.get("quality_assets", [])
    return {pdl_asset_key(float(asset["target_pdl"])): asset for asset in assets}


def variant_id(tile_id: str, source_pdl: float, compression_level: int, qp: int) -> str:
    return f"{tile_id}__pdl_{qlabel(source_pdl)}__cl{compression_level}__qp{qp}"


def drc_filename(source_pdl: float, compression_level: int, qp: int) -> str:
    return f"pdl_{qlabel(source_pdl)}_cl{compression_level}_qp{qp}.drc"


def decoded_filename(source_pdl: float, compression_level: int, qp: int) -> str:
    return f"pdl_{qlabel(source_pdl)}_cl{compression_level}_qp{qp}.decoded.ply"


def build_encoder_argv(
    encoder_path: Path,
    source_ply: Path,
    target_drc: Path,
    compression_level: int,
    qp: int,
    point_cloud_flag: str = "-point_cloud",
) -> list[str]:
    return [
        str(encoder_path),
        point_cloud_flag,
        "-i",
        str(source_ply),
        "-o",
        str(target_drc),
        "-cl",
        str(compression_level),
        "-qp",
        str(qp),
    ]


def build_decoder_argv(decoder_path: Path, source_drc: Path, target_ply: Path) -> list[str]:
    return [str(decoder_path), "-i", str(source_drc), "-o", str(target_ply)]


def build_probe_matrix(
    selected_tiles: list[dict[str, Any]],
    source_tiles_by_id: dict[str, dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    compression_level = int(profile["compression_level"])
    for selection in selected_tiles:
        tile_id = selection["tile_id"]
        if tile_id not in source_tiles_by_id:
            raise DracoProbeError(f"selected tile not present in source tile index: {tile_id}")
        assets = asset_by_pdl(source_tiles_by_id[tile_id])
        for source_pdl in profile["candidate_source_pdls"]:
            key = pdl_asset_key(float(source_pdl))
            if key not in assets:
                raise DracoProbeError(f"{tile_id}: missing source PDL asset metadata for {key}")
            for qp in profile["candidate_qp_values"]:
                vid = variant_id(tile_id, float(source_pdl), compression_level, int(qp))
                if vid in seen:
                    raise DracoProbeError(f"duplicate probe variant_id: {vid}")
                seen.add(vid)
                variants.append(
                    {
                        "variant_id": vid,
                        "selection_reason": selection["selection_reason"],
                        "tile_id": tile_id,
                        "source_point_count": selection["source_point_count"],
                        "source_pdl": float(source_pdl),
                        "compression_level": compression_level,
                        "qp": int(qp),
                        "source_asset": assets[key],
                    }
                )
    if len(variants) != EXPECTED_VARIANT_COUNT:
        raise DracoProbeError(f"expected {EXPECTED_VARIANT_COUNT} variants, got {len(variants)}")
    return variants


def run_subprocess(argv: list[str]) -> tuple[int, str, str, float]:
    started = time.perf_counter()
    completed = subprocess.run(argv, capture_output=True, text=True, shell=False)
    elapsed = time.perf_counter() - started
    return completed.returncode, sanitize_stdio(completed.stdout), sanitize_stdio(completed.stderr), elapsed


def rename_staging_once(staging_root: Path, artifact_root: Path) -> None:
    staging_root.rename(artifact_root)


def publish_staging(
    staging_root: Path,
    artifact_root: Path,
    *,
    publish_once=rename_staging_once,
    sleep_func=time.sleep,
    max_attempts: int = PUBLISH_MAX_ATTEMPTS,
    retry_delay_seconds: float = PUBLISH_RETRY_DELAY_SECONDS,
) -> int:
    last_error: PermissionError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            publish_once(staging_root, artifact_root)
            return attempt
        except PermissionError as exc:
            last_error = exc
            if attempt < max_attempts:
                sleep_func(retry_delay_seconds)
    raise DracoProbeError(
        "Could not publish Draco probe staging root by rename after "
        f"{max_attempts} attempts; staging path: {staging_root}; target path: {artifact_root}; "
        f"last PermissionError: {last_error}"
    )


def publish_staging_with_copy_fallback(staging_root: Path, artifact_root: Path) -> dict[str, Any]:
    try:
        attempts = publish_staging(staging_root, artifact_root)
        return {"publish_method": "rename", "rename_attempts": attempts, "staging_cleanup_warning": None}
    except DracoProbeError as rename_error:
        if artifact_root.exists():
            raise
        try:
            shutil.copytree(staging_root, artifact_root)
        except Exception as copy_error:
            if artifact_root.exists():
                try:
                    shutil.rmtree(artifact_root)
                except Exception as cleanup_error:
                    raise DracoProbeError(
                        f"{rename_error}; copytree fallback failed: {copy_error}; "
                        f"partial final root cleanup failed: {artifact_root}; cleanup error: {cleanup_error}"
                    ) from cleanup_error
            raise DracoProbeError(f"{rename_error}; copytree fallback failed: {copy_error}") from copy_error

        cleanup_warning = None
        try:
            shutil.rmtree(staging_root)
        except Exception as cleanup_error:
            cleanup_warning = f"published final root, but staging cleanup failed: {staging_root}; cleanup error: {cleanup_error}"
            print(f"WARNING: {cleanup_warning}", file=sys.stderr)
        return {"publish_method": "copytree_after_rename_permission_error", "rename_attempts": PUBLISH_MAX_ATTEMPTS, "staging_cleanup_warning": cleanup_warning}


def run(args: argparse.Namespace) -> dict[str, Any]:
    profile_path = Path(args.probe_profile)
    source_root = Path(args.source_root)
    artifact_root = Path(args.artifact_root)
    if artifact_root.exists():
        raise DracoProbeError(f"Probe artifact root already exists; refusing overwrite: {artifact_root}")
    if not source_root.is_dir():
        raise DracoProbeError(f"Source multi-PDL artifact root missing: {source_root}")

    profile = load_and_check_profile(profile_path)
    source_manifest_path = source_root / "generation_manifest.json"
    source_tile_index_path = source_root / "frame_1051_tile_index.json"
    source_manifest = load_json(source_manifest_path)
    source_tile_index = load_json(source_tile_index_path)
    if source_manifest.get("artifact_profile_id") != profile["source_artifact_profile_id"]:
        raise DracoProbeError("source artifact profile id does not match probe profile")
    if source_tile_index.get("dataset_id") != profile["dataset_id"] or int(source_tile_index.get("frame_id")) != int(profile["frame_id"]):
        raise DracoProbeError("source tile index dataset/frame does not match probe profile")

    toolchain = resolve_and_check_toolchain(profile)
    encoder_path = Path(toolchain["encoder"]["path"])
    decoder_path = Path(toolchain["decoder"]["path"])
    selected_tiles = select_representative_tiles(source_tile_index)
    source_tiles_by_id = {tile["tile_id"]: tile for tile in source_tile_index["tiles"]}
    variants = build_probe_matrix(selected_tiles, source_tiles_by_id, profile)

    parent = artifact_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging_root = parent / f".{artifact_root.name}.staging_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
    if staging_root.exists():
        raise DracoProbeError(f"Staging root already exists: {staging_root}")
    staging_root.mkdir(parents=True)

    try:
        probe_profile_sha = sha256_file(profile_path)
        source_manifest_sha = sha256_file(source_manifest_path)
        source_tile_index_sha = sha256_file(source_tile_index_path)
        write_json(staging_root / "probe_profile_snapshot.json", {"probe_profile_sha256": probe_profile_sha, "probe_profile": profile})
        write_json(
            staging_root / "source_artifact_manifest_snapshot.json",
            {"source_artifact_manifest_sha256": source_manifest_sha, "source_artifact_manifest": source_manifest},
        )
        write_json(
            staging_root / "source_tile_index_snapshot.json",
            {"source_tile_index_sha256": source_tile_index_sha, "source_tile_index": source_tile_index},
        )
        write_json(
            staging_root / "probe_tile_selection.json",
            {
                "source_tile_index_sha256": source_tile_index_sha,
                "selection_rule": profile["representative_tile_selection"],
                "selected_tiles": selected_tiles,
            },
        )

        variant_records: list[dict[str, Any]] = []
        generated_drc_count = 0
        generated_decoded_count = 0
        for variant in variants:
            tile_id = variant["tile_id"]
            source_pdl = float(variant["source_pdl"])
            qp = int(variant["qp"])
            compression_level = int(variant["compression_level"])
            source_asset = variant["source_asset"]
            source_relpath = source_asset["relative_path"]
            source_ply = source_root / source_relpath
            if not source_ply.is_file():
                raise DracoProbeError(f"{variant['variant_id']}: source PLY missing: {source_ply}")
            source_sha = sha256_file(source_ply)
            if source_sha.lower() != str(source_asset["sha256"]).lower():
                raise DracoProbeError(f"{variant['variant_id']}: source PLY SHA-256 mismatch")

            tile_dir = staging_root / "tiles" / tile_id
            tile_dir.mkdir(parents=True, exist_ok=True)
            drc_path = tile_dir / drc_filename(source_pdl, compression_level, qp)
            decoded_path = tile_dir / decoded_filename(source_pdl, compression_level, qp)
            encoder_argv = build_encoder_argv(
                encoder_path,
                source_ply,
                drc_path,
                compression_level,
                qp,
                profile["point_cloud_flag"],
            )
            if any(arg in {"-qc", "-qg"} for arg in encoder_argv):
                raise DracoProbeError(f"{variant['variant_id']}: forbidden color quantization arg in encoder argv")
            enc_code, enc_stdout, enc_stderr, enc_elapsed = run_subprocess(encoder_argv)
            if enc_code != 0:
                raise DracoProbeError(
                    f"{variant['variant_id']}: draco_encoder failed with exit code {enc_code}; stderr={enc_stderr}"
                )
            if not drc_path.is_file():
                raise DracoProbeError(f"{variant['variant_id']}: encoder did not create DRC: {drc_path}")
            generated_drc_count += 1

            decoder_argv = build_decoder_argv(decoder_path, drc_path, decoded_path)
            dec_code, dec_stdout, dec_stderr, dec_elapsed = run_subprocess(decoder_argv)
            if dec_code != 0:
                raise DracoProbeError(
                    f"{variant['variant_id']}: draco_decoder failed with exit code {dec_code}; stderr={dec_stderr}"
                )
            if not decoded_path.is_file():
                raise DracoProbeError(f"{variant['variant_id']}: decoder did not create decoded PLY: {decoded_path}")
            generated_decoded_count += 1

            variant_records.append(
                {
                    "variant_id": variant["variant_id"],
                    "tile_id": tile_id,
                    "selection_reason": variant["selection_reason"],
                    "source_point_count": variant["source_point_count"],
                    "source_pdl": source_pdl,
                    "codec_id": profile["codec_id"],
                    "point_cloud_mode": True,
                    "point_cloud_flag": profile["point_cloud_flag"],
                    "compression_level": compression_level,
                    "qp": qp,
                    "source_ply_relpath": source_relpath,
                    "source_ply_sha256": source_sha,
                    "source_ply_file_size_bytes": source_ply.stat().st_size,
                    "encoder": {
                        "argv": encoder_argv,
                        "exit_code": enc_code,
                        "stdout_summary": enc_stdout,
                        "stderr_summary": enc_stderr,
                        "local_cli_elapsed_diagnostic_only": enc_elapsed,
                    },
                    "decoder": {
                        "argv": decoder_argv,
                        "exit_code": dec_code,
                        "stdout_summary": dec_stdout,
                        "stderr_summary": dec_stderr,
                        "local_cli_elapsed_diagnostic_only": dec_elapsed,
                    },
                    "drc_relpath": rel(drc_path, staging_root),
                    "drc_sha256": sha256_file(drc_path),
                    "drc_file_size_bytes": drc_path.stat().st_size,
                    "decoded_ply_relpath": rel(decoded_path, staging_root),
                    "decoded_ply_sha256": sha256_file(decoded_path),
                    "decoded_ply_file_size_bytes": decoded_path.stat().st_size,
                    "provenance_kind": "draco_roundtrip_probe_variant",
                }
            )

        if generated_drc_count != EXPECTED_VARIANT_COUNT or generated_decoded_count != EXPECTED_VARIANT_COUNT:
            raise DracoProbeError("generated file counts do not match the 30-variant probe matrix")

        generation_manifest = {
            "artifact_profile_id": profile["profile_id"],
            "generation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "stage": "2B",
            "dataset_id": profile["dataset_id"],
            "frame_id": profile["frame_id"],
            "grid_profile_id": profile["grid_profile_id"],
            "source_artifact_root": as_posix(source_root),
            "target_artifact_root": as_posix(artifact_root),
            "source_artifact_profile_id": profile["source_artifact_profile_id"],
            "source_artifact_manifest_sha256": source_manifest_sha,
            "source_tile_index_sha256": source_tile_index_sha,
            "probe_profile_path": as_posix(profile_path),
            "probe_profile_sha256": probe_profile_sha,
            "toolchain": toolchain,
            "codec_id": profile["codec_id"],
            "point_cloud_flag": profile["point_cloud_flag"],
            "compression_level": profile["compression_level"],
            "position_quantization_flag": profile["position_quantization_flag"],
            "candidate_source_pdls": profile["candidate_source_pdls"],
            "candidate_qp_values": profile["candidate_qp_values"],
            "selected_tiles": selected_tiles,
            "expected_variant_count": EXPECTED_VARIANT_COUNT,
            "generated_drc_file_count": generated_drc_count,
            "generated_decoded_ply_file_count": generated_decoded_count,
            "variants": variant_records,
            "generation_script_path": as_posix(Path(__file__).resolve()),
            "generation_script_sha256": sha256_file(Path(__file__).resolve()),
            "python_version": sys.version,
            "non_claims": [
                "not the full 600-file frame 1051 DRC corpus",
                "not formal asset catalog",
                "not Stage2Input",
                "not target-side decode-cost measurement",
                "not DRC-aware Q_base measurement",
                "not Pareto pruning",
            ],
        }
        write_json(staging_root / "generation_manifest.json", generation_manifest)
        write_json(staging_root / "validation_report.json", {"passed": False, "status": "pending_independent_validation"})
        publish_result = publish_staging_with_copy_fallback(staging_root, artifact_root)
        final_manifest_path = artifact_root / "generation_manifest.json"
        final_manifest = load_json(final_manifest_path)
        final_manifest["publish_result"] = publish_result
        write_json(final_manifest_path, final_manifest)
        generation_manifest["publish_result"] = publish_result
        return generation_manifest
    except Exception as original_error:
        if staging_root.exists() and not artifact_root.exists():
            try:
                shutil.rmtree(staging_root)
            except Exception as cleanup_error:
                raise DracoProbeError(
                    f"Probe generation failed: {original_error}; staging cleanup failed; "
                    f"residual staging path: {staging_root}; cleanup error: {cleanup_error}"
                ) from cleanup_error
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    return parser.parse_args()


def main() -> int:
    try:
        manifest = run(parse_args())
    except DracoProbeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "artifact_profile_id": manifest["artifact_profile_id"],
                "target_artifact_root": manifest["target_artifact_root"],
                "selected_tiles": manifest["selected_tiles"],
                "generated_drc_file_count": manifest["generated_drc_file_count"],
                "generated_decoded_ply_file_count": manifest["generated_decoded_ply_file_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
