#!/usr/bin/env python3
"""Analyze paired fresh-VM benchmark observations."""

import argparse
import csv
import json
import math
from pathlib import Path
import random
import statistics
import sys


REQUIRED_FIELDS = {
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
}

TREATMENTS = {
    "emulated": {"runner_label": "ubuntu-24.04", "host_arch": "amd64"},
    "native": {"runner_label": "ubuntu-24.04-arm", "host_arch": "arm64"},
}

WORKLOAD_LABELS = {"cpython": "CPython"}


def workload_label(value):
    return WORKLOAD_LABELS.get(value, value.replace("-", " ").title())


def load_records(paths):
    records = []
    files = []
    for supplied in paths:
        path = Path(supplied)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.jsonl")))
        else:
            files.append(path)
    for path in files:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(
                        "{}:{}: invalid JSON: {}".format(path, line_number, error)
                    ) from error
    return records


def validate_record(row):
    missing = sorted(REQUIRED_FIELDS - set(row))
    if missing:
        raise ValueError("record is missing required fields: {}".format(", ".join(missing)))
    if row["schema_version"] != 2:
        raise ValueError("unsupported schema_version: {}".format(row["schema_version"]))
    string_fields = (
        "block_id",
        "workload",
        "phase",
        "trial_class",
        "runner_label",
        "host_arch",
        "target_arch",
        "execution_mode",
        "started_at",
        "git_sha",
        "runner_image_os",
        "runner_image_version",
    )
    for field in string_fields:
        if not isinstance(row[field], str):
            raise ValueError("{} must be a string".format(field))
    for field in (
        "block_id",
        "workload",
        "phase",
        "runner_label",
        "host_arch",
        "target_arch",
        "execution_mode",
        "started_at",
    ):
        if not row[field]:
            raise ValueError("{} must not be empty".format(field))
    elapsed = row["elapsed_seconds"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(elapsed)
        or elapsed < 0
    ):
        raise ValueError("elapsed_seconds must be a finite non-negative number")
    if isinstance(row["exit_code"], bool) or not isinstance(row["exit_code"], int):
        raise ValueError("exit_code must be an integer")
    if not isinstance(row["command"], list) or not all(
        isinstance(part, str) for part in row["command"]
    ):
        raise ValueError("command must be a list of strings")
    if row["trial_class"] not in {"pilot", "retained"}:
        raise ValueError("invalid trial_class: {}".format(row["trial_class"]))
    if row["target_arch"] != "arm64":
        raise ValueError("target_arch must be arm64")
    mode = row["execution_mode"]
    if mode not in TREATMENTS:
        raise ValueError("invalid execution_mode: {}".format(mode))
    expected = TREATMENTS[mode]
    for field, value in expected.items():
        if row[field] != value:
            raise ValueError(
                "{} for {} treatment must be {!r}, got {!r}".format(
                    field, mode, value, row[field]
                )
            )
    if not isinstance(row["expected_repetitions"], int) or row["expected_repetitions"] < 1:
        raise ValueError("expected_repetitions must be a positive integer")
    if not isinstance(row["repetition"], int) or row["repetition"] < 1:
        raise ValueError("repetition must be a positive integer")
    if row["repetition"] > row["expected_repetitions"]:
        raise ValueError("repetition exceeds expected_repetitions")


def primary_records(records):
    for row in records:
        validate_record(row)
        if row["trial_class"] == "retained" and row["phase"] == "build-test":
            yield row


def vm_analysis(records):
    groups = {}
    for row in primary_records(records):
        mode = row["execution_mode"]
        key = (
            row["block_id"],
            row["workload"],
            row["phase"],
            mode,
        )
        groups.setdefault(key, []).append(row)

    medians = []
    errors = {}
    for (block_id, workload, phase, mode), rows in sorted(groups.items()):
        key = (block_id, workload, phase, mode)
        expected_counts = {row["expected_repetitions"] for row in rows}
        repetitions = [row["repetition"] for row in rows]
        reasons = []
        if len(expected_counts) != 1:
            reasons.append("inconsistent expected_repetitions")
        if len(repetitions) != len(set(repetitions)):
            reasons.append("duplicate repetition")
        if len(expected_counts) == 1:
            expected = next(iter(expected_counts))
            if set(repetitions) != set(range(1, expected + 1)):
                reasons.append("missing or unexpected repetition")
        if any(row.get("exit_code") != 0 for row in rows):
            reasons.append("measured command failure")
        if reasons:
            errors[key] = "; ".join(reasons)
            continue
        seconds = [float(row["elapsed_seconds"]) for row in rows]
        medians.append(
            {
                "block_id": block_id,
                "workload": workload,
                "phase": phase,
                "execution_mode": mode,
                "elapsed_seconds": statistics.median(seconds),
                "repetitions": len(seconds),
                "expected_repetitions": next(iter(expected_counts)),
            }
        )
    return medians, errors


