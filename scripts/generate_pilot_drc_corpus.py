#!/usr/bin/env python3
"""Generate the frame 1051 pilot DRC corpus from existing multi-PDL PLY assets.

This script is intentionally narrow: it creates 40 non-empty tiles * 5 source
PDLs * 3 qp values = 600 DRC files, then validates each DRC with a temporary
decode basic-integrity check before publishing the final artifact root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_draco_roundtrip_probe import DracoProbeValidationError, parse_ply_points, rgb_tuple


DEFAULT_PROFILE_PATH = Path("configs/pilot_drc_corpus.longdress_1051_g128_pdl5_qp3_cl10_v1.json")
EXPECTED_NON_EMPTY_TILES = 40
EXPECTED_VARIANT_COUNT = 600
PUBLISH_RETRY_ATTEMPTS = 20
PUBLISH_RETRY_SECONDS = 0.25
STDIO_LIMIT = 2000


class DrcCorpusGenerationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def qlabel(value: float) -> str:
    return f"{value:.1f}"


def drc_filename(source_pdl: float, compression_level: int, qp: int) -> str:
    return f"pdl_{qlabel(source_pdl)}_cl{compression_level}_qp{qp}.drc"


def variant_id(tile_id: str, source_pdl: float, compression_level: int, qp: int) -> str:
    return f"{tile_id}__pdl_{qlabel(source_pdl)}__cl{compression_level}__qp{qp}"


def resolve_command(command: str) -> Path:
    resolved = shutil.which(command)
    if not resolved:
        raise DrcCorpusGenerationError(f"Command not found on PATH: {command}")
    return Path(resolved).resolve()


def assert_toolchain_hashes(profile: dict[str, Any], encoder_path: Path, decoder_path: Path) -> dict[str, str]:
    observed_encoder = sha256_file(encoder_path)
    observed_decoder = sha256_file(decoder_path)
    expected_encoder = str(profile["expected_encoder_sha256"]).upper()
    expected_decoder = str(profile["expected_decoder_sha256"]).upper()
    if observed_encoder != expected_encoder:
        raise DrcCorpusGenerationError(
            f"draco_encoder SHA-256 mismatch: expected {expected_encoder}, observed {observed_encoder}, path={encoder_path}"
        )
    if observed_decoder != expected_decoder:
        raise DrcCorpusGenerationError(
            f"draco_decoder SHA-256 mismatch: expected {expected_decoder}, observed {observed_decoder}, path={decoder_path}"
        )
    return {"encoder_sha256": observed_encoder, "decoder_sha256": observed_decoder}


def resolve_and_check_toolchain(profile: dict[str, Any]) -> dict[str, Any]:
    encoder_path = resolve_command(str(profile["encoder_command"]))
    decoder_path = resolve_command(str(profile["decoder_command"]))
    hashes = assert_toolchain_hashes(profile, encoder_path, decoder_path)
    return {
        "encoder_path": str(encoder_path),
        "decoder_path": str(decoder_path),
        "encoder_sha256": hashes["encoder_sha256"],
        "decoder_sha256": hashes["decoder_sha256"],
    }


def assert_output_root_available(output_root: Path) -> None:
    if output_root.exists():
        raise DrcCorpusGenerationError(f"Output root already exists; refusing to overwrite: {output_root}")


def non_empty_tiles(tile_index: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = [tile for tile in tile_index.get("tiles", []) if not tile.get("is_empty")]
    tiles.sort(key=lambda item: str(item["tile_id"]))
    return tiles


def quality_asset_for(tile: dict[str, Any], source_pdl: float) -> dict[str, Any]:
    for asset in tile.get("quality_assets", []):
        if float(asset.get("target_pdl")) == float(source_pdl):
            return asset
    raise DrcCorpusGenerationError(f"Missing source PLY asset for tile={tile.get('tile_id')} pdl={source_pdl}")


def build_expected_variants(tile_index: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
    tiles = non_empty_tiles(tile_index)
    cl = int(profile["compression_level"])
    variants: list[dict[str, Any]] = []
    for tile in tiles:
        for source_pdl in profile["source_pdls"]:
            for qp in profile["qp_values"]:
                variants.append(
                    {
                        "variant_id": variant_id(str(tile["tile_id"]), float(source_pdl), cl, int(qp)),
                        "tile_id": str(tile["tile_id"]),
                        "source_pdl": float(source_pdl),
                        "compression_level": cl,
                        "qp": int(qp),
                    }
                )
    return variants


def build_encoder_argv(
    encoder_path: Path,
    source_ply: Path,
    target_drc: Path,
    compression_level: int,
    qp: int,
    point_cloud_flag: str,
) -> list[str]:
    argv = [
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
    if "-qc" in argv or "-qg" in argv:
        raise DrcCorpusGenerationError(f"Forbidden color-control flag in encoder argv: {argv}")
    return argv


def build_decoder_argv(decoder_path: Path, source_drc: Path, decoded_ply: Path) -> list[str]:
    return [str(decoder_path), "-i", str(source_drc), "-o", str(decoded_ply)]


def run_subprocess(argv: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(argv, capture_output=True, text=True, shell=False)
    elapsed = time.perf_counter() - started
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout_summary": completed.stdout[-STDIO_LIMIT:],
        "stderr_summary": completed.stderr[-STDIO_LIMIT:],
        "local_cli_elapsed_diagnostic_only": elapsed,
    }


def assert_basic_decode_integrity(
    source_ply: Path,
    decoded_ply: Path,
    source_parsed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = source_parsed or parse_ply_points(source_ply)
    decoded = parse_ply_points(decoded_ply)
    if decoded["vertex_count"] != source["vertex_count"]:
        raise DrcCorpusGenerationError(
            f"decoded vertex count mismatch for {decoded_ply}: {decoded['vertex_count']} != {source['vertex_count']}"
        )
    for index, point in enumerate(decoded["points"]):
        values = (float(point["x"]), float(point["y"]), float(point["z"]))
        if not all(value == value and abs(value) != float("inf") for value in values):
            raise DrcCorpusGenerationError(f"decoded PLY has non-finite coordinate at point {index}: {decoded_ply}")
    if Counter(rgb_tuple(point) for point in source["points"]) != Counter(rgb_tuple(point) for point in decoded["points"]):
        raise DrcCorpusGenerationError(f"RGB triplet multiset mismatch in temporary decode: {decoded_ply}")
    return {
        "basic_decode_integrity_pass": True,
        "decoded_vertex_count": int(decoded["vertex_count"]),
        "rgb_multiset_exact": True,
        "decoded_schema_fields": [name for _, name in decoded["properties"]],
    }


def publish_staging(staging_root: Path, output_root: Path) -> None:
    last_error: PermissionError | None = None
    for attempt in range(1, PUBLISH_RETRY_ATTEMPTS + 1):
        try:
            staging_root.replace(output_root)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt == PUBLISH_RETRY_ATTEMPTS:
                break
            time.sleep(PUBLISH_RETRY_SECONDS)
    raise DrcCorpusGenerationError(
        f"Failed to publish staging after {PUBLISH_RETRY_ATTEMPTS} attempts; "
        f"staging={staging_root}; target={output_root}; last_error={last_error}"
    )


def assert_staging_complete(staging_root: Path, expected_variant_count: int, manifest: dict[str, Any]) -> None:
    if not staging_root.exists():
        raise DrcCorpusGenerationError(f"Staging root does not exist: {staging_root}")
    variants = manifest.get("variants", [])
    if len(variants) != expected_variant_count:
        raise DrcCorpusGenerationError(f"Staging manifest variant count mismatch: {len(variants)} != {expected_variant_count}")
    drc_files = list(staging_root.rglob("*.drc"))
    if len(drc_files) != expected_variant_count:
        raise DrcCorpusGenerationError(f"Staging DRC count mismatch: {len(drc_files)} != {expected_variant_count}")


def publish_if_complete(staging_root: Path, output_root: Path, manifest: dict[str, Any], expected_variant_count: int) -> None:
    assert_staging_complete(staging_root, expected_variant_count, manifest)
    publish_staging(staging_root, output_root)


def remove_staging(staging_root: Path) -> None:
    if staging_root.exists():
        shutil.rmtree(staging_root)


def generate(args: argparse.Namespace) -> dict[str, Any]:
    profile_path = Path(args.profile)
    profile = load_json(profile_path)
    source_root = Path(profile["source_artifact_root"])
    output_root = Path(args.output_root or profile["output_root"])
    assert_output_root_available(output_root)

    source_manifest_path = source_root / "generation_manifest.json"
    source_tile_index_path = source_root / "frame_1051_tile_index.json"
    source_manifest = load_json(source_manifest_path)
    source_tile_index = load_json(source_tile_index_path)
    tiles = non_empty_tiles(source_tile_index)
    if len(tiles) != EXPECTED_NON_EMPTY_TILES:
        raise DrcCorpusGenerationError(f"Expected {EXPECTED_NON_EMPTY_TILES} non-empty tiles, observed {len(tiles)}")
    expected_variants = build_expected_variants(source_tile_index, profile)
    if len(expected_variants) != EXPECTED_VARIANT_COUNT:
        raise DrcCorpusGenerationError(f"Expected {EXPECTED_VARIANT_COUNT} variants, observed {len(expected_variants)}")

    toolchain = resolve_and_check_toolchain(profile)
    encoder_path = Path(toolchain["encoder_path"])
    decoder_path = Path(toolchain["decoder_path"])

    staging_root = output_root.parent / f".{output_root.name}.staging-{os.getpid()}-{int(time.time())}"
    temp_decode_dir = staging_root / "_tmp_decode"
    if staging_root.exists():
        raise DrcCorpusGenerationError(f"Unexpected staging root already exists: {staging_root}")

    manifest: dict[str, Any] = {
        "artifact_profile_id": profile["profile_id"],
        "stage": "2C.0-manual-generation-target",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_id": profile["dataset_id"],
        "frame_id": profile["frame_id"],
        "grid_profile_id": profile["grid_profile_id"],
        "source_artifact_root": profile["source_artifact_root"],
        "source_artifact_profile_id": profile["source_artifact_profile_id"],
        "source_artifact_manifest_sha256": sha256_file(source_manifest_path),
        "source_tile_index_sha256": sha256_file(source_tile_index_path),
        "profile_path": profile_path.as_posix(),
        "profile_sha256": sha256_file(profile_path),
        "output_root": output_root.as_posix(),
        "codec_id": profile["codec_id"],
        "point_cloud_flag": profile["point_cloud_flag"],
        "compression_level": profile["compression_level"],
        "source_pdls": profile["source_pdls"],
        "qp_values": profile["qp_values"],
        "encoder_path": toolchain["encoder_path"],
        "encoder_sha256": toolchain["encoder_sha256"],
        "decoder_path": toolchain["decoder_path"],
        "decoder_sha256": toolchain["decoder_sha256"],
        "expected_non_empty_tile_count": EXPECTED_NON_EMPTY_TILES,
        "expected_variant_count": EXPECTED_VARIANT_COUNT,
        "variants": [],
    }
    try:
        staging_root.mkdir(parents=True)
        temp_decode_dir.mkdir(parents=True)
        write_json(staging_root / "profile_snapshot.json", {"profile_sha256": sha256_file(profile_path), "profile": profile})
        write_json(
            staging_root / "source_artifact_manifest_snapshot.json",
            {"source_artifact_manifest_sha256": sha256_file(source_manifest_path), "manifest": source_manifest},
        )
        write_json(
            staging_root / "source_tile_index_snapshot.json",
            {"source_tile_index_sha256": sha256_file(source_tile_index_path), "tile_index": source_tile_index},
        )

        aggregate_by_pdl: dict[str, dict[str, Any]] = defaultdict(lambda: {"drc_count": 0, "total_drc_file_size_bytes": 0})
        aggregate_by_qp: dict[str, dict[str, Any]] = defaultdict(lambda: {"drc_count": 0, "total_drc_file_size_bytes": 0})
        for tile in tiles:
            tile_id = str(tile["tile_id"])
            tile_dir = staging_root / "tiles" / tile_id
            tile_dir.mkdir(parents=True, exist_ok=True)
            for source_pdl in profile["source_pdls"]:
                source_asset = quality_asset_for(tile, float(source_pdl))
                source_ply = source_root / source_asset["relative_path"]
                if not source_ply.exists():
                    raise DrcCorpusGenerationError(f"Source PLY missing: {source_ply}")
                source_sha = sha256_file(source_ply)
                if source_sha.lower() != str(source_asset["sha256"]).lower():
                    raise DrcCorpusGenerationError(f"Source PLY hash mismatch: {source_ply}")
                source_parsed = parse_ply_points(source_ply)
                if int(source_parsed["vertex_count"]) != int(source_asset["retained_point_count"]):
                    raise DrcCorpusGenerationError(f"Source point count mismatch: {source_ply}")
                for qp in profile["qp_values"]:
                    qp_int = int(qp)
                    cl = int(profile["compression_level"])
                    vid = variant_id(tile_id, float(source_pdl), cl, qp_int)
                    target_drc = tile_dir / drc_filename(float(source_pdl), cl, qp_int)
                    decoded_tmp = temp_decode_dir / f"{vid}.decoded.ply"
                    encoder_argv = build_encoder_argv(encoder_path, source_ply, target_drc, cl, qp_int, str(profile["point_cloud_flag"]))
                    encoder_result = run_subprocess(encoder_argv)
                    if encoder_result["exit_code"] != 0:
                        raise DrcCorpusGenerationError(
                            f"Encoder failed for tile={tile_id} pdl={source_pdl} qp={qp_int}: {encoder_result['stderr_summary']}"
                        )
                    if not target_drc.exists() or target_drc.stat().st_size <= 0:
                        raise DrcCorpusGenerationError(f"DRC was not created or is empty: {target_drc}")
                    decoder_argv = build_decoder_argv(decoder_path, target_drc, decoded_tmp)
                    decoder_result = run_subprocess(decoder_argv)
                    if decoder_result["exit_code"] != 0:
                        raise DrcCorpusGenerationError(
                            f"Decoder failed for tile={tile_id} pdl={source_pdl} qp={qp_int}: {decoder_result['stderr_summary']}"
                        )
                    integrity = assert_basic_decode_integrity(source_ply, decoded_tmp, source_parsed)
                    decoded_tmp.unlink(missing_ok=True)
                    drc_size = target_drc.stat().st_size
                    drc_sha = sha256_file(target_drc)
                    pdl_key = qlabel(float(source_pdl))
                    qp_key = str(qp_int)
                    aggregate_by_pdl[pdl_key]["drc_count"] += 1
                    aggregate_by_pdl[pdl_key]["total_drc_file_size_bytes"] += drc_size
                    aggregate_by_qp[qp_key]["drc_count"] += 1
                    aggregate_by_qp[qp_key]["total_drc_file_size_bytes"] += drc_size
                    manifest["variants"].append(
                        {
                            "variant_id": vid,
                            "tile_id": tile_id,
                            "source_pdl": float(source_pdl),
                            "codec_id": profile["codec_id"],
                            "point_cloud_flag": profile["point_cloud_flag"],
                            "compression_level": cl,
                            "qp": qp_int,
                            "source_ply_relpath": source_asset["relative_path"],
                            "source_ply_sha256": source_sha,
                            "source_ply_file_size_bytes": source_ply.stat().st_size,
                            "source_point_count": int(source_asset["retained_point_count"]),
                            "drc_relpath": relpath(target_drc, staging_root),
                            "drc_sha256": drc_sha,
                            "drc_file_size_bytes": drc_size,
                            "encoder_path": toolchain["encoder_path"],
                            "encoder_sha256": toolchain["encoder_sha256"],
                            "decoder_path": toolchain["decoder_path"],
                            "decoder_sha256": toolchain["decoder_sha256"],
                            "encoder_command": encoder_result,
                            "decoder_command": decoder_result,
                            **integrity,
                        }
                    )

        manifest["generated_drc_file_count"] = len(manifest["variants"])
        manifest["basic_decode_integrity_checked_variant_count"] = len(manifest["variants"])
        manifest["drc_files_by_pdl"] = dict(sorted(aggregate_by_pdl.items()))
        manifest["drc_files_by_qp"] = dict(sorted(aggregate_by_qp.items(), key=lambda item: int(item[0])))
        manifest["generation_summary"] = {
            "non_empty_tile_count": len(tiles),
            "source_pdl_count": len(profile["source_pdls"]),
            "qp_count": len(profile["qp_values"]),
            "expected_variant_count": EXPECTED_VARIANT_COUNT,
            "generated_drc_file_count": len(manifest["variants"]),
            "decoded_ply_retained": False,
            "basic_decode_integrity_pass": True,
        }
        write_json(staging_root / "generation_manifest.json", manifest)
        write_json(staging_root / "generation_summary.json", manifest["generation_summary"])
        shutil.rmtree(temp_decode_dir, ignore_errors=True)
        publish_if_complete(staging_root, output_root, manifest, EXPECTED_VARIANT_COUNT)
        return manifest
    except Exception:
        if staging_root.exists():
            shutil.rmtree(temp_decode_dir, ignore_errors=True)
            remove_staging(staging_root)
        raise


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate frame 1051 pilot DRC corpus.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE_PATH), help="DRC corpus profile JSON path.")
    parser.add_argument("--output-root", default=None, help="Override output root; defaults to profile output_root.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        manifest = generate(args)
    except (DrcCorpusGenerationError, DracoProbeValidationError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "Generated DRC corpus: "
        f"{manifest['generation_summary']['generated_drc_file_count']} DRC files at {manifest['output_root']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
