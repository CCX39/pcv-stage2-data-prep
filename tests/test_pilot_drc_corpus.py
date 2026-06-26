import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


generator = load_module("generate_pilot_drc_corpus", "scripts/generate_pilot_drc_corpus.py")
validator = load_module("validate_pilot_drc_corpus", "scripts/validate_pilot_drc_corpus.py")


def synthetic_profile():
    return {
        "source_pdls": [0.2, 0.4, 0.6, 0.8, 1.0],
        "qp_values": [8, 10, 12],
        "compression_level": 10,
        "point_cloud_flag": "-point_cloud",
        "canary_selection": {"source_pdl": 1.0, "qp_values": [8, 10, 12]},
    }


def synthetic_tile_index(count=40):
    tiles = []
    for index in range(count):
        tiles.append(
            {
                "tile_id": f"gx_{index:02d}_gy_0_gz_0",
                "is_empty": False,
                "point_count": 100 + index,
                "quality_assets": [
                    {"target_pdl": pdl, "relative_path": f"tiles/t{index}/pdl_{pdl:.1f}.ply", "sha256": "A" * 64}
                    for pdl in [0.2, 0.4, 0.6, 0.8, 1.0]
                ],
            }
        )
    return {"tiles": tiles}


class PilotDrcCorpusTests(unittest.TestCase):
    def test_expected_matrix_has_600_variants(self):
        variants = generator.build_expected_variants(synthetic_tile_index(), synthetic_profile())
        self.assertEqual(len(variants), 600)
        self.assertEqual(len({item["variant_id"] for item in variants}), 600)

    def test_encoder_command_uses_only_active_codec_dimensions(self):
        argv = generator.build_encoder_argv(
            Path("draco_encoder.exe"),
            Path("source.ply"),
            Path("target.drc"),
            10,
            12,
            "-point_cloud",
        )
        self.assertIn("-point_cloud", argv)
        self.assertIn("-cl", argv)
        self.assertIn("10", argv)
        self.assertIn("-qp", argv)
        self.assertIn("12", argv)
        self.assertNotIn("-qc", argv)
        self.assertNotIn("-qg", argv)

    def test_output_root_existing_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(generator.DrcCorpusGenerationError):
                generator.assert_output_root_available(root)

    def test_toolchain_hash_drift_fails_before_subprocess(self):
        profile = {
            "expected_encoder_sha256": "0" * 64,
            "expected_decoder_sha256": "1" * 64,
        }
        with tempfile.TemporaryDirectory() as temp:
            encoder = Path(temp) / "encoder.exe"
            decoder = Path(temp) / "decoder.exe"
            encoder.write_bytes(b"encoder")
            decoder.write_bytes(b"decoder")
            with mock.patch("subprocess.run") as run_mock:
                with self.assertRaises(generator.DrcCorpusGenerationError):
                    generator.assert_toolchain_hashes(profile, encoder, decoder)
                run_mock.assert_not_called()

    def test_validator_detects_missing_and_duplicate_matrix(self):
        profile = synthetic_profile()
        expected = validator.build_expected_variants(synthetic_tile_index(), profile)
        observed = list(expected.values())
        missing_manifest = {"variants": observed[:-1]}
        with self.assertRaises(validator.DrcCorpusValidationError):
            validator.validate_manifest_variant_matrix(missing_manifest, expected)

        duplicate_manifest = {"variants": observed + [observed[0]]}
        with self.assertRaises(validator.DrcCorpusValidationError):
            validator.validate_manifest_variant_matrix(duplicate_manifest, expected)

    def test_canary_selection_uses_min_max_and_qp_triplets(self):
        tile_index = {
            "tiles": [
                {"tile_id": "b_tile", "is_empty": False, "point_count": 5},
                {"tile_id": "a_tile", "is_empty": False, "point_count": 5},
                {"tile_id": "z_tile", "is_empty": False, "point_count": 1000},
                {"tile_id": "y_tile", "is_empty": False, "point_count": 1000},
                {"tile_id": "empty", "is_empty": True, "point_count": 0},
            ]
        }
        canaries = validator.select_canary_variants(tile_index, synthetic_profile())
        self.assertEqual(len(canaries), 6)
        self.assertEqual({item["tile_id"] for item in canaries}, {"a_tile", "y_tile"})
        self.assertEqual({item["qp"] for item in canaries}, {8, 10, 12})
        self.assertEqual({item["source_pdl"] for item in canaries}, {1.0})

    def test_incomplete_staging_is_not_published(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()
            manifest = {"variants": []}
            with self.assertRaises(generator.DrcCorpusGenerationError):
                generator.publish_if_complete(staging, final, manifest, expected_variant_count=1)
            self.assertFalse(final.exists())
            self.assertTrue(staging.exists())


if __name__ == "__main__":
    unittest.main()
