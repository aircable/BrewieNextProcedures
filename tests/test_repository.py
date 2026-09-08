import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bundle import build
from validate import validate


class RepositoryTests(unittest.TestCase):
    def test_source_is_valid(self):
        self.assertEqual(validate(), [])

    def test_bundle_is_reproducible_and_flat(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            archive_a = build(Path(first))
            archive_b = build(Path(second))
            self.assertEqual(
                hashlib.sha256(archive_a.read_bytes()).hexdigest(),
                hashlib.sha256(archive_b.read_bytes()).hexdigest(),
            )
            with tarfile.open(archive_a, "r:gz") as archive:
                names = archive.getnames()
                self.assertTrue(any(name.endswith("/programs/beer_brewing.yml") for name in names))
                self.assertTrue(any(name.endswith("/programs/lme_brewing.yml") for name in names))
                self.assertTrue(any(name.endswith("/programs/cleaning_short.yml") for name in names))
                self.assertTrue(any(name.endswith("/programs/prepare_brew.yml") for name in names))
                self.assertTrue(any(name.endswith("/catalog/programs.yml") for name in names))
                self.assertFalse(any("procedures/brewing" in name for name in names))
                self.assertFalse(any(".backups" in name for name in names))
                manifest_member = next(name for name in names if name.endswith("/bundle-manifest.json"))
                manifest = json.load(archive.extractfile(manifest_member))
                self.assertEqual(manifest["entrypoints"]["brew"], "programs/beer_brewing.yml")

    def test_release_tag_matches_version(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_tag.py"), "v0.2.0"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
