# Phase 02 validation report

## Current engineering checkpoint, 28 October 2026

Status: **blocked_dependency**. Implementation and independent test work is
delivered; full phase acceptance still awaits the frozen Phase 01 dataset and
final complete audit. No completed phase or exact-paper reproduction is claimed.

[Fourteen test groups pass](tests_05/result.json), including all 25 frozen
adversarial fixtures, independent geometry, counter/score reconstruction,
full original-QFT5 equivalence for both adapters, missing-one-qubit and wrong-
permutation negative checks, and a separately labelled corrected control.
The [full test transcript](tests_05/unittest.txt) records the actual run.

The complete original QFT5 comparisons use Qiskit Operator on original QASM
versus a separate NumPy physical-slot simulation of explicitly restored gates.
[RFT](full_circuit_rft_qft5_02/comparison.json) and
[DasAtom](full_circuit_dasatom_qft5_02/comparison.json) pass at errors below
9e-16. The gate-restoration sidecar is derived, not native one-qubit output;
no native score or physical timing was changed. See [D003](../decisions/D003_PHASE02_SEMANTICS_AND_CONTROL.md).

DasAtom's paper describes unloading each batch, while its pinned router omits
vacant-destination dependencies. The original QFT10 failure remains invalid
under this interpretation. A separate [corrected control](../../runs/phase_02/dasatom_corrected_vacancy_qft10_01/summary.json)
preserves its embeddings, all 105 CZ operations and final mapping, replacing
only transport with conservative serial staging paths. It passes analytic
continuous clearance, trap, transfer, resource and logical replay checks within
the declared single-plane/one-site-clearance model. It does not establish device
calibration, native route validity or improved performance. Dense/inaccessible
staging is explicitly unsupported; the full-grid rejection test passes.

The [v2 background auditor](live_audit_v2/live_status.json) covers every terminal
attempt and repetition, with separate outcomes for missing traces at resource
caps. It checks frozen input/worker hashes, final mappings, all available native
legacy counters and scores, observed evidence and explicit batch-policy replay.
It keeps invalid/unsupported results excluded from physical-validity claims.
It runs below normal priority and never writes to the benchmark study. V1 was
stopped at 332 audited attempts after zero accounting/mapping/contract errors;
v2 freezes the complete final implementation set. Old snapshots remain evidence.

| Acceptance item | Current result |
| --- | --- |
| Adapters preserve operations and mappings | Pass on tests and all available audited traces; final whole-dataset gate pending |
| Required valid/adversarial fixtures | Pass, 25 fixtures |
| Independent checker | Pass; no planner acceptance imports, hand geometry and distinct unitary engines |
| Atom-event/stage/time/distance definitions | Pass; original and derived quantities remain separate |
| Legacy score inputs | Pass on audited traces, including counters and strict relative score comparison; final dataset pending |
| Explicit physical coverage | Pass; no native missing-evidence path is labelled fully validated |
| Defect evidence and downstream marking | Pass for available traces, D20 diagnosis plus separate corrected control; original invalid statuses retained |
| Full tiny original-circuit semantics | Pass under explicit restoration contract; native omission remains labelled |

The only remaining acceptance dependency is the complete frozen Phase 01
dataset and its final audit/review. The follow auditor automatically writes
`first_pass_final_audit.json` after the controller finishes and every planned
job has an attempt or a recorded censored omission. That artifact alone does
not mark Phase 01 complete. Required slow retries/controls and its acceptance
still belong to Phase 01. No missing paper revision is presented as recovered.

## Historical foundation checkpoint

The following earlier checkpoint is retained for its initial scope and evidence;
the current section and D003 supersede its open D20/D21 implementation items.

Owner: Codex /root. 28 October 2026. Status: **in progress, not complete**.
Dependency handoffs: [00](../../handoffs/phase_00.md), [01](../../handoffs/phase_01.md).
Contract: [D002](../decisions/D002_TRACE_V1.md).

## Delivered and tested

