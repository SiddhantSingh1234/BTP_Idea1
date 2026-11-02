# Final benchmark analysis checkpoint, 29 October 2026

Complete within D001/D005/D006 pinned-source scope: 132 targets, 198 RFT samples and 66 corrected DasAtom measurements. Independent replay and legacy formulas pass. Historical paper configuration and native physical evidence remain explicit limits.

[Audited results and plots](../reports/final_benchmark_analysis_01/report.md) | [Final gate](../reports/final_benchmark_analysis_01/final_gate.json).

Earlier checkpoints below remain historical evidence.

---

# Phase 01 handoff — paper-focused plan, stopped execution, reused/corrected data

## Current checkpoint: D006, standalone runner ready, 28 October 2026

Owner Codex /root. The user's latest direction is to provide the command so
they can launch the full benchmark. The runner is ready, tested and **stopped**.
From the BTP workspace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-Phase01Benchmark.ps1
```

See [run guide and tested commands](../reports/phase_01/standalone/README.md),
[D006](../reports/decisions/D006_STANDALONE_FROZEN_BASELINE.md), and frozen
`runs/phase01_frozen_baseline_v1/comparison_contract.json`. It runs independently
of an active agent, validates inline, saves progress/results and skips successes
on resume. Automatic idle sleep is inhibited while working; manual sleep/lid,
shutdown and reboot can interrupt it. No startup task is installed.

All 132 targets remain. Sixty-six RFT results/198 timing samples are frozen and
reused; 57 cached DasAtom repairs and all original references are copied as
evidence. The corrected DasAtom compiler needs one fresh timing pass on all
66 configurations because cached repair time is not compile time. Nine of these
still lack a complete schedule. One actual detached QFT5 11x11 measured smoke
already passed in the canonical study; **65 new measurements remain**. It is
reused when the user launches. The full run has not started.

Eight standalone/process groups, 16 paper-focus groups and 14 foundation groups
pass: `reports/phase_01/standalone/tests_03`,
`reports/phase_01/paper_focus_v2/tests_06`, `reports/phase_02/tests_07`.
The process checks exercised real detached compilation, immutable reuse,
cross-process locking, timeout/stop/monitor gaps and controller-crash cleanup.
Earlier failed automation reports remain, followed by fixes and passing tests.

Phase01 remains **in_progress**: missing measurements, final discrepancy
analysis, regenerated figure/table and independent dataset acceptance remain.
Phase04 must be completed/frozen separately and compared on the same 66 RFT
targets, initial placements, scorer and timing/warmup contract, including its
new heuristic overhead. No later heuristic is enabled in this baseline.
Exact manuscript revision/options remain unresolved; native minimum physical
separation/calibrated fidelity are unsupported. Accepted Phase02/03 and other
Phase04 work remain unchanged.

## Historical D005 checkpoint, 28 October 2026

Owner: Codex /root. Research phase remains **in_progress**; benchmark and auditor
execution are **stopped_by_user**, with no long background restart. The accepted
Phase 02/03 engineering statuses and separate Phase 04 work are preserved.
This checkpoint supersedes the historical 726-job execution instructions below.

Read [D005](../reports/decisions/D005_STOP_REDUCE_REUSE_REPAIR.md),
[the revised plan](../configs/studies/paper_focus_v2.json), and
[the revision report](../reports/phase_01/paper_focus_v2/revision_report.md).
The original paper's page 6 was rendered/checked directly: **all 132** numerical
benchmark configurations remain (72 Figure 4, 60 Table II), with all four/three
respective metrics. The Table I worked example remains tested. No paper point
was dropped; exact manuscript revision/options remain unresolved.

At stop, 411 terminal records existed: 376 paper-target attempts and 35 extra
attempts. All raw records and selected worker artifacts match frozen/prior-audit
hashes. Historical summary/CSV were archived before their derived counts were
refreshed. The native compiler worker, vendor sources and all original outcomes
remain unchanged. The old controller has an operational guard refusing to
resume this explicitly stopped study; its pre-guard source is archived.

### Reuse and repairs

- All **66 RFT** paper targets reuse their native results and prior independent
  audits; all existing timing samples stay available.
- All **57 DasAtom** targets with saved layouts have corrected discrete schedules
  in `runs/paper_focus_v2/cached_corrections_05`. No partition, VF2 or embedding
  search was rerun for these corrections. Twenty needed idle-register restoration.
  Active embeddings/gate groups remain unchanged; legal native transitions are
  retained, occupied destinations/cycles are corrected with explicit vacancies.
- **Nine** mandatory DasAtom 35x35 targets lack a complete trace after native
  timeout: QFT35..60 step5, misex1_241, qv_n16_d5 and square_root_7. They remain
  in the plan and [bounded retry queue](../reports/phase_01/paper_focus_v2/final_02/targeted_retry_queue.json).
  No retries have been launched during this update.

Thus 123/132 targets have reused or corrected schedules under the legacy
discrete rules. Physical minimum separation and cross-trap geometry remain
explicitly unsupported; a discrete pass is not physical device validation.
The stricter old single-plane control remains a distinct hypothetical model.
Original invalid results remain invalid and are never overwritten by repairs.

All repeated saved traces agree per configuration. Future broad RFT8/prefix
sweeps and blanket repeats are retired; completed extras/repetitions are kept.
Five actual routing seeds on the fixed worked example pass the small diagnostic
test; this is not a full benchmark seed-distribution claim.

### Actual tested commands and outcomes

From the BTP workspace root; existing output directories are immutable:

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/prepare_paper_focus.py
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/repair_cached_paper_results.py --out btp_work/runs/paper_focus_v2/cached_corrections_05
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/paper_focus_acceptance.py --out btp_work/reports/phase_01/paper_focus_v2/tests_05
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_02_acceptance.py --out btp_work/reports/phase_02/tests_06
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/run_paper_focus.py status
```

