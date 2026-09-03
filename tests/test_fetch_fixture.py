import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / "scripts" / "fetch_fixture.py"


class FetchFixtureCliTests(unittest.TestCase):
    def write_manifest(self, directory, source, expected_sha=None):
        payload = source.read_bytes()
        digest = expected_sha or hashlib.sha256(payload).hexdigest()
        manifest = Path(directory) / "fixtures.json"
        manifest.write_text(
            json.dumps(
                {
                    "demo": {
                        "url": source.as_uri(),
                        "sha256": digest,
                        "filename": "demo-source.tar.gz",
                    }
                }
            ),
            encoding="utf-8",
        )
        return manifest

    def run_fetch(self, manifest, destination, workload="demo"):
        return subprocess.run(
            [
                sys.executable,
                str(FETCH),
                "--manifest",
                str(manifest),
                workload,
                str(destination),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_matching_download_is_installed_under_the_manifest_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "upstream.tar.gz"
            source.write_bytes(b"pinned source archive")
            manifest = self.write_manifest(root, source)
            destination = root / "download"

            completed = self.run_fetch(manifest, destination)

            fetched = destination / "demo-source.tar.gz"
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(fetched.read_bytes(), b"pinned source archive")
            self.assertEqual(completed.stdout.strip(), str(fetched))

    def test_checksum_mismatch_fails_without_installing_the_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "upstream.tar.gz"
            source.write_bytes(b"tampered source archive")
            manifest = self.write_manifest(root, source, expected_sha="0" * 64)
            destination = root / "download"

            completed = self.run_fetch(manifest, destination)

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("SHA-256 mismatch", completed.stderr)
            self.assertFalse((destination / "demo-source.tar.gz").exists())
            self.assertEqual(list(destination.glob(".*.tmp")), [])

    def test_matching_cached_fixture_avoids_an_unavailable_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "upstream.tar.gz"
            source.write_bytes(b"cached source archive")
            manifest = self.write_manifest(root, source)
            destination = root / "download"
            destination.mkdir()
            cached = destination / "demo-source.tar.gz"
            cached.write_bytes(source.read_bytes())
            source.unlink()

            completed = self.run_fetch(manifest, destination)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(cached.read_bytes(), b"cached source archive")

    def test_unknown_workload_reports_available_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "upstream.tar.gz"
            source.write_bytes(b"source")
            manifest = self.write_manifest(root, source)

            completed = self.run_fetch(manifest, root / "download", "missing")

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unknown workload 'missing'", completed.stderr)
            self.assertIn("demo", completed.stderr)


if __name__ == "__main__":
    unittest.main()
