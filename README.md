# Native ARM64 evidence for GitHub Copilot cloud sandboxes

This repository tests a specific product hypothesis: repositories that ship
Linux/ARM64 containers and native dependencies should be able to opt into a
native ARM64 GitHub Copilot cloud sandbox.

The experiment compares the same pinned `linux/arm64` compile-and-test workloads
on equal-size public GitHub-hosted runners:

| Treatment | Runner | Execution |
| --- | --- | --- |
| Emulated comparison | `ubuntu-24.04` | ARM64 through QEMU/binfmt |
| Native comparison | `ubuntu-24.04-arm` | native ARM64 |

Both public runner shapes provide 4 vCPU, 16 GB RAM, and 14 GB SSD. Each paired
block uses fresh VMs and captures architecture, toolchain, correctness, timing,
and failure evidence.

## Read the evidence

- [Proposal](PROPOSAL.md) — the GitHub-facing product request and target workload
- [Methodology](METHODOLOGY.md) — treatments, protocol, endpoints, and limitations
- [Primary sources](SOURCES.md) — GitHub, Docker, and ARM-cloud market evidence
- `results/2026-09-03/` — raw retained records and generated analysis once trials complete

The Actions comparison measures the relevant native-versus-emulated execution
mechanism. It does not run on the Azure Container Apps Sandboxes substrate and
is not a direct benchmark of Copilot's model, orchestration, current sandbox
speed, or end-to-end task success; those require a GitHub-internal A/B test.

## Workloads

- Google Brotli: compile an AArch64 Python C extension, run 135 upstream
  tests, and compress/decompress a deterministic 64 MiB payload.
- CPython 3.14.7: configure and compile an AArch64 interpreter, then run five
  regression suites containing more than 1,000 tests.

Sources and target container images are checksum or digest pinned. Downloads and
base-layer preparation occur outside the primary timed stage.

## Reproduce

Run one independent paired block:

```bash
gh workflow run benchmark.yml \
  -f workload=all \
  -f repetitions=1 \
  -f trial_class=retained
```

After downloading one or more run artifacts into a directory:

```bash
python3 scripts/analyze.py results \
  --markdown RESULTS.md \
  --csv results.csv \
  --pairs-csv pairs.csv
```

Run `python3 -m unittest discover -s tests -v` to verify the measurement,
analysis, workflow, fixture, and workload contracts.
