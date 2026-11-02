# Final benchmark analysis checkpoint, 29 October 2026

The full132-schedule benchmark and model-change analysis are complete. Every schedule reconstructs exactly and every serialized evaluator output replays identically. Same decisions; one analytical no-cooling profile.

[Audited results and plots](../reports/final_benchmark_analysis_01/report.md) | [Final gate](../reports/final_benchmark_analysis_01/final_gate.json).

Earlier checkpoints below remain historical evidence.

---

# Phase 03 handoff: movement timing and error model

Owner Codex /root,28 October2026. **Status: complete within the declared analytical model scope.** [Final gate](../reports/phase_03/gate_01.json) passes. Phase02 engineering is accepted complete by the user under [D004](../reports/decisions/D004_PHASE03_MODEL_AND_DEPENDENCY.md); Phase01 benchmarks/final dataset acceptance remain in progress. No applicable AGENTS.md was found in workspace ancestors/new-work subtree. All new work is in btp_work; Intern_Report was excluded. No subagents or benchmark controllers were launched.

## Scope and identity

NEW [movement_error package](../implementation/movement_error): source-backed profiles, compatible cubic timing/positions, labelled linear/triangular heating surrogates, stable conditional survival, event-time gate heating, explicit transfers/cooling, per-qubit exposure and local prediction. [Specification](../reports/phase_03/model_specification.md), [citations](../reports/phase_03/source_research.md), [changes](../reports/phase_03/change_ledger.md), [validation](../reports/phase_03/validation_report.md).

Seven [profiles](../configs/hardware) and a [new envelope schema](../configs/schemas/schedule_phase03_v1.schema.json) leave trace-v1 and original implementation unchanged. Envelope: immutable source trace, resolved profile, hashes and transformation log. No Git commit identity is invented: [tests04 hashes](../reports/phase_03/tests_04/result.json), [pilot03 hashes](../runs/phase_03/pilot_03/error_budget_pilot.json). Source pins remain RFT3d1f09233c2acd357fd9fbfad1b5300a921d301a and DasAtom73a6bdf0fd200b2733745211eaf2e0c1e17f496a.

Historical scoring delegates to the untouched scorer. Rescore keeps frozen events identical; retime changes time/trajectory; retime_and_cool adds explicit operations/carrier handoffs. Ordered gate/movement choices stay fixed and hashed. Changed schedules are not compiler improvements.

## Actual tested commands