def vm_medians(records):
    medians, _ = vm_analysis(records)
    return medians


def pairing_analysis(records, expected_git_sha=None):
    records = list(records)
    medians, group_errors = vm_analysis(records)
    if expected_git_sha is not None:
        if not expected_git_sha.strip():
            raise ValueError("expected_git_sha must not be blank")
        retained_git_shas = {
            row["git_sha"] for row in records if row["trial_class"] == "retained"
        }
        if retained_git_shas != {expected_git_sha}:
            observed = ", ".join(sorted(retained_git_shas)) or "no retained records"
            raise ValueError(
                "expected retained records at harness git_sha {}, observed {}".format(
                    expected_git_sha, observed
                )
            )
    treatments = {}
    for row in medians:
        key = (row["block_id"], row["workload"], row["phase"])
        treatments.setdefault(key, {})[row["execution_mode"]] = row

    primary_keys = {
        (row["block_id"], row["workload"], row["phase"])
        for row in primary_records(records)
    }
    primary_keys.update(
        (row["block_id"], row["workload"], "build-test")
        for row in records
        if row["trial_class"] == "retained" and row["phase"] == "attempt"
    )
    setup_failures = {}
    for row in records:
        if (
            row["trial_class"] == "retained"
            and row["phase"] not in {"attempt", "build-test", "verification"}
            and row["exit_code"] != 0
        ):
            key = (row["block_id"], row["workload"], "build-test")
            setup_failures.setdefault(key, []).append(
                "{} {} failure (exit {})".format(
                    row["execution_mode"], row["phase"], row["exit_code"]
                )
            )
    verifications = {}
    for row in records:
        if row["trial_class"] == "retained" and row["phase"] == "verification":
            key = (row["block_id"], row["workload"], "build-test")
            verifications.setdefault(key, {}).setdefault(
                row["execution_mode"], []
            ).append(row)
    attempts = {}
    for row in records:
        if row["trial_class"] == "retained" and row["phase"] == "attempt":
            key = (row["block_id"], row["workload"], "build-test")
            attempts.setdefault(key, {}).setdefault(row["execution_mode"], []).append(
                row
            )
    pairs = []
    exclusions = []
    for block_id, workload, phase in sorted(primary_keys):
        pair_key = (block_id, workload, phase)
        relevant_errors = [
            "{}: {}".format(mode, reason)
            for (error_block, error_workload, error_phase, mode), reason in sorted(
                group_errors.items()
            )
            if (error_block, error_workload, error_phase) == pair_key
        ]
        relevant_errors.extend(sorted(setup_failures.get(pair_key, [])))
        block_rows = [
            row
            for row in records
            if row["trial_class"] == "retained"
            and row["block_id"] == block_id
            and row["workload"] == workload
        ]
        git_shas = {row["git_sha"] for row in block_rows}
        if any(not value.strip() for value in git_shas):
            relevant_errors.append("blank git_sha in retained block")
        if len(git_shas) > 1:
            relevant_errors.append("treatments or phases use different git_sha values")
        attempt_modes = attempts.get(pair_key, {})
        for mode in sorted(TREATMENTS):
            rows = attempt_modes.get(mode, [])
            if not rows:
                relevant_errors.append("missing {} attempt record".format(mode))
            elif len(rows) > 1:
                relevant_errors.append("duplicate {} attempt record".format(mode))
            elif rows[0]["exit_code"] != 0:
                relevant_errors.append(
                    "{} attempt record failure (exit {})".format(
                        mode, rows[0]["exit_code"]
                    )
                )
            else:
                primary_counts = {
                    row["expected_repetitions"]
                    for row in block_rows
                    if row["phase"] == "build-test"
                    and row["execution_mode"] == mode
                }
                if (
                    len(primary_counts) == 1
                    and rows[0]["expected_repetitions"] != next(iter(primary_counts))
                ):
                    relevant_errors.append(
                        "{} attempt repetition count does not match primary timing".format(
                            mode
                        )
                    )
        verification_modes = verifications.get(pair_key, {})
        for mode in sorted(TREATMENTS):
            rows = verification_modes.get(mode, [])
            if not rows:
                relevant_errors.append("missing {} post-timing verification".format(mode))
            elif len(rows) > 1:
                relevant_errors.append("duplicate {} post-timing verification".format(mode))
            elif rows[0]["exit_code"] != 0:
                relevant_errors.append(
                    "{} verification failure (exit {})".format(
                        mode, rows[0]["exit_code"]
                    )
                )
            else:
                primary_counts = {
                    row["expected_repetitions"]
                    for row in block_rows
                    if row["phase"] == "build-test"
                    and row["execution_mode"] == mode
                }
                if (
                    len(primary_counts) == 1
                    and rows[0]["expected_repetitions"] != next(iter(primary_counts))
                ):
                    relevant_errors.append(
                        "{} verification repetition count does not match primary timing".format(
                            mode
                        )
                    )
        modes = treatments.get(pair_key, {})
        missing_modes = sorted({"emulated", "native"} - set(modes))
        if relevant_errors or missing_modes:
            reasons = relevant_errors
            if missing_modes:
                reasons.append("missing valid treatment: {}".format(", ".join(missing_modes)))
            exclusions.append(
                {
                    "block_id": block_id,
                    "workload": workload,
                    "phase": phase,
                    "reason": "; ".join(reasons),
                }
            )
            continue

        if (
            modes["emulated"]["expected_repetitions"]
            != modes["native"]["expected_repetitions"]
        ):
            exclusions.append(
                {
                    "block_id": block_id,
                    "workload": workload,
                    "phase": phase,
                    "reason": "treatments declare different repetition counts",
                }
            )
            continue

        emulated = modes["emulated"]["elapsed_seconds"]
        native = modes["native"]["elapsed_seconds"]
        if native <= 0:
            exclusions.append(
                {
                    "block_id": block_id,
                    "workload": workload,
                    "phase": phase,
                    "reason": "native median is not positive",
                }
            )
            continue
        pairs.append(
            {
                "block_id": block_id,
                "workload": workload,
                "phase": phase,
                "emulated_seconds": emulated,
                "native_seconds": native,
                "speedup": emulated / native,
                "git_sha": next(iter(git_shas)),
            }
        )
    pair_git_shas = {row["git_sha"] for row in pairs}
    if len(pair_git_shas) > 1:
        raise ValueError(
            "multiple harness git_sha values would be aggregated: {}".format(
                ", ".join(sorted(pair_git_shas))
            )
        )
    if expected_git_sha is not None:
        if pair_git_shas != {expected_git_sha}:
            observed = ", ".join(sorted(pair_git_shas)) or "no complete pairs"
            raise ValueError(
                "expected harness git_sha {}, observed {}".format(
                    expected_git_sha, observed
                )
            )
    return pairs, exclusions