Sixteen new-scope and fourteen foundation test groups pass, including 25
adversarial fixtures, all paper coverage, 411 record hashes, selected worker-file
hashes, 66 RFT audit matches, 57 repaired replays, tuple/list normalization,
no-CZ/capacity/full-grid cases, tiny original unitary, five routing seeds, native
route reuse, timeout family cleanup, successful-run reuse and same-cap holds.
Fresh QFT10 and 16-declared/5-active compilation smokes pass and exactly match
cached corrected layouts/gate groups/movements. They are validation pilots,
not timing samples promoted into a performance comparison.

### Remaining measurements and execution

The [joined CSV](../reports/phase_01/paper_focus_v2/final_02/paper_targets.csv)
keeps old native timing statistics and status separate from corrected schedule
metrics. Cached repair duration is **not** full corrected compilation time.
Corrected full-compilation fields remain null where not freshly measured; obtain
fresh timings wherever a corrected-performance comparison relies on them.

The new runner is ready, but the following execution command has **not** been
run: `python tools/run_paper_focus.py run --limit 1` (use the existing venv and
the btp_work prefix from workspace root). It runs at most one missing paper
target, not the 726-job plan. Use an exact `--target` to choose a case. Default
caps are 1800s, qv_n16_d5 3600s, square_root_7 6000s, and observed family memory
4 GiB. Prior successful compatible runs are skipped; a failed identical-budget
attempt is held rather than repeated automatically. An OS lock prevents duplicate
controllers, and validation runs inline rather than in a second auditor.

Finish the nine missing-target measurements and any necessary corrected timing
measurements, then final analysis/table/figure acceptance. Keep censored and
unsupported outcomes explicit. No exact-paper or full physical-validity claim
is made. No proposed heuristic is enabled in this baseline pipeline.

## Historical native campaign checkpoint

