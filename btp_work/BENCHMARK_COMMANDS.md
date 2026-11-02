# Benchmark commands: Phases 1, 3, 4, 5 and 6

These commands are for PowerShell. Run them from the workspace root:

```powershell
Set-Location 'C:\Users\hp\Documents\BTP'
```

The launchers run in the background and return immediately. Repeating a launch
command resumes its existing frozen study and skips successful targets. It does
not create a fresh complete benchmark repetition. Existing error, invalid,
unsupported and resource-limit outcomes remain explicit; unchanged terminal
failures are held rather than retried indefinitely.

## Recommended order and purpose

| Order | Run | What it does | New DasAtom compilation? |
| --- | --- | --- | --- |
| 1 | Phase 1 | Establish original RFT results and corrected DasAtom reference schedules | Only unfinished/recoverable DasAtom targets |
| 2 | Phase 3 | Evaluate saved RFT instructions and DasAtom traces under the common movement/error model | No |
| 3 | Phase 4 | Compile lookahead variants and matched controls, then evaluate with Phase 3 | No |
| 4 | Phase 5 | Compile assignment controls/variants on the same RFT matrix, then evaluate with Phase 3 | No |
| 5 | Phase 6 | Repair both fixed Phase 5 starting policies with matched disabled/zero/small/standard budgets, using Phase 3 | No |

Inspect each phase's status/results before starting the next. Production model
comparisons serialize with each other and wait while Phase 1 owns its controller
lock, protecting compilation measurements from competing production workloads.
Avoid starting a new Phase 1 run while another timed comparison is executing.

Phase 3 uses the frozen `extended_no_cooling` analytical profile. The same profile
and declared geometry are used for original, Phase 4 and Phase 5 schedules. It
adds explicit transfers, cubic movement timing, heating/loss and per-qubit
exposure. Comparing scores under different models does not isolate an algorithm
improvement. The scope remains the normalized CZ skeleton and declared analytical
geometry, not experimentally calibrated full-circuit hardware fidelity.

## Phase 1: original benchmark reference

### Start or resume

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-Phase01Benchmark.ps1
```

Uses the verified controller repair and preserves completed measurements and
historical attempts. Its 132 configurations comprise 66 reused RFT targets and
66 corrected DasAtom measurements.

### Status

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\standalone_baseline.py status
```

`measurement_matrix_complete` describes measurement completion. It does not
by itself establish `phase_01_complete`, which also requires analysis and review.

### Results

- `btp_work/runs/phase01_frozen_baseline_v1/results.csv`
- `btp_work/runs/phase01_frozen_baseline_v1/summary.json`
- Saved DasAtom traces: `measurements/<target>/attempt_XX/worker/trace/`

## Phase 3: evaluate original schedules with the new cost model

### Start or resume

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase3
```

Reuses saved RFT instructions and DasAtom traces; it does not run either compiler
again. Retiming/scoring is separate from the reused original compilation time.
Missing DasAtom source schedules remain pending. This provides the common-model
baseline needed for fair Phase 4 and Phase 5 quality comparisons.

The launcher uses the separately verified execution optimization revision.
Larger identical source-trace analyses can be reused within a score; changed
schedules and the independent transformed-schedule projection are still checked.

### Status

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase3
```

### Results

- `btp_work/runs/phase03_matched_benchmark_v1/results.csv`
- `btp_work/runs/phase03_matched_benchmark_v1/summary.json`

## Phase 4: full lookahead benchmark with Phase 3 scoring

### Start or resume

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase4 -Study .\btp_work\runs\phase04_matched_benchmark_v2
```

Use this explicit `v2` study consistently. The older prepared default `v1`
snapshot contains the older Windows launcher; `v2` freezes the repaired source
on its first launch and preserves the older snapshot.

Runs all 66 RFT input/grid targets, a fresh unchanged control, and lookahead
horizons 1, 2, 4 and 8. There are 396 planned result rows, including the reused
original-score row per target. Uses the original benchmark-runner timed region
and the common Phase 3 evaluator. No DasAtom compiler run is needed.

### Status

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase4 --study .\btp_work\runs\phase04_matched_benchmark_v2
```

