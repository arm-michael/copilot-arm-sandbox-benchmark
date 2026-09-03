# Proposal: opt-in Linux/ARM64 for GitHub Copilot cloud sandboxes

## Decision requested

Add Linux/ARM64 as an opt-in execution architecture for cloud sandbox sessions
started from GitHub Copilot CLI and the GitHub Copilot app. Keep x64 as the
default. Persist the selected architecture when a session is stopped, resumed,
or continued from another device; expose it in the UI and logs; and never
silently substitute x64.

The first target is repositories that build and test ARM64 containers and
native dependencies for Graviton, Cobalt, Axion, and similar production
infrastructure. QEMU should remain a compatibility fallback, but native
execution lets the agent compile, run, inspect, and retest the target artifact
inside one hosted session.

This primary request concerns **Copilot cloud sandboxes**. The Actions-powered
**Copilot cloud agent** is a separate runtime and a related follow-on request.

## The major workload: ARM64 cloud-native service development

A representative session repeatedly:

1. modifies application code, a Dockerfile, or native build configuration;
2. builds a `linux/arm64` image containing C/C++, Rust, Go/cgo, a Python
   extension, a Node native add-on, or another architecture-specific component;
3. executes ARM64 image build steps, tests, startup probes, and binaries;
4. diagnoses ABI, dependency, packaging, or runtime failures; and
5. edits and retests until the target-native artifact passes.

This is more than cross-compilation. Docker treats emulation, native nodes, and
cross-compilation as different strategies and warns that QEMU can be much
slower for compute-heavy work such as compilation and compression.
Cross-compilation also cannot replace every target-architecture Docker `RUN`
step, package-manager invocation, native test, or runtime probe.
[Docker: multi-platform build strategies](https://docs.docker.com/build/building/multi-platform/)

When target-native commands execute through QEMU, the emulation penalty is paid
on every affected iteration. Without native execution, architecture-specific
failures may surface only in an emulated run or downstream ARM64 CI. Native
execution increases target fidelity and is expected to shorten feedback for
this workload; the product effect should be measured internally.

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
Architecture should therefore be a property of the hosted session, not of the
laptop or phone controlling it.

Cloud sandboxes are still in public preview. This is the right time to make
architecture a first-class session property before interfaces, snapshots, and
capacity assumptions harden.

This requires an end-to-end ARM tier, not an Actions-label substitution: an ARM
host and isolation boundary, ARM64 base image and tool cache, compatible
snapshots, capacity, metering, and a GitHub-facing architecture selector. Azure
Container Apps currently documents `linux/amd64` container images as required,
so the cloud-sandbox change likely requires coordination with the underlying
platform team.
[Microsoft: Container Apps containers](https://learn.microsoft.com/en-us/azure/container-apps/containers)

### Related, separate Mobile runtime

GitHub Mobile also directly starts and tracks **Copilot cloud agent** sessions.
[GitHub: cloud agent on Mobile](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-mobile)
That agent works in an ephemeral GitHub Actions-powered environment currently
documented as compatible with Ubuntu x64 and Windows 64-bit runners.
[GitHub: cloud-agent environment](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-environment)

Native ARM64 would benefit that runtime too. Its implementation could allow an
ARM64 runner through `copilot-setup-steps.yml`; that is a second product change,
not the mechanism proposed for Azure-backed cloud sandboxes.

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
can identify the initial cohort directly from repositories already declaring
ARM64 CI, publishing ARM64 images, or opting into an ARM64 sandbox.

GitHub has already validated the adjacent execution mechanism. Native ARM64
Actions runners are available as `ubuntu-24.04-arm`; for public repositories,
that label and `ubuntu-24.04` have the same advertised 4-vCPU, 16-GB-memory,
14-GB-storage envelope.
[GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
GitHub calls containerized services and multi-architecture builds ideal ARM
runner workloads and says native execution eliminates emulation overhead.
[GitHub: ARM64 on Actions](https://github.blog/news-insights/product-news/arm64-on-github-actions-powering-faster-more-efficient-build-systems/)

## Controlled external evidence

This repository compares equal-size GitHub-hosted Actions runner choices while
both execute pinned `linux/arm64` workloads:

| Workload | Native ARM64 | x64 + QEMU | Median paired speedup | Evidence |
| --- | ---: | ---: | ---: | --- |
| Google Brotli extension, 135 tests, 64 MiB round trip | pending retained trials | pending retained trials | pending | pending |
| CPython 3.14.7 build, 1,000+ tests | pending retained trials | pending retained trials | pending | pending |

Each pair runs on fresh VMs. Sources, base images, Actions, BuildKit, and QEMU
are pinned; downloads and setup are outside the primary timer; and AArch64 ELF
inspection, target-native tests, and post-timing evidence verification gate
every retained observation.

These are target-native build stressors chosen to expose the execution
mechanism. They do not estimate the compile fraction or end-to-end savings of a
typical Copilot task.

This benchmark does **not** run inside Copilot cloud sandboxes. It compares
GitHub Actions runner SKUs to measure a relevant native-versus-emulated
mechanism. GitHub identifies Azure Container Apps Sandboxes as the product
substrate but does not publicly document an equivalent sandbox CPU model or
resource shape; the measured ratio is not a current-product speedup. The
underlying Actions CPUs also differ, so the result does not isolate emulation as
the sole cause. An internal experiment must measure the product outcome.

## “Actions already has ARM”

An ARM64 Actions job is the correct independent merge gate. It can reject an
agent-produced commit, but it is not the agent's persistent ARM64 tool
environment: reproducing and probing a failure crosses another job boundary and
transfers context through logs and artifacts. Native ARM64 execution inside the
session shortens that diagnostic loop; CI remains final validation.

## Opt-in MVP

For cloud sandboxes:

1. Add an `x64` / `arm64` architecture selector to Copilot app and CLI session
   creation, with x64 remaining the default.
2. Persist architecture with the stopped session and its snapshot, including
   when remote control is used from GitHub Mobile.
3. Show architecture in session UI and logs; require consent before fallback.
4. Allow organization policy, quotas, queue visibility, and ARM capacity
   controls under the existing identity, metering, and isolation model.
5. Start with explicit opt-in and repositories that already publish ARM64
   artifacts or run ARM64 CI.

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
class of production software in its target environment while preserving the
stateful, cross-device workflow that makes cloud sandboxes useful.
