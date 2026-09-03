#!/usr/bin/env python3
"""Run one command and append a reproducible JSONL timing record."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


ARCHITECTURE_ALIASES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


def normalize_arch(value):
    """Return the OCI architecture name used by this experiment."""
    normalized = ARCHITECTURE_ALIASES.get(value.strip().lower())
    if normalized is None:
        raise ValueError("unsupported architecture: {}".format(value))
    return normalized


def execution_mode(host_arch, target_arch):
    """Classify target execution as native or emulated."""
    if normalize_arch(host_arch) == normalize_arch(target_arch):
        return "native"
    return "emulated"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--repetition", required=True, type=int)
    parser.add_argument("--runner-label", required=True)
    parser.add_argument("--host-arch", default=platform.machine())
    parser.add_argument("--target-arch", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    return args


def main(argv=None):
    args = parse_args(argv)
    host_arch = normalize_arch(args.host_arch)
    target_arch = normalize_arch(args.target_arch)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started_ns = time.perf_counter_ns()
    completed = subprocess.run(args.command, check=False)
    elapsed_seconds = (time.perf_counter_ns() - started_ns) / 1_000_000_000

    record = {
        "schema_version": 1,
        "block_id": "{}.{}".format(run_id, run_attempt),
        "workload": args.workload,
        "phase": args.phase,
        "repetition": args.repetition,
        "runner_label": args.runner_label,
        "host_arch": host_arch,
        "target_arch": target_arch,
        "execution_mode": execution_mode(host_arch, target_arch),
        "started_at": started_at,
        "elapsed_seconds": round(elapsed_seconds, 9),
        "exit_code": completed.returncode,
        "command": args.command,
        "git_sha": os.environ.get("GITHUB_SHA", ""),
        "runner_image_os": os.environ.get("ImageOS", ""),
        "runner_image_version": os.environ.get("ImageVersion", ""),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as stream:
        json.dump(record, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")

    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
