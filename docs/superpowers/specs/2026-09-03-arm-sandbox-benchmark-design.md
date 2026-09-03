# Native ARM64 Copilot Sandbox Evidence Design

## Purpose

Produce reproducible evidence for an opt-in Ubuntu ARM64 execution environment for GitHub Copilot cloud agent. The headline workload is developing, building, executing, and debugging Linux/ARM64 containers and their native dependencies for ARM cloud production.

## Product claim under test

GitHub Copilot cloud agent currently runs in an Actions-powered development environment but supports Ubuntu x64 and Windows x64 runners only. For repositories that target Linux/ARM64, a native ARM64 sandbox should shorten the agent's edit-build-test loop and improve target fidelity compared with executing the same ARM64 userland through QEMU on x64.

The experiment measures the performance mechanism on GitHub-hosted Actions runners. It does not claim to benchmark Copilot's unpublished orchestration overhead or prove that all ARM workloads benefit.

## Treatments

The public repository uses runner SKUs with the same published resources:

| Treatment | Runner | Published resources | Target |
| --- | --- | --- | --- |
| Current proxy | `ubuntu-24.04` | 4 vCPU, 16 GB RAM, 14 GB SSD | `linux/arm64` through QEMU/binfmt |
| Proposed proxy | `ubuntu-24.04-arm` | 4 vCPU, 16 GB RAM, 14 GB SSD | native `linux/arm64` |

Every paired observation comes from one workflow run at one commit. Each treatment gets a fresh VM. Inputs, target container images, source archives, checksums, commands, concurrency, and correctness assertions are identical. Processor implementations differ, so results describe the two actual runner choices rather than pure QEMU overhead.

## Workloads

1. **Google Brotli Python extension:** compile a real C/C++ Python extension, execute its unit tests, and perform compression/decompression. This is the concrete native-package case beneath the broad container workload.
2. **CPython:** configure and compile a pinned Python release and run a stable targeted test set. This represents a substantial language-runtime build/test loop.
3. **Small smoke workload:** verify runner architecture, QEMU registration on x64, ARM64 container execution, measurement output, and artifact collection before expensive trials.

Pinned source archives are fetched and checksum-verified before measurement. Dockerfiles perform no network access in measured stages. Both hosts execute ARM64 toolchains inside the same target-platform containers; the x64 job must not silently cross-compile on the build platform.

## Protocol

- Begin with one smoke/pilot pair and exclude it from reported estimates.
- Run at least five independent paired workflow blocks during the investigation. A longer follow-up should use 30 paired blocks over three days.
- Use one timed build per fresh VM for the primary estimate. If a workload is short enough, use three repetitions and reduce them to the per-VM median.
- Record setup and end-to-end job timing separately from workload timing.
- Never discard a slow successful observation. Retry an entire pair only after a classified infrastructure failure.
- Archive host metadata, runner image versions, Docker/Buildx/QEMU versions, exact commands, exit codes, source hashes, output architecture, test results, and raw JSONL.

## Correctness gates

- `nproc` must report four on the public runners.
- The target container must report `aarch64` on both treatments.
- The x64 treatment must expose an enabled `qemu-aarch64` binfmt registration.
- Produced ELF/shared-library files must identify as AArch64.
- Test suites and round-trip hashes must agree across treatments.
- Any command failure is a correctness result, not a timing sample.

## Metrics

The primary endpoint per workload is paired speedup:

`x64 + QEMU workload seconds / native ARM64 workload seconds`

Report raw paired samples, median speedup, geometric-mean paired speedup, range, and a paired bootstrap 95% confidence interval when sample size permits. Secondary metrics include setup time, workload success rate, and total job time. Queue time is reported separately and is not part of workload speedup.

## Deliverables

- Public benchmark repository and immutable workflow-run links.
- Reusable measurement and analysis scripts with automated tests.
- Raw result artifacts and a machine-readable consolidated dataset.
- Methodology, limitations, and reproduction instructions.
- A concise GitHub-ready proposal that separates sourced facts, measured results, and inferences.

## Explicit non-claims

- The study does not isolate processor microarchitecture from emulation mode.
- It does not benchmark cross-compilation, the AMD64 half of a multi-platform matrix, power, carbon, or universal ARM performance.
- Actions runners are a controlled proxy; Copilot sandbox performance could differ.
- Native ARM complements, rather than replaces, the authoritative CI architecture matrix.