### Results

- `btp_work/runs/phase04_matched_benchmark_v2/results.csv`
- `btp_work/runs/phase04_matched_benchmark_v2/summary.json`

## Phase 5: full assignment benchmark with Phase 3 scoring

### Start or resume

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase5
```

Runs all 66 RFT input/grid targets: 12 QFT sizes on three grids and 15 Table-II
circuits on two grids. There are 792 planned rows: a reused original-score row,
a fresh original control, and ten fixed controls/variants per target:

1. `phase04_reference` (h4)
2. `sum_distance` (corrected orientation)
3. `bottleneck_distance`
4. `bottleneck_time`
5. `composite_sum`
6. `composite_bottleneck`
7. `sum_distance_expanded`
8. `composite_bottleneck_expanded`
9. `composite_no_conflict`
10. `composite_no_future`

All-slot and optional-displacement pilot diagnostics are excluded from this
fixed full-matrix protocol. This avoids an unnecessary variant Cartesian product.
Weights are unchanged and no best variant is selected from the full results.

Uses the same Phase 3 profile and original benchmark-runner timing region as
Phase 4. Index construction, prefix heating, assignment and parking are charged
inside the timer; setup, scoring and output writing are separate. No DasAtom
recompilation is required. The study is already prepared.

Compare composite objectives with corrected distance-sum at the SAME candidate
budget. Comparing Phase 5 to Phase 4 also includes orientation/assignment changes.
The CSV retains separate deltas for these comparison axes.

### Status

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase5
```

### Results and protocol

- `btp_work/runs/phase05_matched_benchmark_v1/results.csv`
- `btp_work/runs/phase05_matched_benchmark_v1/summary.json`
- [Full Phase 5 protocol and test evidence](reports/phase_05/full_benchmark.md)

## Optional: process one pending target before continuing

Add `-Limit 1` to any launcher to process one additional pending target, then
pause. This still runs that target's configured controls/variants. It is not a
single-variant run. For example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase5 -Limit 1
```

Then resume the full run with the normal command without `-Limit 1`.

## Optional: stop a running campaign

These commands request termination of the current attempt. Committed successful
results are preserved. A later resume repeats the interrupted attempt.

### Phase 1

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\standalone_baseline.py stop
```

### Phase 3

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py stop --track phase3
```

### Phase 4 (same explicit v2 study)

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py stop --track phase4 --study .\btp_work\runs\phase04_matched_benchmark_v2
```

### Phase 5

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py stop --track phase5
```

## Phase 6: full bounded-repair benchmark

The Phase 6 implementation/pilot is complete. This command runs its separate
full paper-matrix benchmark. Run it after Phase 5 has finished: preparation
freezes both accepted Phase 5 starting instruction streams for all 66 targets.
It does not rerun DasAtom or the entire Phase 5 variant matrix.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase6
```

This runs 66 RFT targets x two starting policies (`sum_distance` and
`composite_bottleneck_expanded`) x four repair budgets = **528 rows**. Parking
stays fixed at h=4, gamma=0.9, with the same no-cooling Phase 3 model. Before
repair, each fresh starting schedule must reproduce its frozen Phase 5
instructions, score, input, profile and geometry. The repair options are the
already accepted Phase 6 configs; none were tuned on full Phase 5 results.
The adapter also reproduces the original post-warmup Phase 5 routing RNG state
for every replay, so a different random movement order cannot masquerade as a
repair improvement.

- `disabled`: preserve the preceding policy, check the integration wrapper.
- `zero`: preserve it with repair enabled and zero evaluations, isolate overhead.
- `small`: at most four candidate evaluations per starting policy.
- `standard`: at most twelve candidate evaluations per starting policy across
  its rounds; measure the quality/cost tradeoff against small and disabled.

