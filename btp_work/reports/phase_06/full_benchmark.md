# Phase 6 full paper-matrix benchmark

The default study is now `runs/phase06_matched_benchmark_v2`, using the scoped
memory repair described in [memory_repair.md](memory_repair.md). The initial v1
campaign finished with 42 successes and 24 OOM targets and remains preserved.
V2 repeats the complete 66-target matrix with one consistent execution version.

This adds an operational benchmark adapter over the completed Phase 6 repair
implementation. The scientific implementation, hardware profiles, fixed pilot
budgets, completed pilot evidence, and existing frozen studies remain intact.
The full campaign is separate from the accepted small pilot.

From `C:\Users\hp\Documents\BTP`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase6
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase6
```

The first command starts/resumes the full study; the second is read-only status.
The source launcher prepares a missing study, freezes code, inputs, environment
metadata, profiles and configs, then runs its frozen controller in the background.
Repeated starts skip successful targets. `-Limit 1` processes one additional
target, including all eight rows. Stop uses `model_comparison.py stop --track phase6`.

## Fixed protocol

| Axis | Values and purpose |
| --- | --- |
| Targets | All 66 original RFT case/grid targets: 36 QFT grid targets and 30 Table II targets |
| Starting policies | Corrected sum-distance and expanded composite bottleneck, both fixed before the full Phase 5 analysis |
| Parking | next_events h=4, gamma=0.9 |
| Model | extended_no_cooling.v1; same Phase 3 evaluator and declared two-plane geometry |
| Repair | disabled, zero, small (4 evaluations), standard (12 total evaluations) |
| Total | 528 final schedule rows; 132 policy baselines, each shared across its four budgets |
| Seeds | Original seed 42, hash seed 0, one thread; frozen layout/options and exact post-warmup Phase 5 routing RNG |
| Acceptance | Valid retained incumbent; strict full-E improvement for each accepted repair; preserved prefix, input and caller RNG |
| Resources | One serial owned process family; observed 4 GiB memory cap; 7200 s per complete target |
| Reference | Completed default Phase 5 study must use the same frozen Phase 1 baseline |

Preparation freezes the Phase 5 manifest/results and both starting instruction
files for every target. Every fresh baseline is checked against those instruction
hashes, full E (absolute tolerance 1e-12), normalized input, profile and geometry.
Any mismatch is an explicit failed target, rather than a silently changed control.
There is no new DasAtom compilation: the prior Phase 3 evaluation of saved DasAtom
traces remains the cross-algorithm anchor.

The accepted small-pilot replay API seeds the global router RNG directly.
The full Phase 5 benchmark instead inherits the global RNG state after layout
sampling and unchanged compiler warmup. NetworkX's movement batching consumes
that state, so resetting to 42 would confound repair with a new random routing
outcome. The adapter reconstructs and checks the recorded Phase 5 measured-start
RNG hash and saves the full state. A scoped copy of the accepted replay function,
using identical bytecode and a random-module facade, supplies that state at its
seed call on every replay. Its caller state restoration remains unchanged.
The accepted source files and pilot outputs are not edited. The case recipe
binds the routing-state hash; `routing_rng_state.json` supplies the full state
for reconstruction. This adapter is restored after the worker finishes.

Disabled and zero must preserve schedule, instructions and final routing RNG.
Each enabled budget starts independently from the same prepared baseline;
standard does not start from the small-budget result. Accepted candidates have
strict complete-E gains, but neither a larger budget nor the locally best
surrogate guarantees a larger final gain because repair changes later proposals.
Invalid/rejected/failed trials still consume evaluation budget and elapsed time.

The adapter calls the unchanged `prepare` and `repair` APIs. It deliberately
retains the production full replay, physical boundary capture, checks and audits.
It does not cap away scientific state or replace the evaluator with a heuristic.
One preparation warmup per policy is discarded; one measured preparation is
shared. All four repair calls independently revalidate their supplied incumbent.

## Timing and stored evidence

`end_to_end_compile_validate_repair_seconds` is measured preparation plus external
wall time around the repair API. Preparation includes context setup, source-hook
loading, canonical mapping, compilation and validation/scoring. Repair time
includes incumbent copy/revalidation, generation, every rejected/failed full
replay, scoring, rollback, accepted checkpoint writes and final integrity work.
Saving the final report/artifact export after repair is outside this timer.
Separate candidate compile/scoring/generation/prefix costs aid diagnosis, but
are not an exhaustive additive partition of wall time.

`compile_seconds` is empty because Phase 5 measures a narrower original compiler
region. Comparing the Phase 6 end-to-end value to that field would overstate the
repair slowdown. Compare Phase 6 end-to-end costs against its own disabled/zero
controls, and common-model quality against exact matched Phase 5 baselines.
One sample per variant in fixed order supplies descriptive timings only.
Observed overlap with Phase 1 invalidates all Phase 6 timing fields for that
attempt. Model comparison campaigns share an exclusive execution lock.

Each worker saves its complete case recipe, Phase 5 compatibility checks,
baseline/accepted instruction streams, traces, schedules, validations, metrics,
error terms, proposal plans, candidate audit, accepted history and last incumbent
checkpoint. The summary CSV includes E/F/makespan, movement, retained schedule
hashes, rollback indicators, evaluation/accept counts and timing components.
Existing errors/timeouts remain visible; interrupted attempts can resume.

## Analysis boundaries

The production study is prepared separately from integration smoke studies.
Integration tests exercise the real detached launcher and resume plus all eight
budget/policy combinations on QFT cases and a Table II case on grid 35. They
also check input/source preservation, frozen Phase 6 scientific hashes and
rejection of timings contaminated by a concurrent Phase 1 controller. Evidence:
[full_benchmark_tests_04/result.json](full_benchmark_tests_04/result.json).

Do not claim a complete full-matrix Phase 6 result until all 66 targets and 528
rows are accepted and analyzed. The original pilot remains a small analytical
study. Neither this matrix nor the Phase 5 matrix independently proves hardware
fidelity, a global optimum, generalization to unseen workloads, or reproduction
of the paper under its original assumptions.
