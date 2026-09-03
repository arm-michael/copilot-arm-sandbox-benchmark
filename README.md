# Native ARM64 evidence for GitHub Copilot cloud sandboxes

This repository tests a specific product hypothesis: repositories that ship
Linux/ARM64 services, runtimes, packages, containers, or native dependencies
should be able to opt into a native ARM64 GitHub Copilot cloud sandbox.

The primary product request targets the Azure Container Apps Sandboxes-backed
runtime used by Copilot CLI and the GitHub Copilot app. The Actions-powered
Copilot cloud agent used for background tasks is treated as a related, separate
ARM64 opportunity.

The experiment compares the same pinned Linux/ARM64 compile-and-test workloads
inside target containers on public GitHub-hosted runners with the same
advertised resource envelope:

| Treatment | Runner | Execution |
| --- | --- | --- |
| Emulated comparison | `ubuntu-24.04` | ARM64 through QEMU/binfmt |
| Native comparison | `ubuntu-24.04-arm` | native ARM64 |

Both public runner shapes provide 4 vCPU, 16 GB RAM, and 14 GB SSD. Each paired
block uses fresh VMs and captures architecture, toolchain, correctness, timing,
and failure evidence.

Across the 10 retained pairs, native ARM64 completed the timed stage sooner in
10/10. The median paired ratio was **13.36x** for Brotli and **21.50x** for
CPython. These compare offered Actions runner SKUs whose CPUs and runner images
also differ; they are mechanism-proxy evidence, not pure QEMU-overhead estimates
or measured Copilot cloud-sandbox speedups.

## Read the evidence

- [Proposal](PROPOSAL.md) — the GitHub-facing product request and target workload
- [Methodology](METHODOLOGY.md) — treatments, protocol, endpoints, and limitations
- [Primary sources](SOURCES.md) — GitHub, Docker, and ARM-cloud market evidence
- [Results](results/2026-09-03/RESULTS.md) — final paired estimates and exclusions
- [Run ledger](results/2026-09-03/RUNS.md) — every dispatch, correction, and disposition
- [Evidence audit](results/2026-09-03/AUDIT.md) — record counts, architecture, and correctness
- [`raw/`](results/2026-09-03/raw/) — the 10 retained paired blocks

The Actions comparison measures the relevant native-versus-emulated execution
mechanism. It does not run on the Azure Container Apps Sandboxes substrate and
is not a direct benchmark of Copilot's model, orchestration, current sandbox
speed, or end-to-end task success; those require a GitHub-internal A/B test.
The cloud-sandbox documentation does not document nested container tooling, so
the product case rests on direct ARM64 compile, load, test, and debug commands;
image builds are an additional benefit only where supported.

## Workloads

- Google Brotli: compile an AArch64 Python C extension, run 135 upstream
  tests, and compress/decompress a deterministic 64 MiB payload.
- CPython 3.14.7: configure and compile an AArch64 interpreter, then run five
  regression suites containing 1,018 tests with a fixed seed.

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
python3 scripts/analyze.py results/2026-09-03/raw \
  --markdown results/2026-09-03/RESULTS.md \
  --csv results/2026-09-03/results.csv \
  --pairs-csv results/2026-09-03/pairs.csv \
  --expected-git-sha b9d8f62d3a874ecc1fcab110476afec6397f63eb
```

Run `python3 -m unittest discover -s tests -v` to verify the measurement,
analysis, workflow, fixture, and workload contracts.