Working directory C:\Users\hp\Documents\BTP, existing Python3.13.2 venv. Existing destinations are immutable: use fresh suffixes to rerun. Model/CLI use stdlib; tests use existing SciPy/Phase02 dependencies; plots use existing Matplotlib. PDF tools are isolated from the benchmark environment.

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_03_acceptance.py --out btp_work/reports/phase_03/tests_04
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_02_acceptance.py --out btp_work/reports/phase_03/phase02_regression_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/run_phase03_pilot.py --out btp_work/runs/phase_03/pilot_03
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/phase03_model.py rescore --trace btp_work/runs/phase_03/pilot_03/raw/sources/synthetic_heating --profile btp_work/configs/hardware/frozen_ideal.json --out btp_work/runs/phase_03/cli_rescore_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/phase03_model.py transform --trace btp_work/runs/phase_03/pilot_03/raw/sources/synthetic_heating --profile btp_work/runs/phase_03/cli_stress_profile_01.json --mode retime_and_cool --out btp_work/runs/phase_03/cli_cooling_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/phase03_model.py check --schedule btp_work/runs/phase_03/cli_cooling_01/schedule.json --out btp_work/reports/phase_03/cli_cooling_check_01.json
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/phase03_model.py evaluate --schedule btp_work/runs/phase_03/cli_cooling_01/schedule.json --out btp_work/reports/phase_03/cli_cooling_evaluate_01.json
```

All16 new groups and14 unchanged Phase02 groups pass. All CLI paths return ok. Exit codes:0ok,2invalid,3unsupported. Legacy score availability is separate from physical validation.

## Acceptance and results

All five mandatory criteria are mapped in the [validation report](../reports/phase_03/validation_report.md). [Worked budget/atom states](../reports/phase_03/worked_budget.md), [pilot](../reports/phase_03/error_budget_pilot.md), [CSV](../reports/phase_03/error_budget_pilot.csv), [56 raw evaluations](../runs/phase_03/pilot_03/raw), [prediction replay](../runs/phase_03/pilot_03/prediction_vs_replay.json).

Pilot03:12ok,41unsupported,3invalid, all retained. QFT5 conditional ordering does not reverse. The corrected QFT10 control stays separate from native invalid routing. Synthetic cooling lowers E46.585 to.862618 while increasing time413.132us to2350.532us and consuming three banks. This is an analytical extra-hardware tradeoff, not an algorithmic/device-performance gain. Cooling has6 atom-events,12CZ,24H,12 extra transfers;256 initial spare atoms and bank registration/preparation time are explicit. No-cooling profiles never reset n. Exhaustion is unsupported.

## Next-phase interface

Import local_batch_cost from implementation.movement_error.physics. Supply current n, distances in um, resolved profile, optional known shared duration, explicit next CZ pairs and full register for exposure. Marginal terms exclude unsupplied suffix gates/cooling; threshold triggers require full replay. Too-short trajectories and infinite baseline marginals are rejected. One-next-gate prediction error is3.5e-18E; omitting another CZ misses5.9521e-6E. Accept schedule changes using full make_schedule/evaluate replay.

Retiming supports serial transport/transfer stages and parallel declared CZ batches. Independent overlapping stages are rejected rather than silently serialized. A common-monotone-progress projection reuses Phase02's independent geometric proof; Phase03 independently checks bounds, timing, finite banks, suboperations, resources and physical handoff.

Scoring excluding validation is linear in event populations/register size; boundary sorting O(M log M). Inherited geometry may cost O(M*A^2), and simultaneous interval checks can be quadratic. Retained source/envelope/audit storage is O(M+A) up to event populations. Pilot8.33s includes serialization/plots, not compilation. Peak RAM was not measured.

## Limitations and next smoke

This is a mixed-source analytical model, not measured RFT calibration. Effective coherence assumes control/decoupling; omitted original computation1Q gates/pulse errors remain outside timed scope. Heating is harmonic and phase-averaged. Source-like80kHz/38nm is a paper scenario, not asserted isotope/mass consistency. Native physical evidence remains incomplete. Banks use declared hypothetical storage/registration/preparation/transfer primitives, not continuous optical-control proof. Vacuum/background heating and correlated noise are not invented. Phase01 final acceptance and exact manuscript provenance remain open.

Next eligible implementation is Phase04 using these APIs; its heuristics are not implemented here. Minimal smoke: rerun the check command above with a NEW report path. Expect ok,3 cooling episodes,6 cooled atom-events and final logical carriers on bank2. Keep native, corrected and extra-resource tracks separate. The Phase01 controller/audit continues independently.

Final tested acceptance command:

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/check_phase03.py --out btp_work/reports/phase_03/gate_01.json --finalize
```

All final gate checks pass. Phase01 benchmark/dataset completion is not claimed.

## Full comparison execution review, 29 October 2026

The Phase03 matched comparison reuses saved Phase01 RFT instructions and DasAtom traces; it does not compile either method again. [Execution review](../reports/phase_03/comparison_execution_review_01/report.md) documents the separately frozen execution revision, scoped reuse of identical validation/metrics, repaired Windows launcher, [five passing regression groups](../reports/phase_03/comparison_reuse_tests_03/result.json), and successful detached smoke. Scientific artifacts match the original frozen worker byte-for-byte on six saved cases. The full comparison is queued behind Phase01 to preserve compilation timing isolation; original snapshots remain unchanged.