The older sections below retain original commands and evidence. Their running
state and 726-job continuation instructions are superseded by D005 above.

Owner: Codex /root. Date: 28 October 2026. **Not complete.** User D001 accepts
latest public sources and fresh measurements, rather than waiting for unknown
manuscript provenance. The user additionally requests all paper targets, required
tests, and justified extra controls, and authorizes independent Phase 02 work
while the campaign runs. No proposed heuristic is enabled.

Required follow-up from the user's latest instruction: after this campaign
finishes, repair invalid runs and rerun the affected baseline measurements.
[D004](../reports/decisions/D004_REPAIR_FAILED_BASELINES.md) defines the order:
preserve native evidence, diagnose failures, correct underlying routing/register
handling separately, independently validate, and rerun the affected algorithm's
target matrix uniformly. The single corrected QFT10 control is not completion
of that campaign. The follow-up is queued and requires implementation; the
current background processes continue the original campaign/audit only.

## Automation and provenance

The running serial controller is `tools/baseline_campaign.py run`. Its frozen
plan is [plan.json](../runs/current_baseline/study_v1/plan.json); raw attempts,
stdout/stderr, requests, worker results/traces and aggregate measurements live
under `runs/current_baseline/study_v1/`. Read
[progress.json](../runs/current_baseline/study_v1/progress.json),
[summary.json](../runs/current_baseline/study_v1/summary.json) and
[measurements.csv](../runs/current_baseline/study_v1/measurements.csv).
The OS lock prevents duplicate controllers. Do not start another controller
while it is alive. The initial controller PID is 25720; trust the current
progress record/lock rather than assuming this PID will persist after restart.

