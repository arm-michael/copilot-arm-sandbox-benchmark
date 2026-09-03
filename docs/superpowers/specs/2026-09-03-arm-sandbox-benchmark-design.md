# Native ARM64 Copilot Sandbox Evidence Design

## Purpose

Produce reproducible evidence for an opt-in Linux/ARM64 execution architecture
in the Azure Container Apps Sandboxes-backed runtime used by GitHub Copilot CLI
and the GitHub Copilot app. The headline workload is compiling, executing,
testing, and debugging Linux/ARM64 services, runtimes, packages, and native
dependencies for ARM cloud production. Container-image loops are an additional
benefit only where the sandbox exposes supported container tooling. The
Actions-powered Copilot cloud agent is a separate, related opportunity.

## Product claim under test

For repositories that target Linux/ARM64, the hypothesis is that a native ARM64
cloud sandbox can shorten the agent's edit-build-test loop by removing QEMU as
an additional compatibility layer. Public GitHub and Microsoft documentation
does not identify the current Copilot sandbox processor architecture/model,
QEMU availability, or nested-container support. The proposal therefore asks
for an opt-in tier and an internal product experiment rather than treating the
Actions result as observed Copilot behavior.

The experiment measures a relevant native-versus-emulated mechanism on
GitHub-hosted Actions runners. It does not benchmark the Azure Container Apps
Sandboxes substrate, Copilot orchestration, or end-to-end task success, and it
does not prove that all ARM workloads benefit.

## Treatments

The public repository uses runner SKUs with the same published resources:

| Treatment | Runner | Published resources | Target |
| --- | --- | --- | --- |
| Emulated comparison | `ubuntu-24.04` | 4 vCPU, 16 GB RAM, 14 GB SSD | `linux/arm64` through QEMU/binfmt |
| Native comparison | `ubuntu-24.04-arm` | 4 vCPU, 16 GB RAM, 14 GB SSD | native `linux/arm64` |

Every paired observation comes from one workflow run at one commit. Each treatment gets a fresh VM. Inputs, target container images, source archives, checksums, commands, concurrency, and correctness assertions are identical. Processor implementations differ, so results describe the two actual runner choices rather than pure QEMU overhead.

## Workloads

1. **Google Brotli Python extension:** compile a real C/C++ Python extension, execute its unit tests, and perform compression/decompression. This is the concrete native-package edit-build-test case.
2. **CPython:** configure and compile a pinned Python release and run a stable targeted test set. This represents a substantial language-runtime build/test loop.
3. **Small smoke workload:** verify runner architecture, QEMU registration on x64, ARM64 container execution, measurement output, and artifact collection before expensive trials.

Pinned source archives are fetched and checksum-verified before measurement. Dockerfiles perform no network access in measured stages. Both hosts execute ARM64 toolchains inside the same target-platform containers; the x64 job must not silently cross-compile on the build platform.

## Protocol

- Begin with one smoke/pilot pair and exclude it from reported estimates.
- After the corresponding workload's frozen-harness pilot pair passes, dispatch
  at least five retained paired workflow blocks per workload. The completed
  study stopped both cohorts at five in two waves, retained every dispatch, and
  did not replace a failure or extend collection in response to outcomes. A
  longer follow-up should preregister a larger sample across days and regions.
- Use one timed build per fresh VM for the primary estimate. If a workload is short enough, use three repetitions and reduce them to the per-VM median.
- Record setup and end-to-end job timing separately from workload timing.
- Never discard or replace a retained observation because it is slow, failed,
  incomplete, or unfavorable to either treatment.
- Archive host metadata, runner image versions, Docker/Buildx/QEMU versions, exact commands, exit codes, source hashes, output architecture, test results, and raw JSONL.

## Correctness gates

- `nproc` must report four on the public runners.
- The target container must report `aarch64` on both treatments.
- The x64 treatment must expose an enabled `qemu-aarch64` binfmt registration.
- Produced ELF/shared-library files must identify as AArch64.
- Test suites, fixed CPython seed/count, and workload behavior must agree across
  treatments; Brotli round-trip and compiled-extension hashes must also agree.
- Any command failure is a correctness result, not a timing sample.

## Metrics

The primary endpoint per workload is paired speedup:

`x64 + QEMU workload seconds / native ARM64 workload seconds`

Report raw paired samples, direction count, median speedup, geometric-mean
paired speedup, range, and a deterministic exploratory paired-bootstrap 95%
interval. At five blocks, treat the paired values, direction, median, and range
as primary; do not present the interval as decision-grade inference. Secondary
metrics include setup time, workload success rate, and total job time. Queue
time is separate and is not part of workload speedup.

## Deliverables

- Public benchmark repository and immutable workflow-run links.
- Reusable measurement and analysis scripts with automated tests.
- Raw result artifacts and a machine-readable consolidated dataset.
- Methodology, limitations, and reproduction instructions.
- A concise GitHub-ready proposal that separates sourced facts, measured results, and inferences.

## Explicit non-claims

- The study does not isolate processor microarchitecture from emulation mode.
- It does not benchmark cross-compilation, the AMD64 half of a multi-platform matrix, power, carbon, or universal ARM performance.
- Actions runners are a mechanism proxy; Copilot cloud-sandbox performance and
  task outcomes could differ.
- Generic ARM64 execution does not reproduce each Graviton, Cobalt, or Axion
  microarchitecture, production kernel, accelerator, or instance shape.
- Public documentation does not promise nested container tooling in Copilot
  cloud sandboxes; direct native compile/test/debug is the core workload.
- Native ARM complements, rather than replaces, the authoritative CI architecture matrix.
