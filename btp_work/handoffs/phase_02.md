<!-- BEGIN PHASE03 D004 acceptance update -->
# Accepted Phase 02 dependency,28 October2026

The user accepts Phase02 engineering complete and authorizes Phase03. [D004](../reports/decisions/D004_PHASE03_MODEL_AND_DEPENDENCY.md) assigns final frozen-dataset acceptance to the running Phase01 campaign. Older blocked_dependency/phase_complete:false statements below remain historical combined-gate evidence. No dataset completion or native physical-validity claim is added.
<!-- END PHASE03 D004 acceptance update -->

<!-- BEGIN PAPER_FOCUS_V2 BENCHMARK UPDATE -->
## Benchmark update: D005

The user stopped the old benchmark/auditor and adopted a paper-only execution
plan retaining all 132 targets. [D005](../reports/decisions/D005_STOP_REDUCE_REUSE_REPAIR.md)
and the current [Phase 01 handoff](phase_01.md) preserve the accepted Phase 02
engineering status and assign remaining dataset measurements/acceptance to
Phase 01. All 411 native records remain unchanged. Sixty-six RFT targets are
reused; all 57 available DasAtom layouts now have repaired discrete schedules,
including restored idle registers where needed. Nine missing traces remain
queued, with no background execution restarted. Physical minimum-clearance
evidence remains unsupported; no repaired discrete schedule is promoted to a
fully physical-validation claim. Separate Phase 03/04 work is preserved.
<!-- END PAPER_FOCUS_V2 BENCHMARK UPDATE -->

# Phase 02 handoff: engineering delivered, dataset acceptance pending

## Current checkpoint, 28 October 2026

Owner: Codex /root. **Status: blocked_dependency; not phase-complete.**
Implementation/test gaps from the earlier handoff are addressed. Remaining
dependency: the frozen, accepted Phase 01 dataset and final whole-dataset audit.
The live Phase 01 controller was never stopped or changed. No user input is
required. All earlier status statements below are historical where superseded.

User follow-up [D004](../reports/decisions/D004_REPAIR_FAILED_BASELINES.md) requires
repairing invalid baselines after the native campaign and rerunning corrected
measurements. Preserve original failures and use uniform fixes in a distinct
corrected baseline. The QFT10 control demonstrates one valid construction; it
does not replace the required corrected campaign or authorize clearing native
invalid labels. The follow-up specification is queued, not yet executed.

Read [D003](../reports/decisions/D003_PHASE02_SEMANTICS_AND_CONTROL.md) and the
current [validation report](../reports/phase_02/validation_report.md).
[Fourteen test groups pass](../reports/phase_02/tests_05/result.json), including
25 fixtures, both full original-QFT5 checks, deliberate one-qubit/permutation
corruptions, and corrected-control/full-grid rejection checks.

New implementation files:

- `implementation/validation/full_circuit.py`: restores omitted logical
  one-qubit operations from the full CZ-basis precursor, tracks occupied-slot
  transport permutations, and compares every tiny basis column using a separate
  NumPy simulator against Qiskit Operator on original input. A semantic sidecar,
  not a native log or native timing claim.
- `implementation/adapters/vacancy_control.py`: separately named conservative
  DasAtom correctness control; preserves embeddings/gate groups, changes only
  routing, rejects unavailable staging. QFT10's 105 CZ gates/final map and
  continuous clearance pass in an explicitly assumed single-plane model.
- `tools/follow_phase02_audit.py`: immutable audit of all attempts/repetitions,
  censored outcomes, native counters/scores and explicit batch-policy failures.
  Its v2 output freezes the final implementation set. A single OS-locked writer
  runs below normal CPU priority. It writes only to its own report directory.
- `tools/check_phase02.py`: evidence-aware gate; never accepts a live or
  incomplete Phase 01 dataset merely because engineering tests pass.

