import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_pilot_multquality_binary_tiles.py"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_pilot_multquality_binary_tiles", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PublishStagingRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator_module()

    def test_transient_permission_error_retries_then_publishes(self):
        with tempfile.TemporaryDirectory(prefix=".publish_retry_", dir=ROOT) as tmp:
            root = Path(tmp)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()
            (staging / "sentinel.txt").write_text("ok", encoding="utf-8")
            attempts = []

            def publish_once(source, target):
                attempts.append((source, target))
                if len(attempts) < 3:
                    raise PermissionError("transient lock")
                source.rename(target)

            sleep = mock.Mock()
            returned_attempts = self.generator.publish_staging(
                staging,
                final,
                publish_once=publish_once,
                sleep_func=sleep,
            )

            self.assertEqual(returned_attempts, 3)
            self.assertEqual(len(attempts), 3)
            self.assertEqual(sleep.call_count, 2)
            sleep.assert_has_calls(
                [
                    mock.call(self.generator.PUBLISH_RETRY_DELAY_SECONDS),
                    mock.call(self.generator.PUBLISH_RETRY_DELAY_SECONDS),
                ]
            )
            self.assertFalse(staging.exists())
            self.assertTrue(final.is_dir())
            self.assertEqual((final / "sentinel.txt").read_text(encoding="utf-8"), "ok")

    def test_persistent_permission_error_fails_after_twenty_attempts_and_cleans_staging(self):
        with tempfile.TemporaryDirectory(prefix=".publish_retry_", dir=ROOT) as tmp:
            root = Path(tmp)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()
            (staging / "sentinel.txt").write_text("ok", encoding="utf-8")
            attempts = []

            def publish_once(source, target):
                attempts.append((source, target))
                raise PermissionError("persistent lock")

            sleep = mock.Mock()
            with self.assertRaises(self.generator.MultiPdlGenerationError) as raised:
                self.generator.publish_staging(
                    staging,
                    final,
                    publish_once=publish_once,
                    sleep_func=sleep,
                )

            message = str(raised.exception)
            self.assertEqual(len(attempts), self.generator.PUBLISH_MAX_ATTEMPTS)
            self.assertEqual(sleep.call_count, self.generator.PUBLISH_MAX_ATTEMPTS - 1)
            self.assertIn(f"{self.generator.PUBLISH_MAX_ATTEMPTS} attempts", message)
            self.assertIn(str(staging), message)
            self.assertIn(str(final), message)
            self.assertFalse(final.exists())
            self.assertFalse(staging.exists())
            self.assertIn("staging cleanup succeeded", message)


if __name__ == "__main__":
    unittest.main()
