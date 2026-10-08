"""Runs import-linter if it is installed. Skipped (not passed) otherwise."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("lint-imports"), "import-linter not installed: contracts NOT verified")
class ImportContracts(unittest.TestCase):
    def test_contracts_hold(self):
        r = subprocess.run(["lint-imports"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_violation_is_caught(self):
        bad = ROOT / "src" / "deepaira" / "engine" / "_violation_probe.py"
        bad.write_text("import django\n")
        try:
            r = subprocess.run(["lint-imports"], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, "engine importing django must break the build")
        finally:
            bad.unlink()


if __name__ == "__main__":
    unittest.main()