def paired_speedups(records):
    pairs, _ = pairing_analysis(records)
    return pairs


def percentile(sorted_values, probability):
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def bootstrap_ci(values, samples=10000, seed=20260903):
    if not values:
        raise ValueError("at least one speedup is required")
    if samples < 1:
        raise ValueError("bootstrap samples must be positive")
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        resample = [rng.choice(values) for _ in values]
        estimates.append(statistics.median(resample))
    estimates.sort()
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def render_markdown(records, bootstrap_samples, expected_git_sha=None):
    records = list(records)
    pairs, exclusions = pairing_analysis(records, expected_git_sha=expected_git_sha)
    groups = {}
    for row in pairs:
        key = (row["workload"], row["phase"])
        groups.setdefault(key, []).append(row)

    lines = [
        "# Benchmark results",
        "",
        "Harness commit: `{}`.".format(pairs[0]["git_sha"] if pairs else "none"),
        "",
        "Generated from append-only JSONL records. Speedup is x64-hosted QEMU time divided by native ARM64 time; values above 1 favor native ARM64.",
        "",
        "| Workload | Phase | Paired observations | Pairs favoring native | Median x64 + QEMU | Median native ARM64 | Median speedup | Geometric mean speedup | Exploratory paired bootstrap 95% interval |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    range_lines = []
    for (workload, phase), group_pairs in sorted(groups.items()):
        values = [row["speedup"] for row in group_pairs]
        emulated_seconds = statistics.median(
            row["emulated_seconds"] for row in group_pairs
        )
        native_seconds = statistics.median(
            row["native_seconds"] for row in group_pairs
        )
        median = statistics.median(values)
        geometric_mean = math.exp(sum(math.log(value) for value in values) / len(values))
        confidence_interval = "not estimated"
        if len(values) >= 2:
            low, high = bootstrap_ci(values, samples=bootstrap_samples)
            confidence_interval = "{:.2f}x–{:.2f}x".format(low, high)
        lines.append(
            "| {} | {} | {} paired blocks | {}/{} | {:.2f} s | {:.2f} s | {:.2f}x | {:.2f}x | {} |".format(
                workload_label(workload),
                phase.replace("-", " "),
                len(values),
                sum(value > 1 for value in values),
                len(values),
                emulated_seconds,
                native_seconds,
                median,
                geometric_mean,
                confidence_interval,
            )
        )
        range_lines.append(
            "Observed paired speedup range for {}: {:.2f}x–{:.2f}x.".format(
                workload_label(workload), min(values), max(values)
            )
        )
    if not groups:
        lines.append(
            "| No complete pairs | — | 0 paired blocks | — | — | — | — | — | — |"
        )
    if range_lines:
        lines.extend([""] + range_lines)
        lines.extend(
            [
                "",
                "Treatment-time columns are marginal medians across blocks; median speedup is the median of within-block ratios and need not equal their quotient.",
                "Separate fresh-VM blocks are treated as analysis units, but shared fleet and time-window effects can correlate them.",
                "The bootstrap interval is exploratory for this small convenience cohort; the paired values, direction count, and observed range are the primary interpretation.",
            ]
        )
    primary = list(primary_records(records))
    successful = sum(row["exit_code"] == 0 for row in primary)
    attempts = [
        row
        for row in records
        if row["trial_class"] == "retained" and row["phase"] == "attempt"
    ]
    reached_primary = {
        (row["block_id"], row["workload"], row["execution_mode"])
        for row in primary
    }
    lines.extend(
        [
            "",
            "Primary measured-command success: {}/{} ({:.1f}%).".format(
                successful,
                len(primary),
                100 * successful / len(primary) if primary else 0.0,
            ),
            "Intended treatment attempts: {}; treatments reaching primary timing: {}.".format(
                len(attempts), len(reached_primary)
            ),
            "",
            "Excluded primary blocks: {}.".format(len(exclusions)),
            "",
        ]
    )
    if exclusions:
        lines.extend(
            [
                "| Excluded block | Workload | Reason |",
                "| --- | --- | --- |",
            ]
        )
        for row in exclusions:
            lines.append(
                "| {} | {} | {} |".format(
                    row["block_id"], row["workload"], row["reason"]
                )
            )
        lines.append("")
    lines.extend(
        [
            "Actions runners are a mechanism proxy, not the Azure Container Apps Sandboxes substrate used by Copilot cloud sandboxes. CPU models also differ, so these ratios compare the offered runner choices rather than isolating pure QEMU overhead or measuring current Copilot sandbox speed.",
            "",
        ]
    )
    return "\n".join(lines)


def write_csv(records, output, default_fields=None):
    fields = sorted({key for row in records for key in row})
    if not fields:
        fields = list(default_fields or [])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in records:
            serializable = {
                key: json.dumps(value, separators=(",", ":"))
                if isinstance(value, (list, dict))
                else value
                for key, value in row.items()
            }
            writer.writerow(serializable)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--pairs-csv", required=True, type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--expected-git-sha")
    args = parser.parse_args(argv)
    if args.bootstrap_samples < 1:
        parser.error("--bootstrap-samples must be positive")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        records = load_records(args.inputs)
        report = render_markdown(
            records,
            args.bootstrap_samples,
            expected_git_sha=args.expected_git_sha,
        )
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report, encoding="utf-8")
        write_csv(records, args.csv)
        pairs, _ = pairing_analysis(records, expected_git_sha=args.expected_git_sha)
        write_csv(
            pairs,
            args.pairs_csv,
            default_fields=(
                "block_id",
                "workload",
                "phase",
                "emulated_seconds",
                "native_seconds",
                "speedup",
                "git_sha",
            ),
        )
    except Exception as error:
        print("analyze: {}".format(error), file=sys.stderr)
        return 1
    print(args.markdown)
    print(args.csv)
    print(args.pairs_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
