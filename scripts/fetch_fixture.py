#!/usr/bin/env python3
"""Fetch one checksummed benchmark source archive."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.request import urlopen


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_fixture(manifest_path, workload, destination):
    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if workload not in manifest:
        available = ", ".join(sorted(manifest))
        raise ValueError(
            "unknown workload {!r}; available workloads: {}".format(
                workload, available
            )
        )

    fixture = manifest[workload]
    expected_sha = fixture["sha256"].lower()
    output = destination / fixture["filename"]
    destination.mkdir(parents=True, exist_ok=True)
    if output.exists() and sha256_file(output) == expected_sha:
        return output

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(destination),
            prefix=".{}.".format(fixture["filename"]),
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with urlopen(fixture["url"]) as response:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    temporary.write(chunk)

        actual_sha = sha256_file(temporary_path)
        if actual_sha != expected_sha:
            raise ValueError(
                "SHA-256 mismatch for {}: expected {}, got {}".format(
                    workload, expected_sha, actual_sha
                )
            )
        os.replace(str(temporary_path), str(output))
        temporary_path = None
        return output
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "workloads" / "fixtures.json",
    )
    parser.add_argument("workload")
    parser.add_argument("destination", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        output = fetch_fixture(args.manifest, args.workload, args.destination)
    except Exception as error:
        print("fetch_fixture: {}".format(error), file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