Both native adapters, immutable trace storage, an independent replay checker
and metric evaluator are implemented under `implementation/`. The checker
imports no compiler predicates. It checks CZ identity/dependencies, stable
logical carriers, grid bounds, known-trap occupancy, gate geometry, AOD line
equality/order including retained carriers, explicit transfers, timed resources,
and analytic continuous separation for the supported single-AOD shared-progress
model. Unknown evidence is reported separately from known violations.

[Ten acceptance test groups pass](tests_03/result.json), with
[the actual unittest transcript](tests_03/unittest.txt). The tests exercise 25
frozen fixtures, independent hand-calculated closest-distance examples,
parallel-stage versus atom-event accounting, cycle parking and output
permutation, four real compiler smokes, legacy-score reconstruction, schema
fields, byte-checksum corruption, malformed data and stable log-space scoring.
The fixtures cover every named adversarial category in the phase brief. These
are tests of the declared model, not proof that native logs supply that model.

The [larger read-only audit](baseline_snapshot_02/summary.json) selected all 123
available first-repetition results with complete worker artifacts at its
240-record snapshot. It found zero adapter final-map mismatches and zero
legacy-score mismatches. Its [joined CSV](baseline_snapshot_02/audit.csv) retains
source statuses: 73 ok, 46 invalid and four unsupported declared registers.
Every evidence-only trace remains unsupported for full physical validation.
The original invalid outcomes are not overridden. The earlier 24-output audit
and earlier tests remain historical checkpoints with their own code hashes.

The native QFT5 metrics independently reconstruct RFT F=.8748227441484157 and
DasAtom F=.877796969531686. The assumed two-transfer-stage DasAtom QFT10 trace
fails occupancy replay; see [D20 and D21](discrepancy_ledger.md). No native
schedule, baseline worker or original source was changed to make tests pass.

## Acceptance status

| Mandatory criterion | Current evidence / remaining gap |
| --- | --- |
| Both adapters preserve operations/final mapping | Passed on four smokes and 123 completed outputs; final full-dataset audit pending |
| Adversarial fixtures fail correctly and valid fixtures pass | Passed for 25 frozen fixtures in tests_03 |
| Independent checker | Implemented without planner imports; hand geometry and independent CZ basis-phase checks tested |
| Atom-event versus stage definitions | Implemented and tested; unknown native transfers are explicitly incomplete |
| Reconstruct legacy score inputs | Matches all 123 audited results; pending remaining campaign results |
| Physical coverage explicit | Implemented; unsupported trajectories, trap/plane details and minimum separation prevent full validity claims |
| Affected frozen results marked / Phase 01 updated | D20/D21 ledger and Phase 01 handoff flag affected claims; corrections and final gate resolution pending |
| Original versus compiled full-circuit semantics | Tiny normalized CZ scope tested, including final permutation; original one-qubit operations absent from logs, full original-circuit verification remains unsupported |

## Limits and next work

Finish Phase 01 first-pass/retries, seed sensitivity, aggregation and final
target accounting, then run the audit on the complete frozen dataset, including
repetitions rather than only first-repetition snapshots. Diagnose the native
intermediate occupancy semantics without inventing observed transfers. Any
schedule change needs a separate corrected baseline. Resolve the full-gate
semantic contract before claiming original-circuit equivalence.

The checker is a foundation, not a complete device simulator. Nonlinear
independent-progress paths, multiple-AOD coupling, cooling and state handoff
are unsupported. Continuous proofs apply only when trajectory and geometry
are specified. The schema is frozen and parsed but no general JSON Schema
engine was installed. The CPU-only snapshot audit took about 12 seconds while
the campaign ran; benchmark timings are not claimed to come from an otherwise
idle host. No additional packages, source changes or heuristics were introduced.

For E events and N atoms, endpoint/path replay can take O(E N^2); timed resource
checks use an interval sweep with work proportional to overlapping intervals
(quadratic in the worst case). Tiny CZ semantics costs O(2^N G) only up to N=8;
larger circuits use structural checks. Evidence-only native traces do not
invent timed intervals merely to report a makespan.
