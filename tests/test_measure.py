import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.measure import execution_mode, normalize_arch


ROOT = Path(__file__).resolve().parents[1]
MEASURE = ROOT / "scripts" / "measure.py"


class ArchitectureTests(unittest.TestCase):
    def test_normalize_arch_accepts_linux_aliases(self):
        aliases = {
            "x86_64": "amd64",
            "AMD64": "amd64",
            "aarch64": "arm64",
            "ARM64": "arm64",
        }

        for supplied, expected in aliases.items():
            with self.subTest(supplied=supplied):
                self.assertEqual(normalize_arch(supplied), expected)

    def test_normalize_arch_rejects_an_unmeasured_architecture(self):
        with self.assertRaisesRegex(ValueError, "unsupported architecture"):
            normalize_arch("riscv64")

    def test_execution_mode_distinguishes_native_from_emulated(self):
        self.assertEqual(execution_mode("x86_64", "amd64"), "native")
        self.assertEqual(execution_mode("aarch64", "arm64"), "native")
        self.assertEqual(execution_mode("x86_64", "arm64"), "emulated")
        self.assertEqual(execution_mode("aarch64", "amd64"), "emulated")


class MeasurementCliTests(unittest.TestCase):
    def run_measure(self, output, command):
        env = os.environ.copy()
        env.update(
            {
                "GITHUB_RUN_ID": "12345",
                "GITHUB_RUN_ATTEMPT": "2",
                "GITHUB_SHA": "abc123",
                "ImageOS": "ubuntu24",
                "ImageVersion": "20260901.1",
            }
        )
        return subprocess.run(
            [
                sys.executable,
                str(MEASURE),
                "--output",
                str(output),
                "--workload",
                "smoke",
                "--phase",
                "target-execution",
                "--repetition",
                "2",
                "--expected-repetitions",
                "3",
                "--trial-class",
                "retained",
                "--runner-label",
                "ubuntu-24.04",
                "--host-arch",
                "x86_64",
                "--target-arch",
                "arm64",
                "--",
                *command,
            ],
            cwd=ROOT,
            env=env,
            check=False,
        )

    def read_only_record(self, output):
        lines = output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        return json.loads(lines[0])

    def test_success_streams_the_real_command_and_appends_a_complete_record(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "measurements.jsonl"

            completed = self.run_measure(
                output, [sys.executable, "-c", "print('measured command ran')"]
            )

            self.assertEqual(completed.returncode, 0)
            record = self.read_only_record(output)
            self.assertEqual(
                set(record),
                {
                    "schema_version",
                    "block_id",
                    "workload",
                    "phase",
                    "repetition",
                    "expected_repetitions",
                    "trial_class",
                    "runner_label",
                    "host_arch",
                    "target_arch",
                    "execution_mode",
                    "started_at",
                    "elapsed_seconds",
                    "exit_code",
                    "command",
                    "git_sha",
                    "runner_image_os",
                    "runner_image_version",
                },
            )
            expected_values = {
                "schema_version": 2,
                "block_id": "12345.2",
                "workload": "smoke",
                "phase": "target-execution",
                "repetition": 2,
                "expected_repetitions": 3,
                "trial_class": "retained",
                "runner_label": "ubuntu-24.04",
                "host_arch": "amd64",
                "target_arch": "arm64",
                "execution_mode": "emulated",
                "exit_code": 0,
                "git_sha": "abc123",
                "runner_image_os": "ubuntu24",
                "runner_image_version": "20260901.1",
                "command": [sys.executable, "-c", "print('measured command ran')"],
            }
            for key, expected in expected_values.items():
                with self.subTest(key=key):
                    self.assertEqual(record[key], expected)
            self.assertGreaterEqual(record["elapsed_seconds"], 0.0)
            self.assertRegex(record["started_at"], r"^\d{4}-\d{2}-\d{2}T")

    def test_failed_command_is_recorded_and_propagates_its_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "measurements.jsonl"

            completed = self.run_measure(
                output, [sys.executable, "-c", "raise SystemExit(7)"]
            )

            self.assertEqual(completed.returncode, 7)
            record = self.read_only_record(output)
            self.assertEqual(record["exit_code"], 7)
            self.assertEqual(record["execution_mode"], "emulated")

    def test_repetition_outside_the_declared_trial_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "command-ran"
            output = Path(directory) / "measurements.jsonl"
            command = [
                sys.executable,
                "-c",
                "from pathlib import Path; Path({!r}).write_text('ran')".format(
                    str(marker)
                ),
            ]
            env = os.environ.copy()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MEASURE),
                    "--output",
                    str(output),
                    "--workload",
                    "smoke",
                    "--phase",
                    "build-test",
                    "--repetition",
                    "3",
                    "--expected-repetitions",
                    "2",
                    "--trial-class",
                    "retained",
                    "--runner-label",
                    "ubuntu-24.04",
                    "--host-arch",
                    "x86_64",
                    "--target-arch",
                    "arm64",
                    "--",
                    *command,
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("repetition must be between 1 and 2", completed.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
