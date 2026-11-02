# Phase 05 handoff: oriented routability assignment

Owner: Codex /root, 29 October 2026. Status: complete within the implementation/pilot scope. [Final gate](../reports/phase_05/gate_01.json) passes all32 checks. Dependency: accepted [Phase04](phase_04.md) and Phase03 model. [D008](../reports/decisions/D008_PHASE05_ORIENTED_ASSIGNMENT.md), [specification](../reports/phase_05/assignment_spec.md), [validation](../reports/phase_05/validation_report.md), [results](../reports/phase_05/pilot_results.md), [research and references](../reports/phase_05/source_research.md). All new artifacts stay inside btp_work; no subagents or internship-report inputs were used.

## Implementation and controls

New [assignment package](../implementation/assignment) provides make_problem and assign over explicit pair/slot/orientation objects; solve handles exact rectangular sum or bottleneck_sum matching. FutureEventIndex/FuturePotential and local_batch_cost are imported unchanged. [Tests](../reports/phase_05/tests_03/result.json) freeze current package/config hashes. [Starting record](../reports/phase_05/start_record.json) freezes all scientific/benchmark sources.

The isolated loader replaces only the unresolved assignment block and retains the accepted parking/layer/batch hooks. The original router is called without changed arguments/random consumption, with a passive observer afterward. No provider source is edited. Every corrected/new objective applies its chosen scored orientation; historical original/Phase04 controls retain their original behavior.

13 [assignment configs](../configs/variants), plus original_legacy as a separate worker label. Candidate budgets com/expanded/all and objective metrics are independent. Composite/no-conflict/no-future/optional-displacement controls share one fixed profile/parking policy. Settings are untuned and not promoted to a best default from this evaluation.

compile_schedule(schedule,n,layout,geometry,baseline_options,lookahead,assignment,profile,circuit=...,routing_seed=...) returns full instructions, assignment/parking/batch records, stage statistics and resolved options. AssignmentContext tracks emitted-prefix heating and passes the frozen state into predictions. Cooling is rejected by this prefix observer rather than silently resetting states.

Trace serialization/evaluation reuses the unchanged Phase04 adapter. Its origin.kind names that common adapter; the complete Phase05 algorithm identity is the request/compilation sidecar and pilot manifest. Preserve those alongside schedule.json and trace/; do not infer the complete variant from origin.kind alone.

## Actual verified commands

Working directory C:\Users\hp\Documents\BTP. The existing Python3.13.2 venv and dependencies are reused. Existing outputs are immutable; use a fresh suffix when repeating:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tests\phase_05_acceptance.py --out .\btp_work\reports\phase_05\tests_03
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\run_phase05_pilot.py --split development --out .\btp_work\runs\phase_05\development_01
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\run_phase05_pilot.py --split evaluation --out .\btp_work\runs\phase_05\pilot_01
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\finalize_phase05_evidence.py --out .\btp_work\runs\phase_05\audit_01
```

The original worker invocation is also saved in every attempt_record.json. For a cheap reproducible smoke, use qft5_ladder7__s42 request from pilot_01/requests with phase05_worker.py --input <that JSON> --grid11 --seed42 --out <fresh path>; use separate --grid 11 tokens. It emits all 14 small control/variant results. This is exactly the interface used by the tested bounded pilot.

17 acceptance groups pass. 56 development and 308 evaluation schedules validate, with 112+462 timing samples (not independent quality trials). All364 replay with identical budgets. Audit independently verifies 2,496 actual matrix optima and 4,405 applied orientations. Original legacy and Phase04 h4 instruction hashes match16 historical case/seed controls. Both full-original-QFT5 semantic checks pass32 basis columns at error8.33e-16.

## Results and interpretation

[CSV](../reports/phase_05/pilot_results.csv), [plot](../reports/phase_05/pilot_results.png), [raw compilation/schedules](../runs/phase_05/pilot_01/raw), [audit](../runs/phase_05/audit_01/audit.json). Expanded composite versus the same expanded distance-sum policy gives10 better/8 tied/4 worse, mean relative E -1.815%. Against corrected CoM distance-sum it gives6/8/8, mean -1.050%; against Phase04 h4 the combined correction/expansion/objective result is11/2/9, mean -2.234%. These axes are not interchangeable. Bottleneck distance/time alone is worse in14/22 comparisons. No consistent all-workload or compilation-speed improvement is claimed.

A hand orientation example and the sum-versus-bottleneck matrix [[0,6],[6,10]] are tested. The former fixes a cost/materialization mismatch; the latter proves that maximum and sum can disagree. Actual new-new conflicts appear in824 pilot placement batches and remain outside the fixed linear cost. Their routed durations/error remain decisive.

Largest observed matrix4x6, independently enumerated synthetic matrix6x7. Actual process-family peak209.54MiB includes imports/all variants, and diagnostic raw files314.29MiB. The specification includes O(ms*(N+A+h)) common-predictor construction, rectangular threshold/sum costs, optional vacancy-estimator overhead and verbose audit space; sparse-index size is not whole-compiler memory.

## Phase 06 entry point and boundaries

A pre-repair schedule is already saved at runs/phase_05/pilot_01/raw/<case>__s<seed>/attempt_01/worker/<variant>/schedule.json with its instructions.txt, compilation.json, trace/, evaluation.json, validation.json and predictor_vs_actual.json. The corrected sum-distance and composite variants provide controlled starting points; no best one is selected. Any later repair must replay the suffix through the common evaluator and charge rejected candidates/time, not accept a proxy-only improvement.

Accepted scope is a bounded assignment implementation and small analytical pilot. Full matched benchmark evaluation, richer candidate scaling, calibrated native geometry, original one-qubit timing and generalization remain open. Extra PDFs/BibTeX are under source_review/phase05_primary. Frozen Phase01/03/04 benchmark executables/raw outputs are unchanged; no controller was stopped/resumed. Phase06 has not been started.

Final tested gate command (use a fresh output on repetition):

```powershell
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\check_phase05.py --out .\btp_work\reports\phase_05\gate_01.json
```

All32 checks pass. All six phase acceptance boxes are complete; later full benchmark/analysis claims remain separate.

## Full matched benchmark launcher, 29 October 2026

A full 66-target paper-matrix track is now implemented and prepared: `Start-ModelComparison.ps1 -Track phase5`. It produces 792 planned rows under the same Phase03 model and original benchmark-runner timed region as Phase04. Ten fixed controls/ablations isolate orientation, objective and candidate-budget effects; DasAtom is not recompiled. [Protocol and commands](../reports/phase_05/full_benchmark.md), [seven passing benchmark test groups](../reports/phase_05/benchmark_tests_02/result.json), and [frozen-study verification](../reports/phase_05/full_benchmark_verification.json). The production study is prepared; full results and acceptance are not yet claimed. Existing scientific assignment code, pilot artifacts and Phase01/03/04 frozen snapshots remain unchanged.
