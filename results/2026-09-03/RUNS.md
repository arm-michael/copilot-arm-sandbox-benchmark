# Run ledger

This ledger records every benchmark dispatch in chronological order. Run links
identify workflow attempt 1, and commit links use full SHAs. Only the locked
retained cohort under `raw/` is analyzed for headline results.

## Dataset lock and stopping rule

Primary estimates use only records that:

- have `trial_class=retained`;
- use frozen harness commit
  [`b9d8f62d3a874ecc1fcab110476afec6397f63eb`][commit-final];
- belong to the ten retained run IDs listed below; and
- pass every pairing, architecture, repetition, correctness, evidence,
  attempt-record, and post-timing verification gate.

The immutable methodology specified a minimum of five retained dispatches per
workload. Both cohorts stopped at five, issued in two waves. Every dispatch was
retained; no failed, incomplete, slow, fast, or unfavorable result was replaced
or extended with an extra run. The final report records the observed collection
size but does not retroactively claim that an exact-five rule was committed in
the frozen protocol.

Smoke tests and pilots are excluded by class. The earlier Brotli cohort is
excluded in full by harness commit. Any final retained failure remains listed
and is handled by the documented analyzer rules.

## Experimental progression

| Stage | Run(s) | Harness | Disposition and rationale |
| --- | --- | --- | --- |
| Architecture smoke test | [`33786752195`][run-smoke] | [`658b823664124ae574d398acff1fb39d021c577a`][commit-smoke] | Successful validation only. Confirmed an AArch64 native host, x86-64 comparison host, AArch64 targets, and QEMU/binfmt registration. |
| Initial Brotli pilot | [`33787163560`][run-brotli-failed] | [`0130174b79a5c4dbb8331c1853bd97a6cc5ce74e`][commit-initial-pilots] | Both treatments failed because the evidence step looked for the extension in the wrong source path. Diagnostic pilot only. |
| Initial CPython pilot | [`33787162944`][run-cpython-cancelled] | [`0130174b79a5c4dbb8331c1853bd97a6cc5ce74e`][commit-initial-pilots] | Native failed because CPython 3.14.7 no longer contains `test_unicode`; the still-running emulated job was cancelled after that workload defect was diagnosed. Diagnostic pilot only, not excluded because of timing. |
| Corrected Brotli pilot | [`33787825971`][run-brotli-corrected] | [`54678a35dbf4f2f4e347482d175def6b99341a29`][commit-corrected] | Both treatments passed after correcting the extension and import paths. Excluded by `trial_class=pilot`. |
| Corrected CPython pilot | [`33787825923`][run-cpython-corrected] | [`54678a35dbf4f2f4e347482d175def6b99341a29`][commit-corrected] | Both treatments passed after replacing `test_unicode` with `test_str`. Excluded by `trial_class=pilot`; methodology review then identified its unpinned test seed. |
| Pre-freeze Brotli cohort | [`33788566907`][run-prefreeze-1], [`33788567212`][run-prefreeze-2], [`33788567348`][run-prefreeze-3] | [`54678a35dbf4f2f4e347482d175def6b99341a29`][commit-corrected] | All three were marked retained and passed, but the entire cohort is validation-only because it predates the final reviewed protocol and frozen harness. Original labels and results remain visible. |
| Final-harness pilot | [`33790265616`][run-final-pilot] | [`b9d8f62d3a874ecc1fcab110476afec6397f63eb`][commit-final] | All four jobs passed. Both CPython treatments used seed `20260903`, passed all five suites and 1,018 tests, produced AArch64 ELF evidence, and passed post-timing verification. Excluded by `trial_class=pilot` regardless of timing. |
| Final retained Brotli cohort | [`33790856930`][run-brotli-1], [`33790860277`][run-brotli-2], [`33790863851`][run-brotli-3], [`33791562096`][run-brotli-4], [`33791565338`][run-brotli-5] | [`b9d8f62d3a874ecc1fcab110476afec6397f63eb`][commit-final] | All five runs completed successfully; five pairs are eligible and zero are excluded. |
| Final retained CPython cohort | [`33793446944`][run-cpython-1], [`33793453246`][run-cpython-2], [`33793459137`][run-cpython-3], [`33797228069`][run-cpython-4], [`33797234274`][run-cpython-5] | [`b9d8f62d3a874ecc1fcab110476afec6397f63eb`][commit-final] | All five runs completed successfully; five pairs are eligible and zero are excluded. |

## Why the earlier retained-labeled runs are excluded

Review after the three `54678a3` Brotli runs added mandatory nonempty evidence
checks, validation of the passing test-result record, a post-timing verification
record for each treatment, same-commit enforcement, attempt-record enforcement,
and a fixed CPython regrtest seed. Because the earlier cohort could not satisfy
that final protocol contract and preceded the harness freeze, all three runs
are excluded together even though all three passed.

The rule is cohort-wide and commit-based. None of the three was selected or
rejected according to elapsed time or speedup. At `b9d8f62`, the corresponding
Brotli and CPython pilot pairs each passed before retained collection for that
workload began.

## Final retained run accounting

| Workload | Intended paired blocks | Complete eligible pairs | Excluded pairs |
| --- | ---: | ---: | ---: |
| Brotli | 5 | 5 | 0 |
| CPython | 5 | 5 | 0 |

`RESULTS.md`, `results.csv`, and `pairs.csv` are derived only from the eligible
retained records with:

```text
--expected-git-sha b9d8f62d3a874ecc1fcab110476afec6397f63eb
```

[commit-smoke]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/commit/658b823664124ae574d398acff1fb39d021c577a
[commit-initial-pilots]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/commit/0130174b79a5c4dbb8331c1853bd97a6cc5ce74e
[commit-corrected]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/commit/54678a35dbf4f2f4e347482d175def6b99341a29
[commit-final]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/commit/b9d8f62d3a874ecc1fcab110476afec6397f63eb

[run-smoke]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33786752195/attempts/1
[run-brotli-failed]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33787163560/attempts/1
[run-cpython-cancelled]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33787162944/attempts/1
[run-brotli-corrected]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33787825971/attempts/1
[run-cpython-corrected]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33787825923/attempts/1
[run-prefreeze-1]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33788566907/attempts/1
[run-prefreeze-2]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33788567212/attempts/1
[run-prefreeze-3]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33788567348/attempts/1
[run-final-pilot]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33790265616/attempts/1
[run-brotli-1]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33790856930/attempts/1
[run-brotli-2]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33790860277/attempts/1
[run-brotli-3]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33790863851/attempts/1
[run-brotli-4]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33791562096/attempts/1
[run-brotli-5]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33791565338/attempts/1
[run-cpython-1]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33793446944/attempts/1
[run-cpython-2]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33793453246/attempts/1
[run-cpython-3]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33793459137/attempts/1
[run-cpython-4]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33797228069/attempts/1
[run-cpython-5]: https://github.com/arm-michael/copilot-arm-sandbox-benchmark/actions/runs/33797234274/attempts/1
