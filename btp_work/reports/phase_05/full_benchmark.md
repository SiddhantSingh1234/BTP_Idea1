# Full matched Phase 5 benchmark

From C:\Users\hp\Documents\BTP, start or resume:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase5
```

Status:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase5
```

The default frozen study is runs/phase05_matched_benchmark_v1. It is prepared,
not started by this implementation task. It covers all 66 Phase01 RFT input/grid
targets: 12 QFT sizes x 3 grids plus 15 Table-II cases x 2 grids. It retains a
reused original schedule score, a freshly timed unchanged reference, and ten
fixed Phase05 controls/variants per target: 792 planned result rows. No DasAtom
compiler is invoked; DasAtom remains the saved Phase03-evaluated anchor.

Fixed variants:
- phase04_reference (unchanged Phase04 h4)
- sum_distance (corrected orientation, CoM candidates)
- bottleneck_distance
- bottleneck_time
- composite_sum
- composite_bottleneck
- sum_distance_expanded
- composite_bottleneck_expanded
- composite_no_conflict
- composite_no_future

All-slot and optional-displacement pilot diagnostics are deliberately excluded
from the default full-matrix protocol to avoid unnecessary expensive sweeps.
This is a complete workload matrix with a fixed analysis protocol, not a best
variant chosen from full-matrix outcomes. Weights remain the existing untuned
values. Lookahead is fixed h4/gamma .9; no new horizon Cartesian product is run.

Each target uses the original frozen raw/normalized inputs, layout, options and
measured-start global RNG state. The unchanged control must reproduce original
instructions and the final RNG hash before any modified result is accepted.
A reference warmup and a same-state warmup per variant are separate from the
single measured run. Index construction, prefix-heating observation, assignment,
parking and routing are charged INSIDE the original benchmark_runner.run_benchmark
region, matching Phase04. Scoring, file output and module setup stay outside
that region. Old Phase05 pilot planner clocks are not comparable with these
new full-region timings. No confidence interval is inferred from one new sample.

All schedules use the frozen extended_no_cooling Phase03 profile and the common
independent validator/evaluator. Full suffix replay determines accepted scores;
prefix heating must match the final evaluator within 1e-12. Invalid/unsupported
outcomes remain explicit. Changes do not establish calibrated device fidelity
or original one-qubit timing; normalized-CZ and analytical two-plane scope remain.

Use composite versus corrected sum_distance at IDENTICAL candidate budgets to
isolate objective effects. Comparing to Phase04 also includes orientation and
assignment changes; candidate expansion has its own distance-sum control. The
CSV includes deltas versus original, Phase04, corrected sum and expanded sum.

Production AssignmentContext, assignment_core, matching, FutureEventIndex,
FuturePotential and physics functions are unchanged. A benchmark subclass bounds
retained assignment/route/parking snapshots to eight while keeping exact total
counts and complete prefix heating. All trace events and evaluator budgets are
saved. Bounded storage is not an exhaustive audit of every actual matrix.

Execution uses the repaired suspended-root Windows launcher, serial owned workers,
an observed 4 GiB family working-set limit, and 1800 seconds per target worker
covering all its variants. It waits while Phase01 owns its controller lock and
serializes with other model comparisons. A Phase01 overlap invalidates compilation
timings. Successful targets are skipped on resume; interrupted attempts can be
retried; unchanged terminal failures are preserved and held rather than endlessly
retried. Original frozen benchmark files and existing attempts are untouched.
The launcher rejects an incompatible study track/baseline before starting workers.

Validation: all seven groups in benchmark_tests_02 pass. Tests verify all 66 target
identities/configuration hashes and 792 rows, complete instruction/RNG/heating
identity against production on 20 case/variant combinations, retained-diagnostic
limits, real detached Phase04/Phase05 controls, exact Phase04 reference instruction
and E equality, accepted full-replay results, successful target reuse on resume,
rejection of contaminated timings, preservation of original frozen studies, and
wrong-track rejection. Tiny detached smoke runs used an independent test baseline;
the production study remains prepared.

Artifacts:
- tests: benchmark_tests_02/result.json and tests.txt
- isolated full-track smoke: runs/phase05_full_benchmark_benchmark_tests_02
- production study: runs/phase05_matched_benchmark_v1
- worker integration: tools/phase05_comparison_worker.py
