# Native ARM64 Sandbox Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a reproducible paired GitHub Actions experiment comparing Linux/ARM64 workloads under x64-hosted QEMU with native ARM64 execution, then publish a reviewed GitHub proposal.

**Architecture:** A matrix workflow dispatches identical pinned workloads to equal-size x64 and ARM64 public runners. Small Python utilities checksum fixtures, measure subprocesses into JSONL, and analyze paired fresh-VM observations; Dockerfiles force the ARM64 target platform and contain the real compile/test work.

**Tech Stack:** GitHub Actions, Ubuntu 24.04 x64/ARM64 runners, Docker Buildx, QEMU/binfmt, Python 3 standard library, `unittest`, pinned upstream source archives.

**Spec:** `docs/superpowers/specs/2026-09-03-arm-sandbox-benchmark-design.md`

## Global Constraints

- Compare `ubuntu-24.04` with `ubuntu-24.04-arm` in a public repository.
- Execute `linux/arm64` target userlands on both treatments; do not substitute cross-compilation.
- Fetch and checksum fixtures before timed regions; measured Docker stages perform no network I/O.
- Preserve all successful observations and pair by workflow run ID.
- Label the Actions data as a Copilot sandbox proxy, not a direct sandbox benchmark.

---

### Task 1: Measurement records

**Files:**
- Create: `tests/test_measure.py`
- Create: `scripts/measure.py`

**Interfaces:**
- Produces: `normalize_arch(value: str) -> str`, `execution_mode(host_arch: str, target_arch: str) -> str`, and a CLI that runs the command after `--`, streams its output, appends one schema-versioned JSON object, and exits with the child's exit code.
- JSON fields: `schema_version`, `block_id`, `workload`, `phase`, `repetition`, `runner_label`, `host_arch`, `target_arch`, `execution_mode`, `started_at`, `elapsed_seconds`, `exit_code`, `command`, `git_sha`, `runner_image_os`, and `runner_image_version`.

- [ ] Write unit tests for architecture normalization, native/emulated classification, successful timing records, and failed-command records.
- [ ] Run `python3 -m unittest tests.test_measure -v`; verify imports fail because `scripts/measure.py` does not exist.
- [ ] Implement the smallest measurement module satisfying the tested contract using `argparse`, `platform.machine`, `subprocess.run`, `time.perf_counter_ns`, and append-mode JSONL.
- [ ] Re-run `python3 -m unittest tests.test_measure -v`; require zero failures.
- [ ] Commit `tests/test_measure.py` and `scripts/measure.py` with message `feat: add reproducible command measurements`.

### Task 2: Fixture verification and workload contracts

**Files:**
- Create: `tests/test_workload_contracts.py`
- Create: `scripts/fetch_fixture.py`
- Create: `workloads/fixtures.json`
- Create: `workloads/brotli/Dockerfile`
- Create: `workloads/cpython/Dockerfile`

**Interfaces:**
- `fetch_fixture.py WORKLOAD DESTINATION` reads `workloads/fixtures.json`, downloads the declared HTTPS URL, verifies SHA-256, and atomically installs the expected filename.
- Each Dockerfile exposes a `prepared` stage and a final `benchmark` stage accepting `ARG BENCHMARK_ITERATION`.

- [ ] Write tests that reject an unknown fixture, reject a checksum mismatch using a local `file:` fixture, accept a matching fixture, require exact pinned URLs/SHA-256 values, require target-platform Docker bases, and forbid `curl`, `wget`, `apt`, or package-index access in Dockerfiles.
- [ ] Run `python3 -m unittest tests.test_workload_contracts -v`; verify the missing implementation failure.
- [ ] Implement fixture retrieval with temporary-file cleanup and clear errors.
- [ ] Add Brotli 1.2.0 commit `028fb5a23661f123017c060daa546b55cf4bde29`, archive SHA-256 `0afe09a53c8bad9861c8dd1fc1284308d54f19d2979ba3541cfdcc9b05fe360f`, and CPython 3.14.7 SHA-256 `62859805f6fdf25e2bcbf3fa3217801e1996887ca33e6a2af80674bdfa2dbe07` to the manifest.
- [ ] Implement Docker stages that compile and test each workload at four-way concurrency and assert AArch64 outputs.
- [ ] Re-run `python3 -m unittest tests.test_workload_contracts -v`; require zero failures.
- [ ] Commit with message `feat: add pinned native workloads`.

