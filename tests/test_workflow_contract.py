import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "benchmark.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def load_yaml(path):
    ruby = (
        "require 'yaml'; require 'json'; "
        "puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), aliases: true))"
    )
    completed = subprocess.run(
        ["ruby", "-e", ruby, str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


def load_workflow():
    return load_yaml(WORKFLOW)


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
        self.assertEqual(job["env"]["REPETITIONS"], "${{ inputs.repetitions }}")
        self.assertEqual(job["env"]["TRIAL_CLASS"], "${{ inputs.trial_class }}")

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
        buildx = steps[buildx_index]
        self.assertEqual(buildx["with"]["version"], "v0.37.0")
        self.assertIn(
            "image=moby/buildkit:v0.33.0@sha256:6c2fa84a6b61ccd72899dde4239f8d5717f05f9a8ca6f3cad185fb1a95a94de3",
            buildx["with"]["driver-opts"],
        )

    def test_workload_is_measured_and_results_upload_even_after_failure(self):
        workflow = load_workflow()
        steps = workflow["jobs"]["benchmark"]["steps"]
        measured = next(step for step in steps if step.get("id") == "measure")
        upload = next(step for step in steps if step.get("id") == "upload")

        self.assertIn("scripts/measure.py", measured["run"])
        self.assertIn("--platform \"${TARGET_PLATFORM}\"", measured["run"])
        self.assertIn("--target benchmark", measured["run"])
        self.assertIn('--expected-repetitions "${REPETITIONS}"', measured["run"])
        self.assertIn('--trial-class "${TRIAL_CLASS}"', measured["run"])
        self.assertNotIn("${{ inputs.repetitions }}", measured["run"])
        self.assertEqual(upload["if"], "always()")
        self.assertEqual(
            upload["uses"],
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        )
        self.assertIn("evidence/", upload["with"]["path"])

    def test_cached_benchmark_outputs_are_exported_as_evidence_and_job_timing_is_finalized(self):
        workflow = load_workflow()
        steps = workflow["jobs"]["benchmark"]["steps"]
        evidence = next(step for step in steps if step.get("id") == "evidence")
        finalize = next(step for step in steps if step.get("id") == "finalize")

        self.assertIn("--target evidence", evidence["run"])
        self.assertIn("--output type=local", evidence["run"])
        self.assertEqual(finalize["if"], "always()")
        self.assertIn("job-elapsed-seconds", finalize["run"])
        self.assertIn("binfmt-version", finalize["run"])

    def test_every_treatment_records_intent_before_checkout_and_measures_fixture_fetch(self):
        workflow = load_workflow()
        steps = workflow["jobs"]["benchmark"]["steps"]
        attempt = next(step for step in steps if step.get("id") == "attempt")
        fetch = next(step for step in steps if step.get("id") == "fetch")
        finalize = next(step for step in steps if step.get("id") == "finalize")

        self.assertLess(steps.index(attempt), 1)
        self.assertIn('"schema_version": 2', attempt["run"])
        self.assertIn('"phase": "attempt"', attempt["run"])
        self.assertIn("benchmark-attempt.jsonl", attempt["run"])
        self.assertIn("--phase fetch", fetch["run"])
        self.assertIn("scripts/measure.py", fetch["run"])
        self.assertIn("benchmark-attempt.jsonl", finalize["run"])

    def test_ci_runs_unit_tests_and_checksum_pinned_actionlint(self):
        workflow = load_yaml(CI_WORKFLOW)
        job = workflow["jobs"]["checks"]
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        checkout = next(step for step in job["steps"] if "uses" in step)

        self.assertEqual(job["runs-on"], "ubuntu-24.04")
        self.assertEqual(checkout["with"]["fetch-depth"], 2)
        self.assertIn("python3 -m unittest discover -s tests -v", commands)
        self.assertIn("actionlint_1.7.12_linux_amd64.tar.gz", commands)
        self.assertIn(
            "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
            commands,
        )

    def test_container_shell_expansion_has_scoped_shellcheck_suppression(self):
        workflow_text = WORKFLOW.read_text()
        inner_shell_command = (
            "sh -c 'test \"$(uname -m)\" = aarch64 && "
            "dd if=/dev/zero bs=1M count=64 2>/dev/null | sha256sum'"
        )

        self.assertIn(
            "# Expansion is intentionally delayed until sh runs inside the container.\n"
            "          # shellcheck disable=SC2016\n"
            "          python3 scripts/measure.py",
            workflow_text,
        )
        self.assertIn(inner_shell_command, workflow_text)


if __name__ == "__main__":
    unittest.main()