Actual additional tested commands (existing outputs are immutable; use new
suffixes for new runs):

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_02_acceptance.py --out btp_work/reports/phase_02/tests_05
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/verify_phase02_original.py --trace btp_work/runs/phase_02/rft_qft5_evidence_01 --original btp_work/benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm --out btp_work/reports/phase_02/full_circuit_rft_qft5_02
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/verify_phase02_original.py --trace btp_work/runs/phase_02/dasatom_qft5_evidence_01 --original btp_work/benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm --out btp_work/reports/phase_02/full_circuit_dasatom_qft5_02
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/create_phase02_corrected_control.py --run btp_work/runs/current_baseline/study_v1/attempts/fig4_qft__qft_10__g11__dasatom__standalone__native__r1/attempt_01/worker --out btp_work/runs/phase_02/dasatom_corrected_vacancy_qft10_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/follow_phase02_audit.py --study btp_work/runs/current_baseline/study_v1 --out btp_work/reports/phase_02/live_audit_v2 --follow --poll-seconds 20
```

The full-circuit errors are below 9e-16 at tolerance 1e-9. Corrected QFT10 uses
527 unit steps/1581 um and is deliberately conservative; its derived times and
scores are new control data, never native measurements. Original invalid and
unsupported statuses remain visible. No proposed research heuristic was added.

Live evidence: [audit status](../reports/phase_02/live_audit_v2/live_status.json)
and [audit CSV](../reports/phase_02/live_audit_v2/audit.csv). V1 was deliberately
stopped at 332 audited attempts after zero integrity mismatches; v2 starts fresh
to freeze the final code including the corrected control. Do not launch a second
auditor/controller with the same output root. After code changes, use a fresh
audit version; compatible restarts can resume by the same command.

Final acceptance still needs Phase 01 completion/freeze and review of the final
audit, including absent traces/censored attempts. The auditor writes a final
first-pass artifact automatically when the controller finishes and all jobs are
attempted or explicitly omitted. It does not itself claim phase completion.

The actual gate command was also executed:

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/check_phase02.py --out btp_work/reports/phase_02/engineering_gate_01.json
```

[Gate evidence](../reports/phase_02/engineering_gate_01.json): all eight
engineering checks pass, tested artifacts match, the native worker is unchanged,
342 attempts are audited without integrity mismatches, and `phase_complete` is
false because Phase 01/final dataset acceptance is still pending. Document/link
and original-PDF/excerpt integrity checks also pass (37 documents, 169 local
links, eight PDFs and six retained excerpt files at that checkpoint).

## Historical foundation checkpoint

The sections below record the earlier initial foundation. Their unresolved
implementation items are superseded by D003 and the current checkpoint above.

Owner: Codex /root. 28 October 2026. **Status: in_progress; not complete.**
User authorized independent work during the live Phase 01 campaign. No
applicable AGENTS.md was found in the workspace/ancestors or under btp_work.
All new files remain under btp_work; Papers/Proposal are unchanged and
Intern_Report was not used. No proposed heuristics were added.

## Interfaces and delivered scope

Read [D002](../reports/decisions/D002_TRACE_V1.md), the
[validation report](../reports/phase_02/validation_report.md),
[adapter assumptions](../reports/phase_02/adapter_assumptions.md),
[metric dictionary](../reports/phase_02/metric_dictionary.md), and
[discrepancy ledger](../reports/phase_02/discrepancy_ledger.md).

- `implementation/trace/model.py`: normalized CZ circuit/gate IDs and dependencies,
  hardware evidence profile, canonical hashes, immutable metadata/JSONL storage.
- `implementation/adapters/upstream.py`: strict RFT text/native DasAtom array
  adapters; observed coordinates and gate choices retained. No planner imports.
- `implementation/validation/checker.py`: independent replay, coverage and
  single-AOD geometry/resource checks; tiny exhaustive CZ basis-phase semantics.
- `implementation/metrics/legacy.py`: distinct atom/stage/distance accounting,
  exact historical inputs and log-space proxy; no extended noise model.
- `configs/schemas/trace_v1.schema.json`: versioned trace interface.
- `tools/trace_cli.py`: adapt/check/metrics. Existing output paths are rejected;
  outputs must stay inside btp_work.