### Task 3: Paired analysis

**Files:**
- Create: `tests/test_analyze.py`
- Create: `scripts/analyze.py`

**Interfaces:**
- Produces: `load_records(paths)`, `vm_medians(records)`, `paired_speedups(records)`, `bootstrap_ci(values, samples=10000, seed=20260903)`, and a CLI that writes Markdown plus consolidated CSV.
- A valid pair has one successful `x64-qemu` VM median and one successful `arm64-native` VM median for the same `block_id`, workload, and phase.

- [ ] Write tests using two complete pairs plus incomplete and failed records; assert VM-level reduction, exact ratios, deterministic interval ordering, and explicit exclusion counts.
- [ ] Run `python3 -m unittest tests.test_analyze -v`; verify the missing implementation failure.
- [ ] Implement median, geometric mean, deterministic paired bootstrap, Markdown rendering, and CSV output using only the standard library.
- [ ] Re-run `python3 -m unittest tests.test_analyze -v`; require zero failures.
- [ ] Commit with message `feat: analyze paired runner benchmarks`.

### Task 4: GitHub Actions experiment

**Files:**
- Create: `tests/test_workflow_contract.py`
- Create: `.github/workflows/benchmark.yml`
- Create: `scripts/run_workload.sh`

**Interfaces:**
- Manual inputs: `workload` (`smoke`, `brotli`, `cpython`, or `all`) and `repetitions` (positive integer).
- Matrix treatments: `ubuntu-24.04`/`x64-qemu` and `ubuntu-24.04-arm`/`arm64-native`, always targeting `linux/arm64`.
- Produces one artifact named `results-<workload>-<treatment>-<run_attempt>` per job.

- [ ] Write static workflow tests that require both exact runner labels, QEMU setup only on x64, Buildx setup after QEMU, four-core and `aarch64` gates, fixture fetch before timing, measurement wrapper use, and result upload on success or failure.
- [ ] Run `python3 -m unittest tests.test_workflow_contract -v`; verify the absent workflow failure.
- [ ] Implement the workflow and shell coordinator, pinning official action commits and the QEMU image reference used by the setup action.
- [ ] Run all unit tests and `actionlint .github/workflows/benchmark.yml`; require zero failures.
- [ ] Commit and push with message `ci: add paired arm64 benchmark workflow`.

### Task 5: Pilot, repeated trials, and review

**Files:**
- Modify when needed: workload/workflow files from Tasks 1-4
- Create: `results/2026-09-03/raw/`
- Create: `results/2026-09-03/RESULTS.md`
- Create: `results/2026-09-03/results.csv`

- [ ] Dispatch one smoke pair and inspect architecture, binfmt, runner metadata, artifacts, and logs.
- [ ] Dispatch one Brotli and one CPython pilot pair; classify failures before changing the harness.
- [ ] After each correction, add a failing regression test first, then rerun the affected pilot.
- [ ] Dispatch at least five independent successful paired blocks per retained workload.
- [ ] Download artifacts without rewriting them, verify record counts/checksums, and run `scripts/analyze.py`.
- [ ] Have independent reviewers assess code correctness, experimental validity, and claim discipline; resolve all critical/important issues.
- [ ] Commit raw data, analysis, and corrections with traceable workflow URLs.

### Task 6: Proposal and final verification

**Files:**
- Modify: `README.md`
- Create: `METHODOLOGY.md`
- Create: `PROPOSAL.md`
- Create: `SOURCES.md`

- [ ] Write the proposal around Linux/ARM64 containers/cloud services, using native packages as the proof case and Android/embedded only as secondary beneficiaries.
- [ ] Separate sourced facts, measured results, and inferences; include counterarguments, limitations, an opt-in MVP, and immutable run links.
- [ ] Re-run all tests, workflow lint, result analysis, link checks, and a clean-repository reproduction check.
- [ ] Request final adversarial reviews for GitHub product fit, statistical validity, and technical reproducibility; fix every critical/important issue.
- [ ] Push the verified report and record final commit SHA and public repository URL.

