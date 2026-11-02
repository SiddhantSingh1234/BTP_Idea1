# Phase 02 discrepancy ledger

Owner: Codex /root, 28 October 2026. No upstream fix or corrected control applied.
This extends [the Phase 00 ledger](../phase_00/discrepancy_ledger.md).

## Current resolution checkpoint

[D003](../decisions/D003_PHASE02_SEMANTICS_AND_CONTROL.md) supplies the diagnosis
and a separate tested correctness control for D20. The paper's load/move/unload
batch interpretation fails on the emitted occupied destination; the original
record remains invalid. The conservative corrected control passes within its
explicit testing model and is not substituted into native results.

D21's required full tiny-circuit demonstration is now implemented with an
explicit one-qubit restoration sidecar and independent physical-slot simulation.
Both original QFT5 circuits pass; missing-H and wrong-output-permutation
negatives fail as intended. This does not claim native logs suddenly contain
one-qubit gates or physical timing. [Fourteen acceptance groups pass](tests_05/result.json).
The earlier descriptions below remain the original discovery evidence.

## D20: DasAtom intermediate coordinates do not determine physical trap occupancy

Status: confirmed emitted-coordinate overlap; full physical interpretation
unresolved. Affected claims: executable movement, physical transfers/makespan,
and any full physical-validity comparison. Native legacy measurements remain
available as historical accounting, with their original validation status.

Concrete case: `fig4_qft__qft_10__g11__dasatom__standalone__native__r1`.
The [evidence audit](baseline_snapshot_02/attempts/fig4_qft__qft_10__g11__dasatom__standalone__native__r1/validation.json)
records coincident intermediate coordinates with unknown trap states. Its
original Phase 01 boundary replay labels the run invalid because it requires
injective coordinates after every batch. That original result is preserved.

The explicit [two-transfer-stage reconstruction](../../runs/phase_02/dasatom_qft10_two_stage_01/metadata.json)
fails [independent replay](dasatom_qft10_two_stage_check_01.json): at e000038,
a9 is stored at (2,0), already occupied by a0 in SLM under that policy. Other
intermediate duplicates also occur. This disproves that particular immediate
unload interpretation; it is not proof that a different, fully specified
retained-AOD policy would work. Such a policy would need explicit trap states,
shared-line coupling, resources and continuous clearance checks. None is
silently inserted into the native result.

The 123-output snapshot contains 46 source-invalid results, 73 source-ok
results and four unsupported full-register results. All 123 retain unsupported
physical coverage in the evidence-only checker. Logical operation/mapping and
legacy-score agreement do **not** clear the 46 invalid historical statuses.
Do not pool them with physically validated schedules. Phase 01 closure requires
diagnosis and separate reporting; a repair would need its own corrected control.

## D21: native output cannot prove full original-QASM unitary equivalence

Status: confirmed output-scope limitation. Native routing logs contain CZ
operations and omit original one-qubit gates. Exhaustive tiny CZ basis-phase
checks and explicit final permutations validate the normalized route-only
scope; they cannot prove the unitary of the original QFT/QTetris circuit.
Retain `full_original_circuit_checked=false`. An identity-preserving full-gate
trace/reinsertion contract and independent original-circuit checks remain work
for the Phase 02 semantic gate. No such check is claimed completed.

## Boundary convention

The pinned RFT predicate permits cross-gate distance equal to the restriction
radius. DasAtom manuscript Eq. 2 prints strict greater-than. D002 freezes the
snapshot-compatible at-least convention with tolerance for current checks.
This is an explicit profile choice, not resolved manuscript provenance.
