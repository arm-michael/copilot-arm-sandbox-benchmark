# Retained-evidence audit

This audit is separate from the statistical summary. It reconciles the raw
directory with the documented run ledger and checks that the retained timings
describe successful, like-for-like Linux/ARM64 work.

## Dataset lock

- Frozen harness: `b9d8f62d3a874ecc1fcab110476afec6397f63eb`
- Trial class: `retained`
- Collection size: the immutable protocol required at least five blocks; both
  cohorts stopped at five in two waves, with every dispatch retained and no
  failure replacement or outcome-driven extension
- Primary record: one `build-test` timing per treatment on a fresh VM
- Pairing key: workflow run ID and attempt, workload, and phase

Every included block must have exactly one successful pre-checkout attempt,
primary timing, and post-timing verification record for both treatments at the
same frozen SHA. The analyzer rejects a block with missing repetitions,
duplicate records, setup or measured-command failure, architecture mismatch,
mixed or blank SHA, missing verification, or unexpected trial class. These are
documented eligibility gates; no claim depends on an outcome-based exclusion.

## Run and record accounting

| Workload | Dispatched runs | Treatments attempted | Primary timings | Verification records | Eligible pairs | Excluded pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Brotli | 5 | 10 | 10 | 10 | 5 | 0 |
| CPython | 5 | 10 | 10 | 10 | 5 | 0 |

The run IDs, workflow conclusions, harness revisions, and disposition of every
smoke test, pilot, pre-freeze dispatch, and retained dispatch are recorded in
[`RUNS.md`](RUNS.md). The analyzer is invoked with `--expected-git-sha` and the
full frozen SHA; the raw directory is also reconciled manually against that
ledger because an analyzer cannot discover an artifact that was never
downloaded.

A final GitHub API reconciliation found 19/19 benchmark workflow dispatches in
the ledger: the smoke run, two initial pilots, two corrected pilots, three
pre-freeze Brotli runs, the final-harness pilot, and the ten retained runs. All
ten retained workflow runs completed successfully with two successful jobs and
the frozen head SHA.

## Architecture and correctness

| Check | Brotli | CPython |
| --- | --- | --- |
| Native host is ARM64 and comparison host is amd64 | 10/10 correct | 10/10 correct |
| Target `uname` is `aarch64` | 10/10 | 10/10 |
| Produced ELF identifies as AArch64 | 10/10 | 10/10 |
| Machine-readable test result is `passed` | 10/10 | 10/10 |
| Human-readable test contract | 10/10 ran 135 tests and reported `OK` | 10/10 used seed `20260903`, passed all 5 suites, and ran 1,018 tests |
| Workload-specific output | 10/10 completed the 64 MiB round trip | 10/10 completed the fixed-seed regression subset |

All ten retained Brotli treatments recorded the same compiled-extension digest:

```text
927c0517ed5232ac472e68ca0d7be2938e62524af865a95ec04f61a6de9cd77e
```

They also recorded the same input size, compressed size, and round-trip digest:

```text
brotli-roundtrip 67108864 133 7300e8f707acef387096e060277b8c4ae5494fad8a783846266d9298935a765f
```

The pinned Brotli fixture digest was identical in every treatment. CPython
binary digests are not required to match because build metadata can vary
across fresh VMs; architecture, suite/seed/count, and passing behavior are the
functional equivalence gates.

The pinned source digests were identical within each workload:

```text
Brotli:  0afe09a53c8bad9861c8dd1fc1284308d54f19d2979ba3541cfdcc9b05fe360f
CPython: 62859805f6fdf25e2bcbf3fa3217801e1996887ca33e6a2af80674bdfa2dbe07
```

## Independent timing cross-check

A second pass read only each retained `build-test` record and recomputed the
within-run ratio as x64-hosted QEMU seconds divided by native ARM64 seconds.

| Brotli run | Native (s) | x64 + QEMU (s) | Paired ratio |
| --- | ---: | ---: | ---: |
| `33790856930` | 25.4798 | 344.0273 | 13.5020x |
| `33790860277` | 25.5335 | 341.0512 | 13.3570x |
| `33790863851` | 25.8060 | 322.0572 | 12.4799x |
| `33791562096` | 24.9196 | 334.9156 | 13.4398x |
| `33791565338` | 24.7987 | 318.9297 | 12.8608x |

All five favor native ARM64. The independently recomputed median paired ratio
is 13.3570x and the observed range is 12.4799x–13.5020x, matching the analyzer.

| CPython run | Native (s) | x64 + QEMU (s) | Paired ratio |
| --- | ---: | ---: | ---: |
| `33793446944` | 89.9296 | 1,900.7952 | 21.1365x |
| `33793453246` | 93.2729 | 1,242.2782 | 13.3187x |
| `33793459137` | 88.3977 | 2,162.2358 | 24.4603x |
| `33797228069` | 83.9140 | 1,949.3503 | 23.2303x |
| `33797234274` | 88.8415 | 1,909.9404 | 21.4983x |

All five favor native ARM64. The independently recomputed median paired ratio
is 21.4983x and the observed range is 13.3187x–24.4603x, matching the analyzer.

## Disclosures

One Brotli block (`33790860277`) used a newer x64 runner-image/containerd
version than the other blocks. Docker Engine, Buildx, and QEMU/binfmt versions
were unchanged, and its ratio is near the cohort median. It remains included
under the documented inclusion rule.

The offered x64 fleet supplied four processor models across the ten retained
treatments: AMD EPYC 7763 (4), AMD EPYC 9V74 (4), Intel Xeon 6973P-C (1), and
Intel Xeon Platinum 8370C (1). All ten native treatments reported Neoverse-N2.
CPython ratios ranged from 13.32x to 24.46x while the x64 jobs spanned multiple
CPU models. This design cannot separate processor-model effects from other
fleet or time-window variability; every value remains published, and no model
was selected or excluded.

The physical CPUs and runner images differ between treatments. These checks
establish a comparison of the offered GitHub runner choices, not pure QEMU
causality. They also do not turn the Actions runner comparison into a benchmark
of Azure Container Apps Sandboxes or of current Copilot cloud-sandbox speed.
