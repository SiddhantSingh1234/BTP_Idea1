# Current completion notice

This protocol/run guide is preserved below as the pre-execution record. The study and cap-only follow-up are now terminal and analysed. [Final research](../../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [coverage](../../final/idea1_research_release_v1/scope_coverage.csv), [D010](../decisions/D010_BOUNDED_IDEA1_COMPLETION.md), and [gate](../../final/idea1_research_release_v1/completion_gate.json). Older “not started” or “remaining” statements below describe the frozen preparation checkpoint.

---

# Remaining experiments: unattended measurement commands

The production study is prepared at `runs/remaining_experiments_6h_v2`. It has **not been started**. Running a command below starts a hidden, detached measurement controller; no active agent or open terminal is required. Keep the computer powered on. Automatic idle sleep is inhibited while the controller runs; manual sleep/shutdown still interrupts measurements.

From `C:\Users\hp\Documents\BTP`, run everything with one command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-RemainingExperiments.ps1
```

The command resumes the same frozen study on subsequent launches. It skips successful, unsupported, invalid, error, timed-out and out-of-memory cells already measured at the same frozen settings. Interrupted cells have at most one further attempt. Original completed studies and existing raw results remain unchanged.

## Separate groups, if preferred

Use the same command with one selector:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-RemainingExperiments.ps1 -Suite Weighting
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-RemainingExperiments.ps1 -Suite Assignment
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-RemainingExperiments.ps1 -Suite Hardware
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-RemainingExperiments.ps1 -Suite Workloads
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-RemainingExperiments.ps1 -Suite Scale
```

The commands share one cumulative six-hour budget and execution lock. Run one at a time; they are not a request for parallel timing measurements. The default command selects all remaining groups. Relaunching after a group finishes continues other unfinished groups without repeating completed cells. The controller does not extend an exhausted budget automatically.

## Frozen portfolio and limits

| Group | Cells | Measurement |
| --- | ---: | --- |
| Reused reference controls | 24 | Existing validated h4/expanded-composite/no-repair schedules, quality only; no invented fresh timing |
| Weighting | 120 | Uniform versus critical-remaining-CZ-depth parking, gamma0.5/0.9/1; eight representative cases, three router seeds |
| Assignment | 96 | Remove conflict/future/heating/transfer individually, expanded candidates held fixed; eight cases, three seeds |
| Hardware | 129 | Replan under heating/acceleration/coherence/transfer assumptions and parking-area grids20/35; separate finite-bank cooling transforms |
| Larger QAOA/QV | 96 | Genuine QAOA10/12 with p2/4, QV10/12 with depth8/16; three router seeds; original RFT/corrected RFT/proposed small repair/corrected DasAtom |
| QFT scale | 64 | QFT65/70/75/80/85/90/95/100; two router seeds; the same four methods on11x11 hardware |

There are529 planned cells, of which505 are new capped worker measurements. All individual worker caps sum to18,090seconds (5hours1minute30seconds). The controller has a shared cumulative six-hour budget, leaving headroom for preparation/integrity checks, logging and serialization. This is a finite budget, not a promise that every scientific calculation succeeds. Slow, invalid, unsupported and out-of-memory outcomes remain explicit; unstarted cells remain visible when the budget is insufficient.

The workers are serial, one numerical thread, hash seed0, with a4-GiB observed process-family safeguard. Small decision/hardware cells have18-second caps; larger family cells45–90seconds; QFT cells45–150seconds depending on method. Individual time limits include imports and output persistence. Per-stage timer definitions accompany measurements; process wall time provides the common outer scope. Timed-out durations are censoring limits, not successful execution times.

Large QFT uses11x11 because the completed DasAtom QFT60 measurement was roughly17seconds there versus1,224seconds on35x35. This avoids deliberately scheduling known expensive large-grid VF2 cases. Every compared method shares the requested grid, interaction/restriction radii and normalized circuit. Existing small-grid interaction slots remain frozen; capacity/feasibility failures are recorded rather than silently enlarging hardware. Other original grid studies remain available up to60qubits.

The critical-weight addition is separately versioned and independently tested. Its weight is the longest remaining CZ-DAG path length, normalized among queried resolved events. It changes parking only, leaving the assignment future predictor unchanged. Equal-depth weights recover the original potential. Existing accepted source files are not edited. All runtime sources/configurations are frozen under this study's `frozen/`, and all input hashes are verified.

The first prepared v1 directory is retained as an unstarted alternative containing large-grid QFT. The launcher deliberately defaults to **v2**; do not start v1 for this budgeted study.

## Outputs and status

Measurements: `btp_work/runs/remaining_experiments_6h_v2/results.csv`.
Progress: `progress.json`; remaining shared budget: `budget.json`; frozen protocol: `manifest.json`.
Every attempted cell has its request, stdout/stderr, attempt record, observed peak memory, source hashes and available schedules/validation under `measurements/`.

Read status without changing the study:

```powershell
.\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\remaining_experiments.py status --study .\btp_work\runs\remaining_experiments_6h_v2
```

Optional stop (does not delete evidence):

```powershell
.\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\remaining_experiments.py stop --study .\btp_work\runs\remaining_experiments_6h_v2
```

`selected_measurements_finished` means all selected cells have terminal measurement outcomes. It does not mean all succeeded, that every original research requirement is closed, or that the results have been scientifically analysed.

## What will not run

There is **no automatic research analysis, Markdown interpretation, report generation, slide generation or Idea2 implementation**. A later agent should inspect all outcomes, compare only matched completed pairs, retain failures and update Markdown research analysis. Hardware calibration and unresolved historical paper provenance remain limitations; no runtime command can manufacture them.

## Tested evidence

- Seven mathematical/scope/profile/source acceptance groups pass: `bounded_campaign_tests_01/result.json`.
- Real detached smoke: seven accepted schedules independently replayed, plus a retained finite-resource failure and a deliberate forced timeout: `bounded_campaign_smoke_01.json`.
- Partial-group then all-group resume and repeat-launch idempotence pass: `bounded_resume_01/result.json`.
- Final prepared source/input checks are in `bounded_campaign_launch_verification.json`.