All four controls are useful for analysis. They expose wrapper overhead, budget
effects, and dependence on the starting policy. Every candidate uses full replay
and common-model validation; unsuccessful trials count toward the budget and
time. Successful targets resume without being repeated. Default study:
`btp_work/runs/phase06_matched_benchmark_v2` (memory-repaired execution).
The original `phase06_matched_benchmark_v1` study is preserved with 42 successful
and 24 OOM targets. Its terminal OOM failures are not retried by the old frozen
controller. The v2 study reruns all 66 targets rather than mixing timings from
the two execution implementations. Defaults now select v2 for start/status/stop.

The two fresh, fully verified stress-case measurements use the identical frozen
v2 worker and full protocol and are retained in the campaign with provenance,
so those expensive cases are not repeated. The remaining targets run normally.
No original v1 measurements are reused.

To make the study explicit when resuming:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase6 -Study .\btp_work\runs\phase06_matched_benchmark_v2
```

The memory repair shares immutable prefix/diagnostic snapshots through copies,
streams large JSON/hash operations, drops an optional event audit that the
original artifact writer already discarded, and releases completed budget data.
The evaluator, candidate ordering, seed/RNG protocol, repair budgets, physical
checks and 4 GiB cap are unchanged. Validation and stress evidence is in
[reports/phase_06/memory_repair.md](reports/phase_06/memory_repair.md).

Read progress and completion:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase6
```

Optional stop, then resume with the original launch command:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py stop --track phase6
```

The Phase 6 runtime fields are `baseline_compile_validate_seconds`,
`repair_wall_seconds`, and `end_to_end_compile_validate_repair_seconds`.
`compile_seconds` is deliberately empty: these end-to-end costs include
validation, prefix capture, rejected attempts and checkpoints, and cannot be
directly compared with Phase 5's narrower original compiler timer. Compare
budgets within Phase 6, and compare common-model quality with the matched Phase
5 starting policies. Artifact export after repair is outside the timer.

The campaign uses a serial owned process family, a 4 GiB observed family memory
cap, and a two-hour wall cap per target covering all eight rows. Manual sleep
can interrupt it. Up to 32 candidate evaluations per target (two policies x
(4+12)) make this more expensive than rescoring saved traces. Disabled/zero
reuse a prepared baseline; full repair trials must be run to assess changes.
No reliable full-run ETA has been measured yet.

The complete protocol and verification are in
[reports/phase_06/full_benchmark.md](reports/phase_06/full_benchmark.md).
Completed Phase 5 interpretation:
[reports/phase_05/full_analysis_02/report.md](reports/phase_05/full_analysis_02/report.md).

## Optional: repeat only the small Phase 5 pilot

The accepted pilot already exists in `btp_work/runs/phase_05/pilot_01`, with
308 evaluation schedules. Repeating it is unnecessary for the full benchmark.
Use this only to repeat the pilot after an intentional change; it is not a
substitute for the 66-target full-matrix run, and its planner timings are not
comparable directly with the full benchmark timings. Run it separately from
production timing measurements because it does not use their serialization lock.

```powershell
$phase5PilotOutput = '.\btp_work\runs\phase_05\evaluation_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\run_phase05_pilot.py --split evaluation --out $phase5PilotOutput
```

## Reading progress

- `running`: the controller currently owns the study and is processing a target.
- `waiting_for_phase01`: waiting to avoid overlap with Phase 1 compilation timings.
- `waiting_for_other_model_comparison`: another production model comparison owns the shared execution lock.
- `paused_at_limit`: the requested additional-target limit was reached; resume normally to continue.
- `interrupted...`: the attempt was not accepted as a valid timing measurement; resume the same study.
- `finished_with_issues_or_missing_sources`: inspect recorded errors/unsupported cases and missing source schedules.
- `measurements_complete`: the configured accepted measurement matrix is complete; scientific analysis/review is separate.

Study directories must exist before status/stop commands can inspect them.
The first launch prepares a missing study. Modern Standby, manual sleep or
shutdown can interrupt workers even with idle-sleep prevention; interrupted
timings are rejected rather than treated as valid compilation times.

`-ExecutionPolicy Bypass` applies to the launched PowerShell process; these
commands do not change the machine-wide execution policy.
