import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKLOADS = ROOT / "workloads"


class FixtureManifestContractTests(unittest.TestCase):
    def test_real_workloads_are_immutable_https_fixtures(self):
        manifest = json.loads(
            (WORKLOADS / "fixtures.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            manifest,
            {
                "brotli": {
                    "filename": "brotli.tar.gz",
                    "sha256": "0afe09a53c8bad9861c8dd1fc1284308d54f19d2979ba3541cfdcc9b05fe360f",
                    "source_revision": "028fb5a23661f123017c060daa546b55cf4bde29",
                    "url": "https://codeload.github.com/google/brotli/tar.gz/028fb5a23661f123017c060daa546b55cf4bde29",
                },
                "cpython": {
                    "filename": "cpython.tgz",
                    "sha256": "62859805f6fdf25e2bcbf3fa3217801e1996887ca33e6a2af80674bdfa2dbe07",
                    "source_revision": "v3.14.7",
                    "url": "https://www.python.org/ftp/python/3.14.7/Python-3.14.7.tgz",
                },
            },
        )


class DockerfileContractTests(unittest.TestCase):
    FRONTEND = (
        "# syntax=docker/dockerfile:1.12@"
        "sha256:93bfd3b68c109427185cd78b4779fc82b484b0b7618e36d0f104d4d801e66d25"
    )

    def dockerfile(self, workload):
        return (WORKLOADS / workload / "Dockerfile").read_text(encoding="utf-8")

    def test_measured_builds_use_pinned_target_platform_toolchains_without_network(self):
        for workload in ("brotli", "cpython"):
            with self.subTest(workload=workload):
                dockerfile = self.dockerfile(workload)
                self.assertTrue(dockerfile.startswith(self.FRONTEND + "\n"))
                self.assertIn("FROM --platform=${TARGETPLATFORM}", dockerfile)
                for forbidden in ("curl ", "wget ", "apt-get", "pip install"):
                    self.assertNotIn(forbidden, dockerfile)

    def test_each_workload_retains_machine_readable_correctness_evidence(self):
        for workload in ("brotli", "cpython"):
            with self.subTest(workload=workload):
                dockerfile = self.dockerfile(workload)
                self.assertIn("/evidence/elf-header.txt", dockerfile)
                self.assertIn("/evidence/tests.txt", dockerfile)
                self.assertIn("/evidence/artifact-sha256.txt", dockerfile)
                self.assertIn("FROM scratch AS evidence", dockerfile)
                self.assertIn("COPY --from=benchmark /evidence/ /", dockerfile)

    def test_compilation_and_tests_use_the_published_four_vcpus(self):
        brotli = self.dockerfile("brotli")
        cpython = self.dockerfile("cpython")

        self.assertIn("build_ext --inplace -j 4", brotli)
        self.assertIn("make -j 4", cpython)
        self.assertIn("-m test -j 4", cpython)


if __name__ == "__main__":
    unittest.main()
