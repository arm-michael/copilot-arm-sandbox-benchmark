# Proposal: opt-in Linux/ARM64 for GitHub Copilot cloud sandboxes

## Decision requested

Add Linux/ARM64 as an opt-in execution architecture for cloud sandbox sessions
started from GitHub Copilot CLI and the GitHub Copilot app. Retain the current
cloud-sandbox architecture as the default. Persist the selected architecture
when a session is stopped, resumed, or continued from another device; expose it
in the UI and logs; and never silently substitute another architecture.

The first target is repositories that compile and test ARM64 services,
runtimes, packages, and native dependencies for Graviton, Cobalt, Axion, and
similar production infrastructure. Emulation can remain an explicit
compatibility fallback where GitHub provides it, while native execution lets
the agent compile, load, run, inspect, and retest the target artifact inside one
hosted session. Where the sandbox exposes supported rootless container tooling,
the same tier can also execute target-architecture image build steps.

This primary request concerns **Copilot cloud sandboxes**. The Actions-powered
**Copilot cloud agent** is a separate runtime and a related follow-on request.

Across all 10 retained paired blocks, native ARM64 completed the timed
build/test stage sooner. Median paired ratios were 13.36x for Brotli and 21.50x
for CPython. These compare offered Actions runner SKUs whose CPUs and runner
images also differ; they are mechanism-proxy evidence, not pure QEMU-overhead
estimates or current Copilot sandbox speedups. They justify a gated internal
product experiment.
[Final results](results/2026-09-03/RESULTS.md)

## The major workload: ARM64 service and native-dependency development

A representative session repeatedly:

1. modifies application code or native build and packaging configuration;
2. compiles a C/C++, Rust, Go/cgo, Python-extension, Node-add-on, language
   runtime, or other architecture-specific component for Linux/ARM64;
3. loads and executes ARM64 tests, startup probes, package-install checks, and
   binaries directly in the session;
4. diagnoses ABI, dependency, packaging, or runtime failures; and
5. edits and retests until the target-native artifact passes.

