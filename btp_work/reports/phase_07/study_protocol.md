# Current completion notice

This protocol/run guide is preserved below as the pre-execution record. The study and cap-only follow-up are now terminal and analysed. [Final research](../../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [coverage](../../final/idea1_research_release_v1/scope_coverage.csv), [D010](../decisions/D010_BOUNDED_IDEA1_COMPLETION.md), and [gate](../../final/idea1_research_release_v1/completion_gate.json). Older “not started” or “remaining” statements below describe the frozen preparation checkpoint.

---

# Phase 7 incremental study protocol

Owner: Codex /root, 31 October 2026. Status: in progress. The original phase has broader requirements than the already completed paper-matrix studies; none are silently dropped.

The [reuse inventory](reused_studies.json) freezes the five existing result CSVs: 132 baseline, 132 movement-model, 396 lookahead, 792 assignment and 528 repair rows. Their prior reports, gates, failed attempts and source snapshots remain intact. Existing 66-target compiler campaigns are not repeated. This task adds comparisons and analysis that did not exist in those matrices.

## New factorial experiment

[Frozen protocol](../../runs/idea1_extension_v1/protocol.json) fixes eight inputs before execution: QFT5/QFT10, two QTetris Table-II circuits, two MaxCut-type QAOA circuits on seeded simple three-regular graphs (N=6/8, p=2, explicit cost/mixer angles), and two genuine Haar-random SU(4) quantum-volume model circuits (N=6/8, depth=4). The latter are model workloads, not a measured quantum-volume score. The five paired routing seeds are 41–45. At seed42, three timing executions are retained; additional timing repeats are not independent quality samples. This gives 320 quality rows and 128 timing-only rows, 448 rows in total.

The complete 2^3 matrix is:

| Axis | 0 | 1 | Isolation |
| --- | --- | --- | --- |
| L | exact legacy parking | next-four-event parking | same input, oriented assignment and geometry |
| A | sum-distance, expanded slots | composite bottleneck, expanded slots | same candidate-pool policy; objective/metric component changes |
| R | disabled | small, at most four evaluations | same prepared parent and complete replay acceptance |

The repair API previously rejected legacy parking at its entry guard. A private copy of that replay function broadens only this guard, allowing the already implemented exact legacy picker. It does not modify any accepted scientific source. Every L/A baseline is checked for exact instructions and final routing RNG against the unchanged Phase05 compiler. Five acceptance groups also verify scoped restoration, genuine-generator inputs, unchanged source hashes and complete original-circuit semantics on QAOA/QV6 after restoring one-qubit operations. These proofs do not imply that omitted one-qubit physical timing has been measured.

The pilot measured QFT5 and QAOA6 under the identical protocol, four L/A baselines and both repair budgets. It accepted 16 rows in 17.79 seconds total, observed peaks below 140 MiB. It is a small cost estimate rather than a guarantee for deeper QTetris inputs. Its two identical seed42 measurements are reused with hashes and original attempt paths, not recompiled. Per-worker wall limit is 240 seconds, observed process-family memory safeguard is 4 GiB, numerical thread count is one, hash seed is zero, and the campaign has a 3,600-second finite budget. Unrun, failed and timed-out cells remain explicit coverage outcomes. There is no outcome-based parameter tuning.

Timing includes baseline compilation/validation and complete repair work. Independent compatibility recompilation and final artifact export are outside that timer but inside recorded process wall time. Workers run serially; ordinary host activity and concurrent small analysis/document preparation are not controlled away. Timing repeats therefore characterize variability and do not establish cross-method speedups. Baselines shared across R controls are charged to both comparison rows.

## Additional analysis, without new compiler runs

The [analysis script](../../analysis/phase08_incremental.py) reads immutable completed matrices. It adds circuit-cluster bootstrap intervals, aggregation sensitivity, transport-sensitive versus native-gate error budgets, same-scope repair cost effectiveness, per-target Pareto choices, same-circuit grid pairs and fixed-trace transfer/coherence sweeps. A complete independent evaluator replay verifies the closed-form sensitivity transformation on a representative trace. These are model-sensitivity checks, not confidence intervals on a real device and not profile-driven replanning experiments.

## Remaining original-study obligations

QFT through100 with matched primary baselines; broader QAOA/QV size/depth coverage; primary DasAtom comparisons on the newly generated circuits; profile-driven heating/trajectory/cooling and resource sweeps; requested equal/critical-path weighting comparison; and any unperformed scaling/seed axes remain unresolved until evidence is saved. Additional compiler capabilities are assessed in [baseline_capabilities.md](baseline_capabilities.md). A completed small extension matrix does not by itself close the complete original Phase7 gate.

Commands, from btp_work:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 tests/phase07_extension_acceptance.py --out reports/phase_07/extension_tests_new
.\.venv\Scripts\python.exe -B -X utf8 tools/phase07_extension.py prepare --study runs/idea1_extension_new
.\.venv\Scripts\python.exe -B -X utf8 tools/phase07_extension.py pilot --study runs/idea1_extension_new
.\.venv\Scripts\python.exe -B -X utf8 tools/run_phase07_incremental.py --study runs/idea1_extension_new
```

Existing output directories are immutable. The actual frozen experiment is idea1_extension_v1; use its request/case manifests for inspection. Reproduction requires the recorded pinned environment, not an unpinned replacement compiler.
