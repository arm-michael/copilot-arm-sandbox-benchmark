import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "benchmark.yml"


def load_workflow():
    ruby = (
        "require 'yaml'; require 'json'; "
        "puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), aliases: true))"
    )
    completed = subprocess.run(
        ["ruby", "-e", ruby, str(WORKFLOW)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


class WorkflowContractTests(unittest.TestCase):
    def test_matrix_compares_equal_size_public_x64_and_arm64_runners(self):
        workflow = load_workflow()
        job = workflow["jobs"]["benchmark"]

        self.assertEqual(job["runs-on"], "${{ matrix.treatment.runner }}")
        self.assertEqual(
            job["strategy"]["matrix"]["treatment"],
            [
                {
                    "name": "x64-qemu",
                    "runner": "ubuntu-24.04",
                    "host_arch": "amd64",
                },
                {
                    "name": "arm64-native",
                    "runner": "ubuntu-24.04-arm",
                    "host_arch": "arm64",
                },
            ],
        )
        self.assertEqual(job["env"]["TARGET_PLATFORM"], "linux/arm64")

    def test_qemu_is_pinned_scoped_to_x64_and_precedes_buildx(self):
        workflow = load_workflow()
        steps = workflow["jobs"]["benchmark"]["steps"]
        qemu_index = next(i for i, step in enumerate(steps) if step.get("id") == "qemu")
        buildx_index = next(
            i for i, step in enumerate(steps) if step.get("id") == "buildx"
        )
        qemu = steps[qemu_index]

        self.assertLess(qemu_index, buildx_index)
        self.assertEqual(qemu["if"], "matrix.treatment.name == 'x64-qemu'")
        self.assertEqual(
            qemu["uses"],
            "docker/setup-qemu-action@1f40c72289eff860ee54a304f1438e3cff362e0a",
        )
        self.assertEqual(qemu["with"]["platforms"], "arm64")
        self.assertEqual(
            qemu["with"]["image"],
            "docker.io/tonistiigi/binfmt:latest@sha256:400a4873b838d1b89194d982c45e5fb3cda4593fbfd7e08a02e76b03b21166f0",
        )

    def test_workload_is_measured_and_results_upload_even_after_failure(self):
        workflow = load_workflow()
        steps = workflow["jobs"]["benchmark"]["steps"]
        measured = next(step for step in steps if step.get("id") == "measure")
        upload = next(step for step in steps if step.get("id") == "upload")

        self.assertIn("scripts/measure.py", measured["run"])
        self.assertIn("--platform \"${TARGET_PLATFORM}\"", measured["run"])
        self.assertIn("--target benchmark", measured["run"])
        self.assertEqual(upload["if"], "always()")
        self.assertEqual(
            upload["uses"],
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        )


if __name__ == "__main__":
    unittest.main()
