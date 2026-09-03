# Primary sources

## GitHub product and infrastructure

- [About cloud and local sandboxes for GitHub Copilot](https://docs.github.com/en/copilot/concepts/about-cloud-and-local-sandboxes) — cloud sandboxes are ephemeral hosted Linux environments built on Azure Container Apps Sandboxes; Copilot app sessions can use them and cloud sessions can continue across devices.
- [Working with agent sessions in the GitHub Copilot app](https://docs.github.com/en/copilot/how-tos/github-copilot-app/agent-sessions) — the app offers cloud sandbox as a session-location choice.
- [Steering Copilot CLI remotely](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/steer-remotely) — a remotely controlled CLI session can be monitored and steered from GitHub Mobile.
- [Using Copilot cloud agent on GitHub Mobile](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-mobile) — Mobile also starts and tracks the distinct cloud-agent runtime.
- [Configuring the Copilot cloud-agent environment](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-environment) — Copilot cloud agent works in an ephemeral GitHub Actions-powered environment; the documented supported architectures are Ubuntu x64 and Windows x64, and `runs-on` is a supported setup-file setting.
- [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) — public `ubuntu-24.04` and `ubuntu-24.04-arm` runner labels and published 4-vCPU, 16-GB, 14-GB shapes.
- [Arm64 hosted runners for public repositories are generally available](https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/) — availability of public native ARM64 hosted runners.
- [Arm64 standard runners for private repositories](https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/) — later availability of the standard ARM64 runner shape for private repositories.
- [Arm64 on GitHub Actions](https://github.blog/news-insights/product-news/arm64-on-github-actions-powering-faster-more-efficient-build-systems/) — GitHub's explanation that native ARM runners avoid virtualization/emulation overhead and target containerized services and multi-architecture builds.
- [Azure Container Apps Sandboxes overview](https://learn.microsoft.com/en-us/azure/container-apps/sandboxes-overview) — the underlying platform's isolation, lifecycle, snapshot, image, and resource-tier model.
- [Containers in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/containers) — the current service documentation requires Linux `linux/amd64` container images.
- [Azure Container Apps ARM64 request](https://github.com/microsoft/azure-container-apps/issues/569) — Microsoft's public tracker labels ARM64 container-image support as an open roadmap enhancement.

## Why native execution matters

- [Docker multi-platform build strategies](https://docs.docker.com/build/building/multi-platform/) — Docker documents that QEMU emulation can be much slower than native builds, especially for compilation and compression, and recommends native nodes or cross-compilation where appropriate.

## Scale of the target workload

- [AWS Graviton](https://aws.amazon.com/ec2/graviton/) — AWS reports more than 120,000 Graviton customers and positions it for cloud workloads.
- [Azure Cobalt 100 virtual machines generally available](https://azure.microsoft.com/en-us/blog/azure-cobalt-100-based-virtual-machines-are-now-generally-available/) — Microsoft positions its ARM-based CPU for cloud-native workloads.
- [Google Axion C4A generally available](https://cloud.google.com/blog/products/compute/first-google-axion-processor-c4a-now-ga-with-titanium-ssd) — Google positions Axion for general-purpose cloud workloads including web, application, and containerized services.
- [GitHub Octoverse 2023: state of open source and AI](https://github.blog/news-insights/research/the-state-of-open-source-and-ai/) — GitHub reported 4.3 million repositories using Dockerfiles in 2023.
- [CNCF 2025 annual cloud-native survey announcement](https://www.cncf.io/announcements/2026/01/20/kubernetes-established-as-the-de-facto-operating-system-for-ai-as-production-use-hits-82-in-2025-cncf-annual-cloud-native-survey/) — CNCF reports Kubernetes in production for 82% of container users surveyed.

## Pinned workload sources

- [Google Brotli](https://github.com/google/brotli/tree/028fb5a23661f123017c060daa546b55cf4bde29) — exact source revision used by the native-extension workload.
- [Python 3.14.7 release files](https://www.python.org/ftp/python/3.14.7/) — exact CPython source release used by the runtime workload.

## Claim discipline

The product and market statements in the proposal should link to the sources
above. Benchmark numbers must link separately to this repository's raw records
and immutable workflow runs. Conclusions derived by joining those facts are
labeled as inferences, and the Actions-to-Copilot extrapolation is labeled as a
proxy limitation.
