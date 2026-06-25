#!/usr/bin/env python3
"""Validate the frozen tile-local PDL sampling profile against reference vectors.

This script intentionally does not read PLY files and does not generate assets.
It only checks deterministic index sampling semantics.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


MASK32 = 0xFFFFFFFF
RNG_INCREMENT = 0x6D2B79F5
SEED_MIX_MULTIPLIER = 16777619
QUALITY_LEVELS = [0.2, 0.4, 0.6, 0.8, 1.0]


class ValidationError(Exception):
    """Raised when profile or reference vector validation fails."""


def uint32(value: int) -> int:
    return value & MASK32


def imul32(left: int, right: int) -> int:
    return uint32((left & MASK32) * (right & MASK32))


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


def shuffled_indices(count: int, seed: int) -> list[int]:
    indices = list(range(count))
    random = create_seeded_rng(seed)
    for index in range(count - 1, 0, -1):
        swap_index = math.floor(random() * (index + 1))
        indices[index], indices[swap_index] = indices[swap_index], indices[index]
    return indices


def canonical_seed_identity(profile: dict[str, Any], vector: dict[str, Any]) -> str:
    fields = profile["seed_identity_fields"]
    values: dict[str, Any] = {
        "sampling_profile_id": vector["sampling_profile_id"],
        "dataset_id": vector["dataset_id"],
        "frame_id": vector["frame_id"],
        "grid_profile_id": vector["grid_profile_id"],
        "tile_id": vector["tile_id"],
    }
    return "|".join(f"{field}={values[field]}" for field in fields)


def derive_quality_seed(base_seed: int, seed_identity: str) -> int:
    hash_value = uint32(base_seed)
    for byte in seed_identity.encode("utf-8"):
        hash_value = imul32(hash_value ^ byte, SEED_MIX_MULTIPLIER)
    return hash_value


def target_count(source_point_count: int, quality_level: float) -> int:
    if quality_level == 1.0:
        return source_point_count
    return max(1, math.floor(source_point_count * quality_level))


def selected_indices_by_pdl(source_point_count: int, seed: int) -> dict[str, list[int]]:
    permutation = shuffled_indices(source_point_count, seed)
    selected: dict[str, list[int]] = {}
    for quality_level in QUALITY_LEVELS:
        key = quality_key(quality_level)
        if quality_level == 1.0:
            selected[key] = list(range(source_point_count))
        else:
            retained_count = target_count(source_point_count, quality_level)
            selected[key] = sorted(permutation[:retained_count])
    return selected


def quality_key(quality_level: float) -> str:
    return f"{quality_level:.1f}"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def assert_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValidationError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_ratio(label: str, actual: float, expected: float) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValidationError(f"{label}: expected {expected!r}, got {actual!r}")


def validate_profile(profile: dict[str, Any]) -> None:
    assert_equal("quality_levels", profile["quality_levels"], QUALITY_LEVELS)
    assert_equal("sampling_scope", profile["sampling_scope"], "tile_local")
    assert_equal("base_seed", profile["base_seed"], 20260530)
    assert_equal("seed_excludes_quality_level", profile["seed_excludes_quality_level"], True)
    assert_equal(
        "sampling_method",
        profile["sampling_method"],
        "deterministic_seeded_permutation_prefix_sampling",
    )
    forbidden = set(profile["seed_identity_canonicalization"]["forbidden_identity_fields"])
    if "target_pdl" not in forbidden or "quality_level" not in forbidden:
        raise ValidationError("profile must explicitly forbid PDL/quality level in seed identity")
    if any("pdl" in field.lower() or "quality" in field.lower() for field in profile["seed_identity_fields"]):
        raise ValidationError("seed_identity_fields must not include PDL or quality level")


def validate_vector(profile: dict[str, Any], vector: dict[str, Any]) -> None:
    case_id = vector["case_id"]
    source_point_count = int(vector["source_point_count"])
    base_seed = int(vector["base_seed"])
    if source_point_count <= 0:
        raise ValidationError(f"{case_id}: source_point_count must be positive")

    assert_equal(f"{case_id} sampling_profile_id", vector["sampling_profile_id"], profile["sampling_profile_id"])
    assert_equal(f"{case_id} dataset_id", vector["dataset_id"], profile["dataset_id"])
    assert_equal(f"{case_id} frame_id", vector["frame_id"], profile["frame_id"])
    assert_equal(f"{case_id} grid_profile_id", vector["grid_profile_id"], profile["grid_profile_id"])
    assert_equal(f"{case_id} base_seed", base_seed, profile["base_seed"])

    seed_identity = canonical_seed_identity(profile, vector)
    assert_equal(f"{case_id} seed_identity", seed_identity, vector["seed_identity"])
    identity_keys = [part.split("=", 1)[0] for part in seed_identity.split("|")]
    if any(key in {"target_pdl", "quality_level", "target_quality_level"} for key in identity_keys):
        raise ValidationError(f"{case_id}: seed identity unexpectedly includes a PDL/quality field")

    derived_seed = derive_quality_seed(base_seed, seed_identity)
    assert_equal(
        f"{case_id} expected_derived_quality_seed",
        derived_seed,
        int(vector["expected_derived_quality_seed"]),
    )

    expected_counts = vector["expected_retained_point_counts"]
    expected_indices = vector["expected_selected_source_indices_by_pdl"]
    expected_ratios = vector["expected_actual_retained_ratios"]
    actual_indices = selected_indices_by_pdl(source_point_count, derived_seed)

    previous_set: set[int] | None = None
    for quality_level in QUALITY_LEVELS:
        key = quality_key(quality_level)
        actual_count = target_count(source_point_count, quality_level)
        assert_equal(f"{case_id} retained count {key}", actual_count, int(expected_counts[key]))
        if quality_level == 1.0:
            assert_equal(f"{case_id} pdl 1.0 count", actual_count, source_point_count)
        else:
            expected_count = max(1, math.floor(source_point_count * quality_level))
            assert_equal(f"{case_id} pdl {key} count rule", actual_count, expected_count)

        indices = actual_indices[key]
        assert_equal(f"{case_id} selected indices {key}", indices, expected_indices[key])
        assert_equal(f"{case_id} selected length {key}", len(indices), actual_count)
        if indices != sorted(indices):
            raise ValidationError(f"{case_id}: selected indices for {key} are not strictly ascending")
        if len(indices) != len(set(indices)):
            raise ValidationError(f"{case_id}: selected indices for {key} contain duplicates")
        if any(index < 0 or index >= source_point_count for index in indices):
            raise ValidationError(f"{case_id}: selected indices for {key} outside [0, N-1]")

        current_set = set(indices)
        if previous_set is not None and not previous_set.issubset(current_set):
            raise ValidationError(f"{case_id}: nested property failed before {key}")
        previous_set = current_set

        ratio = actual_count / source_point_count
        assert_ratio(f"{case_id} actual retained ratio {key}", ratio, float(expected_ratios[key]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampling-profile", required=True, type=Path)
    parser.add_argument("--reference-vectors", required=True, type=Path)
    args = parser.parse_args()

    try:
        profile = load_json(args.sampling_profile)
        vectors_doc = load_json(args.reference_vectors)
        vectors = vectors_doc.get("vectors", [])
        if not vectors:
            raise ValidationError("reference vector file contains no vectors")

        validate_profile(profile)
        for vector in vectors:
            validate_vector(profile, vector)

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, ValidationError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        "PASS: tile-local sampling reference validation succeeded "
        f"for {len(vectors)} case(s); profile={profile['sampling_profile_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
