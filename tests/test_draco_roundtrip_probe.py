import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_draco_roundtrip_probe.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_draco_roundtrip_probe.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_draco_roundtrip_probe", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_draco_roundtrip_probe", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def record(x, y, z, red, green, blue):
    return {"x": float(x), "y": float(y), "z": float(z), "red": int(red), "green": int(green), "blue": int(blue)}


def point_set(points):
    return {
        "format": "binary_little_endian 1.0",
        "vertex_count": len(points),
        "properties": [("float", "x"), ("float", "y"), ("float", "z"), ("uchar", "red"), ("uchar", "green"), ("uchar", "blue")],
        "points": points,
    }


class DracoRoundTripProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner_module()
        cls.validator = load_validator_module()

    def test_encoder_command_builder_uses_only_active_draco_dimensions(self):
        argv = self.runner.build_encoder_argv(
            Path("draco_encoder.exe"),
            Path("source.ply"),
            Path("target.drc"),
            10,
            8,
            "-point_cloud",
        )
        self.assertIn("-point_cloud", argv)
        self.assertIn("-cl", argv)
        self.assertIn("10", argv)
        self.assertIn("-qp", argv)
        self.assertIn("8", argv)
        self.assertIn("-i", argv)
        self.assertIn("-o", argv)
        self.assertNotIn("-qc", argv)
        self.assertNotIn("-qg", argv)

    def test_representative_tile_selection_uses_min_max_and_lexicographic_ties(self):
        tile_index = {
            "non_empty_tile_count": 5,
            "tiles": [
                {"tile_id": "gx_2", "is_empty": False, "point_count": 10},
                {"tile_id": "gx_1", "is_empty": False, "point_count": 10},
                {"tile_id": "gx_4", "is_empty": False, "point_count": 99},
                {"tile_id": "gx_3", "is_empty": False, "point_count": 99},
                {"tile_id": "gx_empty", "is_empty": True, "point_count": 0},
                {"tile_id": "gx_mid", "is_empty": False, "point_count": 40},
            ],
        }
        selected = self.runner.select_representative_tiles(tile_index)
        self.assertEqual(selected[0]["selection_reason"], "min_nonempty")
        self.assertEqual(selected[0]["tile_id"], "gx_1")
        self.assertEqual(selected[0]["source_point_count"], 10)
        self.assertEqual(selected[1]["selection_reason"], "max_nonempty")
        self.assertEqual(selected[1]["tile_id"], "gx_3")
        self.assertEqual(selected[1]["source_point_count"], 99)

    def test_toolchain_hash_drift_fails_before_subprocess_stage(self):
        profile = {
            "expected_encoder_sha256": "A" * 64,
            "expected_decoder_sha256": "B" * 64,
        }
        with self.assertRaises(self.runner.DracoProbeError) as raised:
            self.runner.assert_toolchain_hashes(
                profile,
                Path("draco_encoder.exe"),
                Path("draco_decoder.exe"),
                "C" * 64,
                "B" * 64,
            )
        self.assertIn("draco_encoder SHA-256 drift", str(raised.exception))

    def test_matrix_generation_has_thirty_unique_variants(self):
        profile = {
            "candidate_source_pdls": [0.2, 0.4, 0.6, 0.8, 1.0],
            "candidate_qp_values": [8, 10, 12],
            "compression_level": 10,
        }
        selected = [
            {"selection_reason": "min_nonempty", "tile_id": "gx_min", "source_point_count": 5},
            {"selection_reason": "max_nonempty", "tile_id": "gx_max", "source_point_count": 100},
        ]
        source_tiles = {
            "gx_min": {
                "tile_id": "gx_min",
                "quality_assets": [{"target_pdl": q, "relative_path": f"min/{q}.ply"} for q in profile["candidate_source_pdls"]],
            },
            "gx_max": {
                "tile_id": "gx_max",
                "quality_assets": [{"target_pdl": q, "relative_path": f"max/{q}.ply"} for q in profile["candidate_source_pdls"]],
            },
        }
        variants = self.runner.build_probe_matrix(selected, source_tiles, profile)
        self.assertEqual(len(variants), 30)
        self.assertEqual(len({variant["variant_id"] for variant in variants}), 30)
        self.assertEqual({variant["tile_id"] for variant in variants}, {"gx_min", "gx_max"})
        self.assertEqual({variant["qp"] for variant in variants}, {8, 10, 12})
        self.assertEqual({variant["source_pdl"] for variant in variants}, {0.2, 0.4, 0.6, 0.8, 1.0})

    def validate_synthetic(self, source_points, decoded_points, qp=8):
        variant = {"variant_id": "synthetic_variant", "qp": qp}
        return self.validator.validate_roundtrip_point_sets(variant, point_set(source_points), point_set(decoded_points))

    def test_reordered_valid_pair_passes_order_independent_validation(self):
        source = [
            record(0, 0, 0, 10, 20, 30),
            record(10, 0, 0, 40, 50, 60),
            record(20, 0, 0, 70, 80, 90),
        ]
        decoded = [source[2].copy(), source[0].copy(), source[1].copy()]
        report = self.validate_synthetic(source, decoded)
        self.assertTrue(report["rgb_multiset_exact"])
        self.assertEqual(report["point_order_status"], "not_required_for_draco_roundtrip")
        self.assertEqual(report["local_rgb_association"]["mutual_unique_pair_count"], 3)

    def test_index_order_difference_is_not_failure_when_point_set_and_rgb_pairs_match(self):
        source = [
            record(0, 0, 0, 112, 105, 103),
            record(10, 0, 0, 201, 175, 153),
        ]
        decoded = [source[1].copy(), source[0].copy()]
        report = self.validate_synthetic(source, decoded)
        self.assertEqual(report["local_rgb_association"]["mutual_unique_pair_count"], 2)

    def test_global_rgb_multiset_mutation_fails(self):
        source = [
            record(0, 0, 0, 10, 20, 30),
            record(10, 0, 0, 40, 50, 60),
        ]
        decoded = [
            record(0, 0, 0, 10, 20, 30),
            record(10, 0, 0, 40, 50, 61),
        ]
        with self.assertRaises(self.validator.DracoProbeValidationError) as raised:
            self.validate_synthetic(source, decoded)
        self.assertIn("RGB triplet multiset mismatch", str(raised.exception))

    def test_local_rgb_association_failure_when_high_confidence_colors_are_swapped(self):
        source = [
            record(0, 0, 0, 10, 20, 30),
            record(10, 0, 0, 40, 50, 60),
        ]
        decoded = [
            record(0, 0, 0, 40, 50, 60),
            record(10, 0, 0, 10, 20, 30),
        ]
        with self.assertRaises(self.validator.DracoProbeValidationError) as raised:
            self.validate_synthetic(source, decoded)
        self.assertIn("high-confidence mutual-nearest RGB mismatch", str(raised.exception))

    def test_geometry_out_of_tolerance_fails(self):
        source = [
            record(0, 0, 0, 10, 20, 30),
            record(1, 0, 0, 40, 50, 60),
        ]
        decoded = [
            record(0, 0, 0, 10, 20, 30),
            record(1.1, 0, 0, 40, 50, 60),
        ]
        with self.assertRaises(self.validator.DracoProbeValidationError) as raised:
            self.validate_synthetic(source, decoded, qp=8)
        self.assertIn("has no counterpart within tolerance", str(raised.exception))

    def test_ambiguity_report_is_not_silent_or_full_identity_proof(self):
        source = [
            record(0, 0, 0, 10, 20, 30),
            record(0, 0, 0, 40, 50, 60),
        ]
        decoded = [
            record(0, 0, 0, 40, 50, 60),
            record(0, 0, 0, 10, 20, 30),
        ]
        report = self.validate_synthetic(source, decoded)
        local_rgb = report["local_rgb_association"]
        self.assertEqual(local_rgb["mutual_unique_pair_count"], 0)
        self.assertGreater(local_rgb["ambiguous_or_nonmutual_point_count"], 0)
        self.assertLess(local_rgb["mutual_unique_pair_coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()
