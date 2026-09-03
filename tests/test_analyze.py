import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.analyze import (
    bootstrap_ci,
    paired_speedups,
    pairing_analysis,
    render_markdown,
    vm_medians,
)


ROOT = Path(__file__).resolve().parents[1]
ANALYZE = ROOT / "scripts" / "analyze.py"


def record(
    block,
    mode,
    seconds,
    repetition=1,
    exit_code=0,
    workload="brotli",
    expected_repetitions=1,
    trial_class="retained",
    phase="build-test",
    git_sha="abc123",
):
    return {
        "schema_version": 2,
        "block_id": block,
        "workload": workload,
        "phase": phase,
        "repetition": repetition,
        "expected_repetitions": expected_repetitions,
        "trial_class": trial_class,
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
        "git_sha": git_sha,
        "runner_image_os": "ubuntu24",
        "runner_image_version": "20260901.1",
    }


class AnalysisTests(unittest.TestCase):
    def sample_records(self):
        records = [
            record("block-1", "emulated", 10, 1, expected_repetitions=3),
            record("block-1", "emulated", 12, 2, expected_repetitions=3),
            record("block-1", "emulated", 100, 3, expected_repetitions=3),
            record("block-1", "native", 2, 1, expected_repetitions=3),
            record("block-1", "native", 3, 2, expected_repetitions=3),
            record("block-1", "native", 4, 3, expected_repetitions=3),
            record("block-2", "emulated", 20),
            record("block-2", "native", 4),
            record("incomplete", "native", 1),
            record("failed", "emulated", 1, exit_code=9),
            record("failed", "native", 1),
            record("mixed", "emulated", 9, 1),
            record(
                "mixed",
                "emulated",
                10,
                2,
                exit_code=3,
                expected_repetitions=2,
            ),
            record("mixed", "native", 2),
            record(
                "pilot",
                "emulated",
                100,
                trial_class="pilot",
            ),
            record("pilot", "native", 1, trial_class="pilot"),
            record("prepare", "emulated", 100, phase="prepare"),
            record("prepare", "native", 1, phase="prepare"),
            record(
                "missing-repetition",
                "emulated",
                8,
                1,
                expected_repetitions=2,
            ),
            record(
                "missing-repetition",
                "native",
                2,
                1,
                expected_repetitions=2,
            ),
            record("duplicate", "emulated", 8),
            record("duplicate", "emulated", 9),
            record("duplicate", "native", 2),
            record("mismatched-count", "emulated", 8),
            record(
                "mismatched-count",
                "native",
                2,
                1,
                expected_repetitions=2,
            ),
            record("never-built", "emulated", 0, phase="attempt"),
            record("never-built", "native", 0, phase="attempt"),
            record("fetch-failed", "emulated", 0, phase="attempt"),
            record("fetch-failed", "native", 0, phase="attempt"),
            record("fetch-failed", "emulated", 1, exit_code=6, phase="fetch"),
            record("fetch-failed", "native", 1, phase="fetch"),
            record(
                "mismatched-count",
                "native",
                3,
                2,
                expected_repetitions=2,
            ),
        ]
        for block in ("block-1", "block-2"):
            expected_repetitions = 3 if block == "block-1" else 1
            for mode in ("emulated", "native"):
                records.append(
                    record(
                        block,
                        mode,
                        0,
                        phase="verification",
                        expected_repetitions=expected_repetitions,
                    )
                )
        return records

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
        self.assertNotIn("pilot", {row["block_id"] for row in pairs})
        self.assertNotIn("prepare", {row["block_id"] for row in pairs})
        self.assertNotIn("missing-repetition", {row["block_id"] for row in pairs})
        self.assertNotIn("duplicate", {row["block_id"] for row in pairs})
        self.assertNotIn("mismatched-count", {row["block_id"] for row in pairs})

    def test_mislabeled_treatment_is_rejected_instead_of_entering_results(self):
        bad = record("bad", "native", 1)
        bad["runner_label"] = "ubuntu-24.04"

        with self.assertRaisesRegex(ValueError, "runner_label"):
            vm_medians([bad])

    def test_attempts_that_never_reach_primary_timing_are_excluded_with_setup_failures(self):
        pairs, exclusions = pairing_analysis(self.sample_records())
        reasons = {row["block_id"]: row["reason"] for row in exclusions}

        self.assertEqual(len(pairs), 2)
        self.assertIn("never-built", reasons)
        self.assertIn("missing valid treatment", reasons["never-built"])
        self.assertIn("fetch-failed", reasons)
        self.assertIn("emulated fetch failure", reasons["fetch-failed"])

    def test_pair_requires_successful_post_timing_verification_for_both_treatments(self):
        records = [
            record("verified", "emulated", 10),
            record("verified", "native", 2),
            record("verified", "emulated", 0, phase="verification"),
            record("verified", "native", 0, phase="verification", exit_code=1),
        ]

        pairs, exclusions = pairing_analysis(records)

        self.assertEqual(pairs, [])
        self.assertIn("native verification failure", exclusions[0]["reason"])

    def test_pair_with_missing_post_timing_verification_is_excluded(self):
        records = [
            record("missing-verification", "emulated", 10),
            record("missing-verification", "native", 2),
            record("missing-verification", "emulated", 0, phase="verification"),
        ]

        pairs, exclusions = pairing_analysis(records)

        self.assertEqual(pairs, [])
        self.assertIn("missing native post-timing verification", exclusions[0]["reason"])

    def test_pair_requires_one_shared_nonempty_harness_sha(self):
        records = [
            record("sha-mismatch", "emulated", 10, git_sha="aaa"),
            record("sha-mismatch", "native", 2, git_sha="bbb"),
            record("sha-mismatch", "emulated", 0, phase="verification", git_sha="aaa"),
            record("sha-mismatch", "native", 0, phase="verification", git_sha="bbb"),
        ]

        pairs, exclusions = pairing_analysis(records)

        self.assertEqual(pairs, [])
        self.assertIn("different git_sha", exclusions[0]["reason"])

    def test_pair_rejects_blank_or_whitespace_only_harness_sha(self):
        for git_sha in ("", "   "):
            with self.subTest(git_sha=repr(git_sha)):
                records = [
                    record("blank-sha", "emulated", 10, git_sha=git_sha),
                    record("blank-sha", "native", 2, git_sha=git_sha),
                    record(
                        "blank-sha",
                        "emulated",
                        0,
                        phase="verification",
                        git_sha=git_sha,
                    ),
                    record(
                        "blank-sha",
                        "native",
                        0,
                        phase="verification",
                        git_sha=git_sha,
                    ),
                ]

                pairs, exclusions = pairing_analysis(records)

                self.assertEqual(pairs, [])
                self.assertIn("blank git_sha", exclusions[0]["reason"])

    def test_pair_rejects_duplicate_or_mismatched_verification_records(self):
        duplicate = [
            record("duplicate-verification", "emulated", 10),
            record("duplicate-verification", "native", 2),
            record("duplicate-verification", "emulated", 0, phase="verification"),
            record("duplicate-verification", "emulated", 0, phase="verification"),
            record("duplicate-verification", "native", 0, phase="verification"),
        ]
        mismatched_count = [
            record(
                "verification-count",
                "emulated",
                10,
                expected_repetitions=2,
            ),
            record(
                "verification-count",
                "emulated",
                11,
                repetition=2,
                expected_repetitions=2,
            ),
            record(
                "verification-count",
                "native",
                2,
                expected_repetitions=2,
            ),
            record(
                "verification-count",
                "native",
                3,
                repetition=2,
                expected_repetitions=2,
            ),
            record(
                "verification-count",
                "emulated",
                0,
                phase="verification",
                expected_repetitions=1,
            ),
            record(
                "verification-count",
                "native",
                0,
                phase="verification",
                expected_repetitions=2,
            ),
        ]

        _, duplicate_exclusions = pairing_analysis(duplicate)
        _, count_exclusions = pairing_analysis(mismatched_count)

        self.assertIn("duplicate emulated", duplicate_exclusions[0]["reason"])
        self.assertIn("verification repetition count", count_exclusions[0]["reason"])

    def test_incomplete_or_malformed_schema_is_rejected(self):
        missing_command = record("bad", "native", 1)
        missing_command.pop("command")
        invalid_elapsed = record("bad", "native", 1)
        invalid_elapsed["elapsed_seconds"] = "fast"

        with self.assertRaisesRegex(ValueError, "command"):
            vm_medians([missing_command])
        with self.assertRaisesRegex(ValueError, "elapsed_seconds"):
            vm_medians([invalid_elapsed])

    def test_bootstrap_interval_is_deterministic_and_contains_the_median(self):
        first = bootstrap_ci([4.0, 5.0], samples=2000, seed=20260903)
        second = bootstrap_ci([4.0, 5.0], samples=2000, seed=20260903)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first[0], 4.0)
        self.assertLessEqual(first[1], 5.0)
        self.assertLessEqual(first[0], 4.5)
        self.assertGreaterEqual(first[1], 4.5)

    def test_multiple_workloads_remain_in_one_well_formed_summary_table(self):
        records = self.sample_records() + [
            record("python-block", "emulated", 30, workload="cpython"),
            record("python-block", "native", 10, workload="cpython"),
            record(
                "python-block",
                "emulated",
                0,
                workload="cpython",
                phase="verification",
            ),
            record(
                "python-block",
                "native",
                0,
                workload="cpython",
                phase="verification",
            ),
        ]

        report = render_markdown(records, bootstrap_samples=200)

        self.assertLess(report.index("| Cpython |"), report.index("Observed paired"))


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
            pairs_csv = root / "pairs.csv"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ANALYZE),
                    str(root / "raw"),
                    "--markdown",
                    str(markdown),
                    "--csv",
                    str(output_csv),
                    "--pairs-csv",
                    str(pairs_csv),
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
            self.assertIn("Median x64 + QEMU", report)
            self.assertIn("Median native ARM64", report)
            self.assertIn("16.00 s", report)
            self.assertIn("3.50 s", report)
            self.assertIn("4.50x", report)
            self.assertIn("4.47x", report)
            self.assertIn("4.00x–5.00x", report)
            self.assertIn("Excluded primary blocks", report)
            self.assertIn("Intended treatment attempts", report)
            with output_csv.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(records))
            self.assertEqual(rows[0]["block_id"], "block-1")
            with pairs_csv.open(newline="", encoding="utf-8") as stream:
                pairs = list(csv.DictReader(stream))
            self.assertEqual(len(pairs), 2)
            self.assertEqual([row["block_id"] for row in pairs], ["block-1", "block-2"])
            self.assertEqual({row["git_sha"] for row in pairs}, {"abc123"})


if __name__ == "__main__":
    unittest.main()