This is more than cross-compilation. Docker treats emulation, native nodes, and
cross-compilation as different strategies and warns that QEMU can be much
slower for compute-heavy work such as compilation and compression.
Cross-compilation can produce target binaries, but it does not itself execute
target-architecture tests, dynamic loads, runtime probes, or package-install
checks. Where supported container tooling is present, target-platform
Dockerfile `RUN` steps that execute target binaries likewise require either a
native node or emulation.
[Docker: multi-platform build strategies](https://docs.docker.com/build/building/multi-platform/)

When target-native commands execute through QEMU, the emulation penalty is paid
on every affected iteration. Without native execution, architecture-specific
failures may surface only in an emulated run or downstream ARM64 CI. A native
ARM64 sandbox removes the emulator as an additional compatibility layer and is
expected to shorten feedback for this workload. It does not reproduce every
cloud-provider microarchitecture, kernel, accelerator, or instance
configuration; provider-specific validation remains downstream, and the
product effect should be measured internally.

GitHub's public cloud-sandbox documentation says users can run shell commands
and iterate on code, but it does not describe Docker, BuildKit, Podman, or
another nested-container interface. The direct compile-test-debug loop above
therefore does not depend on container tooling. Image assembly is an additional
benefit only where GitHub exposes a supported interface; otherwise it should be
evaluated as a separate capability.
[GitHub: cloud and local sandboxes](https://docs.github.com/en/copilot/concepts/about-cloud-and-local-sandboxes)

## Why cloud sandboxes are the right product boundary

GitHub describes cloud sandboxes as fully isolated, ephemeral Linux
environments hosted by GitHub and built on Azure Container Apps Sandboxes. The
entire interactive Copilot CLI session runs remotely, and a cloud session can
be continued from another device.
[GitHub: cloud and local sandboxes](https://docs.github.com/en/copilot/concepts/about-cloud-and-local-sandboxes)

The GitHub Copilot app offers a cloud sandbox as a session-location choice
alongside a local repository or worktree.
[GitHub: Copilot app agent sessions](https://docs.github.com/en/copilot/how-tos/github-copilot-app/agent-sessions)
With remote control enabled, users can monitor and steer a Copilot CLI session
from GitHub Mobile.
[GitHub: steering Copilot CLI remotely](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/steer-remotely)
For a cloud-backed CLI session, architecture should therefore remain a property
of the remote sandbox, not of the laptop or phone steering it.

Cloud sandboxes are still in public preview. This is the right time to make
architecture a first-class session property before interfaces, snapshots, and
capacity assumptions harden.

GitHub meters cloud-sandbox compute per running second and memory per
GiB-second. If faster target execution shortens total session running time, it
can reduce compute-second and GiB-second usage as well as feedback latency. The
Actions proxy cannot estimate that product-level saving; the internal
experiment should measure cost per successful task.
[GitHub: cloud-sandbox billing](https://docs.github.com/en/copilot/concepts/about-cloud-and-local-sandboxes#billing)

Supporting ARM64 is likely to require an ARM-capable sandbox host tier, ARM64
base images and bundled tools, architecture-bound snapshots, capacity,
metering, and a GitHub-facing architecture selector. The
[Sandbox overview](https://learn.microsoft.com/en-us/azure/container-apps/sandboxes-overview)
exposes no CPU-architecture selector or compatibility matrix. Separately, the
broader Apps/Jobs
[Container Apps documentation](https://learn.microsoft.com/en-us/azure/container-apps/containers)
currently supports x86-64 images; that limitation should not be assumed to
apply unchanged to Sandboxes. GitHub and Microsoft should first confirm the
Sandbox host, image, and snapshot boundary.

### Related cloud-agent path in GitHub Mobile

GitHub Mobile also directly starts and tracks **Copilot cloud agent** sessions.
[GitHub: cloud agent on Mobile](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-mobile)
That agent works in an ephemeral GitHub Actions-powered environment currently
documented as compatible with Ubuntu x64 and Windows 64-bit runners.
[GitHub: cloud-agent environment](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment)

Native ARM64 could benefit eligible ARM-targeted tasks in that runtime too.
After the cloud agent is made ARM compatible, `copilot-setup-steps.yml` is the
likely repository-facing configuration surface for selecting an ARM64 runner.
That is a second product change, not the mechanism proposed for Azure-backed
cloud sandboxes.

## Why this is a major workload

GitHub reported 4.3 million repositories using Dockerfiles in 2023.
[GitHub Octoverse 2023](https://github.blog/news-insights/research/the-state-of-open-source-and-ai/)
ARM servers are established production targets:

- AWS reports more than 120,000 Graviton customers and lists application
  servers, microservices, databases, and HPC among its workloads.
  [AWS Graviton](https://aws.amazon.com/ec2/graviton/)
- Microsoft positions generally available Cobalt 100 VMs for scale-out and
  cloud-native Linux workloads.
  [Azure Cobalt 100 GA](https://azure.microsoft.com/en-us/blog/azure-cobalt-100-based-virtual-machines-are-now-generally-available/)
- Google offers generally available Axion C4A instances through Compute Engine,
  GKE, Batch, and Dataproc.
  [Google Axion C4A GA](https://cloud.google.com/blog/products/compute/first-google-axion-processor-c4a-now-ga-with-titanium-ssd)

These figures establish that container development and ARM cloud deployment
are independently substantial; they do not quantify the intersection. GitHub
should size the addressable cohort by intersecting active Copilot app/CLI
repositories with ARM runner labels, ARM image manifests, and ARM build or
publishing configuration. Use that cohort to set preview capacity and measure
opt-in, repeat use, queue latency, and cost.

GitHub already offers the adjacent execution mechanism in Actions. Native ARM64
runners are available as `ubuntu-24.04-arm`; for public repositories, that
label and `ubuntu-24.04` have the same advertised 4-vCPU, 16-GB-memory,
14-GB-storage envelope.
[GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
GitHub calls containerized services and multi-architecture builds ideal ARM
runner workloads and says native execution eliminates emulation overhead.
[GitHub: ARM64 standard runners](https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/)

## Controlled external evidence

This repository compares GitHub-hosted Actions runners with the same advertised
resource envelope while both execute pinned `linux/arm64` workloads:

| Workload | Native timed-stage median | x64 + QEMU timed-stage median | Median paired ratio | Evidence |
| --- | ---: | ---: | ---: | --- |
| Google Brotli extension, 135 tests, 64 MiB round trip | 25.48 s | 334.92 s | 13.36x; 5/5 favored native | [results](results/2026-09-03/RESULTS.md) |
| CPython 3.14.7 build, 1,018 tests | 88.84 s | 1,909.94 s | 21.50x; 5/5 favored native | [results](results/2026-09-03/RESULTS.md) |

The time columns are separate marginal medians across blocks. The ratio column
is the median of the five within-block ratios, so it need not equal the quotient
of those two displayed times.

At this sample size, each exploratory bootstrap interval in the generated
report equals the observed paired range; it adds no independent precision and
is not used as decision-grade inference here.

Each pair runs on fresh VMs. Sources, base images, Actions, BuildKit, and QEMU
are pinned; downloads and setup are outside the primary timer; and AArch64 ELF
inspection, ARM64 tests, and post-timing evidence verification gate
every retained observation.

These are target-native build stressors chosen to expose the execution
mechanism. They do not estimate the compile fraction or end-to-end savings of a
typical Copilot task.

In practical terms, the marginal median timed stage was about 25 seconds versus
5 minutes 35 seconds for Brotli, and 1 minute 29 seconds versus 31 minutes 50
seconds for CPython. When an agent repeats this loop, the internal test should
measure whether native execution converts that mechanism advantage into more
successful test-and-repair iterations within a session budget.

This benchmark does **not** run inside Copilot cloud sandboxes. It compares
GitHub Actions runner SKUs to measure a relevant native-versus-emulated
mechanism. GitHub identifies Azure Container Apps Sandboxes as the product
substrate, but neither GitHub's page nor Microsoft's Sandbox overview identifies
the processor architecture/model or the resource tier used for Copilot
cloud-sandbox sessions; the measured ratio is not a current-product speedup.
The underlying Actions CPUs also differ, so the result does not isolate
emulation as the sole cause. An internal experiment must measure the product
outcome.

## “Actions already has ARM”

An ARM64 Actions job is the correct independent merge gate. It can reject an
agent-produced commit, but it is not the agent's persistent ARM64 tool
environment: reproducing and probing a failure crosses another job boundary and
transfers context through logs and artifacts. Native ARM64 execution inside the
session can shorten that diagnostic loop; CI remains final validation.

## Opt-in MVP

For cloud sandboxes:

1. Add an architecture selector to Copilot app and CLI session creation that
   offers `arm64` alongside the current option, with the latter remaining the
   default during preview.
2. Persist architecture with the stopped session and its snapshot, including
   when remote control is used from GitHub Mobile.
3. Show architecture in session UI and logs; require consent before fallback.
4. Allow organization policy, quotas, queue visibility, and ARM capacity
   controls under the existing identity, metering, and isolation model.
5. Preflight GitHub-owned CLI binaries, bundled tools, language runtimes,
   MCP/LSP servers, the root filesystem, and snapshot restore on ARM64. Surface
   incompatible repository-provided binaries instead of silently changing
   architecture.
6. Start with a gated preview for repositories that already publish ARM64
   artifacts or run ARM64 CI. Size that cohort from GitHub's internal telemetry
   before capacity commitments, then expand through explicit opt-in.

For the separate cloud-agent runtime, evaluate allowing an ARM64 runner in the
setup workflow. Do not couple that follow-on to the cloud-sandbox launch.

## Recommended internal A/B test

Randomize eligible ARM-targeted tasks between x64-plus-emulation and native
ARM64, stratified by repository. Hold model, prompt, context, tools, CPU/memory,
task budget, image contents, and predefined tests constant.

Primary metrics:

- share of tasks producing a merge-ready change that passes ARM64 tests;
- time to first passing target-native test and task completion;
- edit-build-test iterations, retries, timeouts, and emulation failures;
- sandbox compute and total product cost per successful task; and
- first-pass success in independent downstream ARM64 CI.

Guardrails:

- provisioning and queue latency at p50 and p95;
- sandbox failure and infrastructure failure rates;
- stop/resume and cross-device continuation reliability;
- human corrective edits, rejected changes, and reverts;
- no regression on architecture-neutral tasks; and
- isolation, network-policy, and organization-policy parity.

Analyze by intention to treat. Separate queue time from execution time, and
report medians, tails, uncertainty, and cost per successful outcome.

## Bottom line

Native ARM64 cloud sandboxes would let Copilot develop and validate an important
class of production software on its target architecture while preserving the
stateful, cross-device workflow that makes cloud sandboxes useful.
