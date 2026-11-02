# Phase 06 handoff: bounded full-replay repair

Owner: Codex /root, 29 October 2026. Status: complete within the bounded implementation/pilot scope, recorded by the [final gate](../reports/phase_06/gate_01.json). Dependencies: accepted Phase05 and unchanged Phase03 model/common validator. [D009](../reports/decisions/D009_PHASE06_FULL_REPLAY_REPAIR.md), [specification](../reports/phase_06/repair_spec.md), [research](../reports/phase_06/source_research.md), [results](../reports/phase_06/pilot_results.md), [validation](../reports/phase_06/validation_report.md), [changes](../reports/phase_06/change_ledger.md).

## Delivered behavior and controls

The [repair package](../implementation/repair) provides prepare(case, lookahead, assignment, profile, seed=42) and repair(..., options, baseline=None, checkpoint=None, stop_check=None). A baseline argument is an in-memory prepared bundle; supply baseline=None to prepare from the frozen recipe. All inputs remain unchanged. The incumbent contains complete compilation, evaluation, trace and timed schedule. Private proposals change complete legal pair/parking target maps, replay the full circuit, verify its fixed prefix and accept only valid strict complete-E improvements. Rejected/failed trials and exhausted budgets retain a complete feasible incumbent. Supplied baseline scores are independently revalidated. Enabled cooling resources are explicitly unsupported by the accepted planner.

Disabled remains the safe default. Zero, small (4 evaluations) and standard (12 evaluations) are fixed controls in [configs](../configs/variants). They keep the preceding corrected sum-distance or expanded-composite assignment and h=4 parking options unchanged. Numerical tolerance is 1e-12. No best production setting was learned from evaluation. Full immutable requests, seed/config hashes, candidate plans, evaluations, accepted checkpoints and terminal audits are in [development](../runs/phase_06/development_01) and [evaluation](../runs/phase_06/pilot_01).

## Acceptance and evidence

- Disabled/zero preserve the exact Phase05 schedule/instructions and final routing RNG on 50 case/seed/policy baselines.
- All 53 accepted repairs validate and strictly improve complete replayed E. Exact prefix events and complete physical/random-state snapshots are verified.
- Rejections preserve parent occupancy, logical mapping, heating, cooling resources and RNG; forced invalid/route-limit/stop/checkpoint fixtures retain a valid incumbent or explicit baseline failure.
- Deterministic budgets charge every failed/rejected evaluation, full compilation, validation/scoring and local diagnostic cost. [Complexity](../reports/phase_06/repair_spec.md) includes full replay length, router graph work, grid enumeration and diagnostic storage.
- [21 tests](../reports/phase_06/tests_03/result.json), 16 unchanged Phase05 scientific regression groups, 200 final replays and 616 reconstructed candidate evaluations pass. Both repaired QFT5 controls pass the original-circuit 32-column proof at maximum error 8.3271e-16.
- All 102 starting scientific files and four frozen benchmark studies are unchanged; operational pre-existing differences are retained in the prerequisite review. Final version: phase06-448360af615a5c8f in [version_manifest.json](../reports/phase_06/version_manifest.json).

## Results and small examples

Standard improves 12/20 evaluation runs and ties eight on each starting policy. Mean relative E change is -0.4919% after sum-distance and -0.7431% after expanded composite. Small improves 7/20 on each. No retained schedule worsens its baseline; additional compilation work is measurable. Across development/evaluation, 53 valid candidates that improve exact local E but worsen full E are rejected. [Accepted straggler](../runs/phase_06/audit_02/examples/straggler/evidence.json), [actual conflict/batch improvement](../runs/phase_06/audit_02/examples/conflict/evidence.json), [rejected rollback trap](../runs/phase_06/audit_02/examples/local_global_trap/evidence.json) retain complete before/after event evidence.

## Actual commands and next-phase smoke

These commands were executed in the existing Python3.13.2 venv. Their output paths are immutable; choose fresh suffixes when rerunning. The audit tool deliberately reads the recorded development_01/pilot_01 inputs and exports exact frozen evidence; existing report exports are also protected against overwrite.

```powershell
# Working directory: C:\Users\hp\Documents\BTP\btp_work
.\.venv\Scripts\python.exe -B -X utf8 tests/phase_06_acceptance.py --out reports/phase_06/tests_03
.\.venv\Scripts\python.exe -B -X utf8 tools/run_phase06_pilot.py --split development --out runs/phase_06/development_01
.\.venv\Scripts\python.exe -B -X utf8 tools/run_phase06_pilot.py --split evaluation --out runs/phase_06/pilot_01
.\.venv\Scripts\python.exe -B -X utf8 tools/finalize_phase06_evidence.py --out runs/phase_06/audit_02
.\.venv\Scripts\python.exe -B -X utf8 tools/check_phase06.py --out reports/phase_06/gate_01.json
```

For a small next-agent smoke, use phase06_worker.py with the existing request runs/phase_06/development_01/requests/qft5_ladder7__s42.json, --grid 11 --seed 42 and a fresh --out under btp_work. That exact worker interface is exercised in the recorded pilot attempt command and emits all eight matched control/budget rows. The handoff reports tested command arguments rather than inventing a new launcher.

## Limits and Phase07 entry

Phase07 should freeze the version manifest, both starting policies, repair operation caps and declared geometry/model before its final controlled study. Existing full matched Phase01/03/04/05 launchers and raw results are preserved. This task does not launch a new full paper-matrix repair campaign. Prior benchmark cases in the pilot are regression cases; only generator seeds400-403 are unseen by development. Model calibration, native plane separation, cooling-resource planning, full one-qubit physical timing, full benchmark acceptance and statistical generalization remain open. The second round is covered by an acceptance fixture; pilot budgets actually used at most one round. No global optimum, general speedup or native-device fidelity is claimed.
