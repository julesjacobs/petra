from pathlib import Path
import sys
import tempfile
import unittest

from collect_stress_raw import artifact_guard


class ArtifactGuardTests(unittest.TestCase):
    def test_oversized_artifact_is_retained_and_child_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "partial.json"
            command = [sys.executable, "-c",
                       f"from pathlib import Path; import time; Path({str(artifact)!r}).write_bytes(b'x'*4096); time.sleep(30)"]
            self.assertEqual(artifact_guard(root, 1024, command), 125)
            self.assertEqual(artifact.stat().st_size, 4096)
            self.assertTrue((root / "artifact-limit.json").exists())

    def test_small_artifact_keeps_frontend_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "output"
            command = [sys.executable, "-c", f"from pathlib import Path; Path({str(artifact)!r}).write_text('ok')"]
            self.assertEqual(artifact_guard(root, 1024, command), 0)
            self.assertFalse((root / "artifact-limit.json").exists())


if __name__ == "__main__":
    unittest.main()
