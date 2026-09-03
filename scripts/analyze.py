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


def vm_medians(records):
    groups = {}
    for row in records:
        if row.get("target_arch") != "arm64":
            continue
        mode = row.get("execution_mode")
        if mode not in {"native", "emulated"}:
            continue
        key = (
            row["block_id"],
            row["workload"],
            row["phase"],
            mode,
        )
        groups.setdefault(key, []).append(row)

    medians = []
    for (block_id, workload, phase, mode), rows in sorted(groups.items()):
        if any(row.get("exit_code") != 0 for row in rows):
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
            }
        )
    return medians


def paired_speedups(records):
    treatments = {}
    for row in vm_medians(records):
        key = (row["block_id"], row["workload"], row["phase"])
        treatments.setdefault(key, {})[row["execution_mode"]] = row

    pairs = []
    for (block_id, workload, phase), modes in sorted(treatments.items()):
        if set(modes) != {"emulated", "native"}:
            continue
        emulated = modes["emulated"]["elapsed_seconds"]
        native = modes["native"]["elapsed_seconds"]
        if native <= 0:
            continue
        pairs.append(
            {
                "block_id": block_id,
                "workload": workload,
                "phase": phase,
                "emulated_seconds": emulated,
                "native_seconds": native,
                "speedup": emulated / native,
            }
        )
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
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        resample = [rng.choice(values) for _ in values]
        estimates.append(statistics.median(resample))
    estimates.sort()
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def render_markdown(records, bootstrap_samples):
    pairs = paired_speedups(records)
    groups = {}
    for row in pairs:
        key = (row["workload"], row["phase"])
        groups.setdefault(key, []).append(row["speedup"])

    lines = [
        "# Benchmark results",
        "",
        "Generated from append-only JSONL records. Speedup is x64-hosted QEMU time divided by native ARM64 time; values above 1 favor native ARM64.",
        "",
        "| Workload | Phase | Paired observations | Median | Geometric mean | Paired bootstrap 95% CI |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for (workload, phase), values in sorted(groups.items()):
        median = statistics.median(values)
        geometric_mean = math.exp(sum(math.log(value) for value in values) / len(values))
        low, high = bootstrap_ci(values, samples=bootstrap_samples)
        lines.append(
            "| {} | {} | {} paired blocks | {:.2f}x | {:.2f}x | {:.2f}x–{:.2f}x |".format(
                workload.replace("-", " ").title(),
                phase.replace("-", " "),
                len(values),
                median,
                geometric_mean,
                low,
                high,
            )
        )
    if not groups:
        lines.append("| No complete pairs | — | 0 paired blocks | — | — | — |")
    lines.extend(
        [
            "",
            "Actions runners are a controlled proxy for Copilot cloud-agent sandboxes. CPU models differ, so these ratios compare the offered runner choices rather than isolating pure QEMU overhead.",
            "",
        ]
    )
    return "\n".join(lines)


def write_csv(records, output):
    fields = sorted({key for row in records for key in row})
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
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        records = load_records(args.inputs)
        report = render_markdown(records, args.bootstrap_samples)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report, encoding="utf-8")
        write_csv(records, args.csv)
    except Exception as error:
        print("analyze: {}".format(error), file=sys.stderr)
        return 1
    print(args.markdown)
    print(args.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
