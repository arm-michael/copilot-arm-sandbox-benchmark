# Benchmark results

Harness commit: `b9d8f62d3a874ecc1fcab110476afec6397f63eb`.

Generated from append-only JSONL records. Speedup is x64-hosted QEMU time divided by native ARM64 time; values above 1 favor native ARM64.

| Workload | Phase | Paired observations | Pairs favoring native | Median x64 + QEMU | Median native ARM64 | Median speedup | Geometric mean speedup | Exploratory paired bootstrap 95% interval |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Brotli | build test | 5 paired blocks | 5/5 | 334.92 s | 25.48 s | 13.36x | 13.12x | 12.48x–13.50x |
| CPython | build test | 5 paired blocks | 5/5 | 1909.94 s | 88.84 s | 21.50x | 20.29x | 13.32x–24.46x |

Observed paired speedup range for Brotli: 12.48x–13.50x.
Observed paired speedup range for CPython: 13.32x–24.46x.

Treatment-time columns are marginal medians across blocks; median speedup is the median of within-block ratios and need not equal their quotient.
Separate fresh-VM blocks are treated as analysis units, but shared fleet and time-window effects can correlate them.
The bootstrap interval is exploratory for this small convenience cohort; the paired values, direction count, and observed range are the primary interpretation.

Primary measured-command success: 20/20 (100.0%).
Intended treatment attempts: 20; treatments reaching primary timing: 20.

Excluded primary blocks: 0.

Actions runners are a mechanism proxy, not the Azure Container Apps Sandboxes substrate used by Copilot cloud sandboxes. CPU models also differ, so these ratios compare the offered runner choices rather than isolating pure QEMU overhead or measuring current Copilot sandbox speed.
