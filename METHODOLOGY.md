# Methodology

## Question

For an agent that must build and execute Linux/ARM64 software, how does a native
ARM64 GitHub-hosted environment compare with an x64 environment with the same
advertised resource envelope that executes the same ARM64 container through
QEMU?

This experiment tests the execution mechanism on GitHub Actions. It does not
run on the Azure Container Apps Sandboxes substrate used by Copilot cloud
sandboxes, and is not a measurement of Copilot's orchestration, model latency,
current sandbox performance, or end-to-end task-completion rate.

## Treatments

| Treatment | GitHub runner | Published capacity | Host | Target |
| --- | --- | --- | --- | --- |
| Emulated comparison | `ubuntu-24.04` | 4 vCPU, 16 GB RAM, 14 GB SSD | x86-64 | `linux/arm64` through QEMU/binfmt |
| Native comparison | `ubuntu-24.04-arm` | 4 vCPU, 16 GB RAM, 14 GB SSD | ARM64 | native `linux/arm64` |

These are the published capacities for public-repository runners. The labels
and capacities come from GitHub's
[hosted-runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Each treatment receives a fresh VM. A workflow run is one paired block: both
VMs use the same commit, workload source, Dockerfile, target image, BuildKit,
parallelism, and correctness checks.

This is deliberately a comparison between the real runner choices, not an
attempt to isolate QEMU as the only causal variable. The CPU implementations,
runner images, and Docker engines can also differ and are archived with every
observation.

## Workloads

### Brotli native extension and compression

The first workload builds the native C Python extension in Google Brotli at
commit `028fb5a23661f123017c060daa546b55cf4bde29`, runs the repository's Python
test suite, and compresses then decompresses a deterministic 64 MiB payload at
quality 11. It represents the native-dependency development loop beneath
Python, Node, Ruby, and other packages with native code: compile, load, test,
and run a CPU-intensive operation on the target architecture.

### CPython from source

The second workload configures and builds CPython 3.14.7 with four-way
parallelism, verifies that the interpreter is an AArch64 ELF, and runs five
regression suites (`test_json`, `test_math`, `test_re`, `test_statistics`, and
`test_str`) with four workers and a fixed regrtest seed. It represents a larger
language-runtime edit-build-test loop.

Source URLs, revisions, and SHA-256 values are declared in
[`workloads/fixtures.json`](workloads/fixtures.json). Downloads and target base
layers are prepared before the primary timed stage. The measured Docker stages
do not access the network.

## Protocol

1. Run a smoke pair and inspect the host architecture, target `uname`, QEMU
   registration, runner capacity, and uploaded records.
2. Run each real workload as `trial_class=pilot`. Diagnose any failure from the
   full log and artifact, add a regression, and rerun the pilot. Pilot records
   are always excluded from headline estimates.
3. Freeze the harness commit, then collect retained paired blocks on fresh VMs.
   The immutable protocol set a minimum of five. Both cohorts stopped at five,
   every dispatch was retained, and no failed, incomplete, slow, fast, or
   unfavorable result was replaced or extended with an extra run.
4. Preserve every retained dispatch and observation. Never rerun or remove a
   block because it is slow, failed, or unfavorable to either treatment.
5. Classify setup, infrastructure, build, and test failures. Failed or incomplete
   pairs do not contribute a speedup, but their counts and reasons remain in the
   exclusion report.

The workflow accepts multiple repetitions on one VM, but the present protocol
uses one primary timed build per fresh VM. If repetitions are increased later,
the analyzer reduces them to one per-VM median before pairing, so repetitions
are never mistaken for independent samples.

## Correctness gates

An observation is eligible only when all of the following hold:

- both published runner shapes report four logical CPUs;
- the native host reports `aarch64` and the comparison host reports `x86_64`;
- both target containers report `aarch64`;
- the x64 host has an enabled `qemu-aarch64` binfmt registration;
- the produced interpreter or shared library identifies as AArch64;
- the ARM64 test suite and workload-specific round trip pass;
- all expected repetitions exist and have exit code zero;
- exactly one pre-checkout attempt record exists for each treatment; and
- a post-timing verification record confirms evidence export and correctness
  checks completed for both treatments at one shared harness commit.

Artifacts include append-only JSONL, fixture hashes, exact commands, start and
elapsed times, runner image versions, host CPU/memory/storage metadata,
Docker/Buildx/BuildKit/QEMU versions, ELF headers, output hashes, and test logs.

## Endpoints and analysis

The primary endpoint is paired workload speedup:

```text
x64-hosted QEMU build-test seconds / native ARM64 build-test seconds
```

A value above 1 favors native ARM64. Separate fresh-VM paired workflow blocks
are treated as analysis units; they are not assumed to be uncorrelated across a
shared fleet and time window. For each workload, the report publishes every
pair in `pairs.csv` and reports the direction count, median paired speedup,
geometric mean, observed range, and a deterministic exploratory paired-bootstrap
95% interval when at least two pairs exist. The treatment-time columns are
separate marginal medians; median paired speedup is the median of within-block
ratios and need not equal their quotient.

At five blocks, the bootstrap interval is descriptive; in these results each
interval equals the observed range and adds no independent precision. It is not
decision-grade inference. If any pair fails or is incomplete, speedup
summarizes only complete eligible pairs while the report separately retains
attempt, failure, and exclusion counts.

Fixture download, base-layer preparation, setup, and queue time are excluded
from the primary endpoint. End-to-end job time is retained as secondary context.
Analysis is implemented with the Python standard library in
[`scripts/analyze.py`](scripts/analyze.py).

## Reproduction

From a fork with GitHub Actions enabled:

```bash
gh workflow run benchmark.yml \
  -f workload=all \
  -f repetitions=1 \
  -f trial_class=retained

gh run download RUN_ID --dir results/RUN_ID
python3 scripts/analyze.py results \
  --markdown RESULTS.md \
  --csv results.csv \
  --pairs-csv pairs.csv \
  --expected-git-sha FROZEN_RETAINED_SHA
```

Use separate workflow dispatches to obtain fresh-VM blocks. Analyze only
artifacts from the frozen retained-trial commit. Reconcile the raw directory
against the immutable run ledger before analysis; the analyzer cannot infer a
dispatch whose artifacts are wholly absent. When `--expected-git-sha` is set,
the analyzer requires every retained record—not only complete pairs—to match
that commit. The ledger identifies the collection rule, commit, status, and
disposition of every run.

## Limitations

- Actions is an observable mechanism proxy, not the Copilot cloud-sandbox
  substrate. A GitHub internal experiment must measure the effect in actual
  cloud sandboxes and on agent task success.
- The treatments differ in physical CPU and runner image as well as execution
  mode; the estimate applies to these offered SKUs.
- Native ARM64 removes the emulator as an additional compatibility layer, but
  it does not reproduce every Graviton, Cobalt, or Axion microarchitecture,
  production kernel, accelerator, or instance configuration.
- Two workloads do not establish a universal ARM speedup. Cross-compilation,
  AMD64 builds, mobile simulators, hardware-dependent embedded work, power, and
  carbon are outside scope.
- The workloads are cold target-native build stressors, not representative
  end-to-end services or incremental edit loops. Brotli includes a synthetic
  quality-11 compression case with highly repetitive input.
- The workload code executes inside target containers in Actions, but GitHub's
  public cloud-sandbox documentation does not document nested container tooling.
  The product case applies directly to in-sandbox ARM64 compile/test commands;
  Dockerfile and image-build loops are conditional on separately supported
  rootless container tooling.
- Five paired blocks in one time window provide preliminary directional
  evidence. The bootstrap interval is exploratory; a decision-grade follow-up
  should use a preregistered larger sample across days and regions.
- GitHub Actions should remain the authoritative multi-architecture CI gate.
  Native agent execution can improve the interactive edit-run-debug loop; it
  does not replace CI coverage.
