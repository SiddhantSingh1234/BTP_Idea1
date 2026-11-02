# D003: full-gate semantic sidecar and separate correctness control

Owner: Codex /root. 28 October 2026. Implementation decision within the Phase 02
validation scope. D001's frozen native benchmark and D002's trace semantics stay
unchanged. No proposed lookahead, assignment objective or score-driven repair is
implemented.

## Full original-circuit check

Native route logs omit one-qubit gates. A separate semantic sidecar now restores
them from the original circuit transpiled to the same CZ basis. Each restored
operation must satisfy the original per-qubit dependency queue. Native CZ order,
atom movements and mappings are retained. Positions define ordered occupied
physical slots; movement induces an explicit transport permutation, and the
final permutation is undone before comparison with logical output order.
Transport permutations are bookkeeping, not extra physical SWAP gates.

The reference is Qiskit Operator on the original QASM. The compiled realization
uses a separate NumPy basis-column simulator, including one-qubit matrices,
CZ phases, physical-slot permutations and precursor global phase. Exhaustive
checks are limited to eight qubits. Missing gates, wrong dependency order,
missing original register and unsupported operations are rejected; larger
circuits retain structural validation. Output flags identify the restoration
as a derived schedule transformation, never observed native one-qubit output.

Both actual QFT5 compilers pass all 32 basis columns:
[RFT](../phase_02/full_circuit_rft_qft5_02/comparison.json),
[DasAtom](../phase_02/full_circuit_dasatom_qft5_02/comparison.json).
Maximum absolute errors are 8.33e-16 and 8.90e-16 at tolerance 1e-9.
Negative tests remove H, corrupt the final permutation, and corrupt a CZ ID.
No original benchmark score is retroactively charged for restored operations.
Phase 03 must explicitly choose its computation-gate scope and timing.

This resolves D21's missing independent semantic demonstration under an explicit
restoration contract. Native logs alone still do not contain a full circuit or
establish its physical timing. That limitation remains labelled.

## D20 diagnosis and corrected control

DasAtom Section III, PDF p.6, describes loading a compatible movement set,
moving it, and unloading it. Its pinned router constructs a move-conflict graph
from pairwise AOD line compatibility; it does not enforce that a destination is
vacant after previously selected batches. The QFT10 occupied-destination
counterexample therefore fails the published immediate-unload interpretation.
Inventing retained AOD states would change the contract and would still require
a new line-coupling and resource proof. Original invalid results remain invalid.

`dasatom_corrected_vacancy_v1` is a separately labelled conservative schedule
control. It preserves every native embedding and gate group. It evacuates the
moving atoms of both endpoint embeddings to a common staging map using serial
orthogonal unit-grid steps through vacant sites, then reverses the target
evacuation. The common intermediate atom map makes the two paths compose.
Each BFS step avoids other occupied sites. The construction is deterministic
and finite when successful; lack of sufficient or accessible staging space is
an explicit unsupported result, not an incomplete accepted route. It is not a
complete grid-puzzle solver and makes no quality/optimality claim.

Its explicit testing profile assumes one plane, 3 um spacing and minimum
separation of one spacing. Those are declared control assumptions, not newly
recovered device measurements. Unit orthogonal segments keep stationary atoms
at least one spacing away; the independent analytic checker verifies this.
Each step has explicit assumed load/move/unload timing and no retained AOD atom.

The [QFT10 control](../../runs/phase_02/dasatom_corrected_vacancy_qft10_01/summary.json)
passes independent [validation](../../runs/phase_02/dasatom_corrected_vacancy_qft10_01/validation.json)
within this model: all 105 CZ operations and the final native mapping are
preserved; 527 serial unit steps total 1581 um. Its derived makespan is about
23975.55 us. These are new control results, not native measurements. The original
compile time is not a measurement of the transformation; its separately timed
transform took about .0158 s on this run, excluding validation/scoring.

The initial greedy development attempt failed to make finite progress and was
replaced before release; [the failure record](../phase_02/correction_development_failure_01.json)
is retained. Small-cycle, no-movement, full-grid rejection and the actual QFT10
control pass acceptance tests. No vendor file, live worker or source result
was edited. Extension comparisons must label native/corrected controls and
share the same correction and profile across compared variants.

## Dataset audit and remaining dependency

The auditor now covers every terminal attempt and repetition, including explicit
no-trace outcomes for capped runs. It keeps source status, independent evidence
status and the derived batch-policy status separate; it compares all available
legacy counters and scores with relative tolerances and records source hashes.
It runs below normal CPU priority and writes outside the live study. A lock
prevents duplicate auditors for an output root. Code changes require a new audit
version. `live_audit_v1` was deliberately stopped after 332 attempts; v2 freezes
the final code set including the separate corrected-control module.

The controller's terminal state plus attempted/explicitly omitted job accounting
triggers a final first-pass audit artifact automatically. This is not permission
to label ongoing Phase 01 or Phase 02 complete. Full research-phase closure
still requires the frozen Phase 01 dataset and review of its final audit.