- `tests/fixtures/trace_v1/`: 25 frozen valid/adversarial cases with input QASM,
  metadata, events and expected outcomes; generated once, do not overwrite.
- `tests/phase_02_acceptance.py`: ten meaningful test groups, all passing in tests_03.
- `tools/audit_phase02_snapshot.py`: read-only snapshot of completed attempt
  artifacts, with separate output root and original statuses retained.

Starting compiler pins remain RFT
`3d1f09233c2acd357fd9fbfad1b5300a921d301a` and DasAtom
`73a6bdf0fd200b2733745211eaf2e0c1e17f496a`. There is no claimed local Git
revision for these new files. Tests/audits retain implementation SHA-256 hashes.
The benchmark worker remains frozen; do not edit it or the live plan to add
validation. Do not launch a second controller or summary writer on the study.

## Actual tested commands

Run from `C:\Users\hp\Documents\BTP` with the existing Python 3.13.2 venv.
These exact output paths already exist; use a fresh suffix for a new attempt.

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/trace_cli.py adapt --run btp_work/runs/phase_00/smoke_rft_qft5_01 --algorithm rft --out btp_work/runs/phase_02/rft_qft5_evidence_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/trace_cli.py adapt --run btp_work/runs/phase_00/smoke_dasatom_qft5_01 --algorithm dasatom --out btp_work/runs/phase_02/dasatom_qft5_evidence_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/trace_cli.py check --trace btp_work/runs/phase_02/rft_qft5_evidence_01 --out btp_work/reports/phase_02/rft_qft5_check_01.json
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/trace_cli.py metrics --trace btp_work/runs/phase_02/rft_qft5_evidence_01 --out btp_work/reports/phase_02/rft_qft5_metrics_01.json
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_02_acceptance.py --out btp_work/reports/phase_02/tests_03
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/audit_phase02_snapshot.py --study btp_work/runs/current_baseline/study_v1 --out btp_work/reports/phase_02/baseline_snapshot_02 --limit 0
```

Both adapters and metrics succeeded. The checker deliberately reports
unsupported for source-native evidence, not physical success. Python CLI
codes are 0 for ok, 2 for invalid and 3 for unsupported; PowerShell wrappers may
surface a generic nonzero exit. Read the JSON status. Ten acceptance test groups
pass. The 123-output audit took 12.1 seconds; all legacy scores and available
saved replay final mappings match. No full-dataset audit is claimed.

## Minimal next smoke

Valid parallel movement: [fixture](../tests/fixtures/trace_v1/valid_parallel/metadata.json).
Valid cycle parking: [fixture](../tests/fixtures/trace_v1/valid_parking_cycle/metadata.json).
Deliberately invalid crossing: [fixture](../tests/fixtures/trace_v1/two_atom_midpath_collision/metadata.json).
Use `trace_cli.py check --trace <fixture directory> --out <new report path>`.
These fixtures were checked by the acceptance suite; do not equate their
synthetic hardware assumptions with physical evidence from native logs.

## Remaining mandatory work

1. Phase 01 dataset, longer retries/seed controls, plots and final analysis are
   still running/pending. Run the final Phase 02 audit after the dataset freezes;
   the present tool deliberately selects first repetitions, so extend final
   audit coverage explicitly before closure.
2. D20: reconcile DasAtom intermediate coordinate overlap with an executable
   transfer/trap policy. The immediate-unload policy fails. Keep original
   invalid records and do not infer that unknown trap ownership makes them valid.
3. D21: recover/define full-gate trace identity and independently compare tiny
   original/compiled circuits. Current semantics cover CZ skeletons only.
4. Apply demonstrated repairs only in a separately named corrected control,
   update the discrepancy ledger and all affected Phase 01 comparison gates.
5. Resolve remaining trace coverage under declared profiles; do not treat
   missing physical evidence as a passed physical check. Phase 03's realistic
   profiles/error model cannot rely on an unsupported native interpretation.

All mandatory phase criteria are accounted for in the validation report;
unresolved items remain open. Source-specific provenance and exact manuscript
revision remain unresolved as previously documented under D001.
