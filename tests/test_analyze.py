import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.analyze import bootstrap_ci, paired_speedups, vm_medians


ROOT = Path(__file__).resolve().parents[1]
ANALYZE = ROOT / "scripts" / "analyze.py"


def record(block, mode, seconds, repetition=1, exit_code=0, workload="brotli"):
    return {
        "schema_version": 1,
        "block_id": block,
        "workload": workload,
        "phase": "build-test",
        "repetition": repetition,
        "runner_label": (
            "ubuntu-24.04" if mode == "emulated" else "ubuntu-24.04-arm"
        ),
        "host_arch": "amd64" if mode == "emulated" else "arm64",
        "target_arch": "arm64",
        "execution_mode": mode,
        "started_at": "2026-09-03T10:00:00Z",
        "elapsed_seconds": seconds,
        "exit_code": exit_code,
        "command": ["benchmark"],
        "git_sha": "abc123",
        "runner_image_os": "ubuntu24",
        "runner_image_version": "20260901.1",
    }


class AnalysisTests(unittest.TestCase):
    def sample_records(self):
        return [
            record("block-1", "emulated", 10, 1),
            record("block-1", "emulated", 12, 2),
            record("block-1", "emulated", 100, 3),
            record("block-1", "native", 2, 1),
            record("block-1", "native", 3, 2),
            record("block-1", "native", 4, 3),
            record("block-2", "emulated", 20),
            record("block-2", "native", 4),
            record("incomplete", "native", 1),
            record("failed", "emulated", 1, exit_code=9),
            record("failed", "native", 1),
            record("mixed", "emulated", 9, 1),
            record("mixed", "emulated", 10, 2, exit_code=3),
            record("mixed", "native", 2),
        ]

    def test_vm_medians_reduce_repetitions_and_exclude_failures(self):
        medians = vm_medians(self.sample_records())
        by_key = {
            (row["block_id"], row["execution_mode"]): row for row in medians
        }

        self.assertEqual(by_key[("block-1", "emulated")]["elapsed_seconds"], 12)
        self.assertEqual(by_key[("block-1", "emulated")]["repetitions"], 3)
        self.assertEqual(by_key[("block-1", "native")]["elapsed_seconds"], 3)
        self.assertNotIn(("failed", "emulated"), by_key)
        self.assertNotIn(("mixed", "emulated"), by_key)

    def test_paired_speedups_require_both_treatments_in_the_same_block(self):
        pairs = paired_speedups(self.sample_records())

        self.assertEqual(len(pairs), 2)
        self.assertEqual([row["block_id"] for row in pairs], ["block-1", "block-2"])
        self.assertEqual([row["speedup"] for row in pairs], [4.0, 5.0])
        self.assertNotIn("incomplete", {row["block_id"] for row in pairs})
        self.assertNotIn("failed", {row["block_id"] for row in pairs})
        self.assertNotIn("mixed", {row["block_id"] for row in pairs})

    def test_bootstrap_interval_is_deterministic_and_contains_the_median(self):
        first = bootstrap_ci([4.0, 5.0], samples=2000, seed=20260903)
        second = bootstrap_ci([4.0, 5.0], samples=2000, seed=20260903)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first[0], 4.0)
        self.assertLessEqual(first[1], 5.0)
        self.assertLessEqual(first[0], 4.5)
        self.assertGreaterEqual(first[1], 4.5)


class AnalysisCliTests(unittest.TestCase):
    def test_cli_writes_a_summary_and_consolidated_observation_csv(self):
        records = AnalysisTests().sample_records()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "raw" / "artifact"
            nested.mkdir(parents=True)
            raw = nested / "results.jsonl"
            raw.write_text(
                "".join(json.dumps(row) + "\n" for row in records),
                encoding="utf-8",
            )
            markdown = root / "RESULTS.md"
            output_csv = root / "results.csv"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ANALYZE),
                    str(root / "raw"),
                    "--markdown",
                    str(markdown),
                    "--csv",
                    str(output_csv),
                    "--bootstrap-samples",
                    "2000",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = markdown.read_text(encoding="utf-8")
            self.assertIn("Brotli", report)
            self.assertIn("2 paired blocks", report)
            self.assertIn("4.50x", report)
            self.assertIn("4.47x", report)
            with output_csv.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(records))
            self.assertEqual(rows[0]["block_id"], "block-1")


if __name__ == "__main__":
    unittest.main()