Exact tested plan/run commands, from the BTP workspace root:

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONDONTWRITEBYTECODE='1'
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/baseline_campaign.py plan
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/baseline_campaign.py run --study btp_work/runs/current_baseline/study_v1
```

The plan command refuses an existing plan. The run command resumes, refusing
a second live controller and preserving earlier attempts. Do not mutate the
worker, input copies or frozen plan during this campaign. Status reads are
safe; do not invoke another writer/summary generator on the live study.

Coverage: 12 QFT sizes (5..60 step5), three grids (11/20/35), both methods;
15 Table II circuits, grids 11/35, both methods: **132 native method/grid targets**.
Three timing repetitions plus existing RFT8 and explicit active-prefix controls
produce **726 planned attempts**. A timeout/OOM suppresses redundant same-cap
repetitions and keeps the case for a separately recorded slower retry; omitted
repetitions are planned non-attempts, never measured zero-time successes.

All 27 input circuits have immutable raw and normalized copies and hashes under
`benchmarks/current_baseline_v1/`. Environment/source pins are the accepted
Phase 00 controls. Numeric threads and hash seed are fixed. Compile timings are
native/adaptor regions as labelled, separate from preprocessing, RFT layout,
worker wall time and validation; native RFT/DasAtom scopes are not identical.
Three timing repeats with one seed are not independent quality samples.

## Resource limits and pilots

Full first pass: 300 seconds per worker process family and 4 GiB observed
process-family memory threshold. Sampling is every 0.2s; the memory quantity is
the maximum observed sum of individual process-family peak working sets, including
the Windows venv redirector and real interpreter. All opened owned-family process
handles are terminated at a cap. It is not a compiler-only RSS figure or an
allocation-proof hard cap. A longer retry budget is planned at 1800 seconds for
censored cases; those retries are not yet claimed executed.

The 30-second pilot confirmed slow DasAtom partition searches on QFT20/60 at
35x35. The first monitor saw only the launcher; preserve those pilot records
but do not use their memory readings. See
[pilot_resource_note.md](../reports/phase_01/pilot_resource_note.md).
The corrected short pilot monitors both processes (about 149 MiB for the RFT
smoke, 194 MiB before a deliberate DasAtom timeout) and exercises termination.

## Tests, reference ledger and interpretation

[Acceptance tests](../reports/phase_01/tests_01/result.json): five tests pass,
including all 132 target combinations, every input hash, native/prefix logical
operation identity, independent tiny CZ basis-phase semantics, negative replay
tests, and ten real RFT7/RFT8 tiny seeded compiler fixtures. Actual test command:

```powershell
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tests/phase_01_acceptance.py
```

This test script uses a new immutable output directory and refuses an existing
one. [published_targets.csv](../reports/phase_01/published_targets.csv) contains
132 separately labelled reference/target rows: Table II's printed numbers and
Fig.4 target coordinates (exact plotted numerical values not digitized). These
are not new measurements. Paper configuration/revision remains unknown.

Declared/native register policies remain explicit. Source-native DasAtom drops
trailing inactive qubits; its native result can succeed while a full-register
trace is unsupported. Separate RFT active-prefix controls support matched route-
only comparisons. Never merge native and prefix tracks silently. Source-native
results, boundary replay outcomes and all failures remain archived. No continuous
trajectory or full-original-unitary correctness is claimed by these smoke checks.

## Remaining work and phase gates

The campaign is running; the full dataset is not yet present. All final Phase 01
criteria remain pending dataset completion/analysis: complete target accounting,
repeatability/variability, resource/failure diagnosis, frozen trace fingerprints,
regenerated table/figures, and baseline handoff for the independent audit. Add
required seed sensitivity and longer retries after inspecting first-pass outcomes.
Do not mark Phase 01 complete because the script is automated.

Phase 02 schema/adapters/independent checker may be prepared on immutable completed
outputs and fixtures by user direction. Its full-baseline audit waits for this
campaign; discovered defects must retain the raw baseline and reopen affected
claims. Avoid heavy concurrent testing that would distort compile timings.

## Phase 02 audit checkpoint, 28 October 2026

Current update: [D003](../reports/decisions/D003_PHASE02_SEMANTICS_AND_CONTROL.md)
diagnoses the occupied destination under the paper's batch load/move/unload
interpretation and adds a separate conservative corrected control. It also adds
full original-circuit semantic reconstruction/checks. Fourteen acceptance groups
pass. [The v2 background auditor](../reports/phase_02/live_audit_v2/live_status.json)
checks all repetitions and retains censored/no-trace outcomes. Native invalid
records remain invalid; none was overwritten or replaced by the control.
Phase 02 engineering is delivered; final acceptance awaits this phase's frozen
dataset and full audit. The earlier snapshot below remains historical evidence.

The independent foundation is now implemented; see [Phase 02 handoff](phase_02.md).
[A 123-output snapshot](../reports/phase_02/baseline_snapshot_02/summary.json)
matches final maps and legacy scores but does not establish physical validity.
Its 46 original source-invalid records remain invalid in Phase 01 comparisons.
[D20/D21](../reports/phase_02/discrepancy_ledger.md) flag incomplete trap/transfer
interpretation and missing original one-qubit gates. An immediate unload after
each DasAtom batch yields known SLM occupancy violations in the QFT10 example;
unknown trap evidence is not a repair. Physical-validity and full-original-
unitary claims remain blocked pending explicit evidence/contract and, if
necessary, a separately named corrected baseline. The worker and raw results
were not changed. Phase 01 remains in_progress.

## Windows controller repair, 29 October 2026

The intermittent WinError 5 startup failures were reproduced at Windows job assignment and repaired with suspended worker startup. See [repair report](../reports/phase_01/controller_repair_verification_01/report.md) and [12 passing regression tests](../reports/phase_01/controller_repair_tests_01/result.json). The original frozen study and all attempts remain unchanged. A separately frozen controller repair waits for the active square-root measurement and then recovers only the 11 diagnosed launch failures. At deployment 54/66 DasAtom measurements were successful, alongside 66 reused RFT targets. Phase 1 final acceptance remains pending.
