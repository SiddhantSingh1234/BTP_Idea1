# D002: trace v1 and explicit validation coverage

Owner: Codex /root. Adopted implementation contract, 28 October 2026.
User authorization: prepare Phase 02 while the Phase 01 campaign runs. No
compiler, benchmark worker, source pin or heuristic is changed by this decision.

The common interface is `neutral_atom_trace.v1`, stored as metadata JSON plus
ordered JSONL events. Its [schema](../../configs/schemas/trace_v1.schema.json)
records logical gates, stable atom carriers, positions, trap state, timing,
resources, provenance, and distinct logical/placement/routing groups. Canonical
JSON hashes cover the CZ circuit and hardware profile; a byte hash covers the
LF-encoded event stream. Original worker inputs/results retain separate hashes.
The adapters record their own implementation hash and the compiler configuration.

Two policies are deliberately distinct:

- `evidence`: preserve observed coordinates and CZ choices; trap state,
  trajectories and physical timing remain unknown. No transfer event is
  manufactured from the legacy four-per-batch counter.
- `two_transfer_stages`: explicitly assume one concurrent SLM-to-AOD load,
  synchronized shared-linear-progress movement, and one AOD-to-SLM store for
  each nonzero movement batch. Zero-distance records do not transfer. Timing
  follows the supplied profile. These are derived events, not observed events,
  and this policy has **two stages**, unlike the historical four-stage alias.

The source-native profile preserves the frozen legacy geometry/constants, but
does not supply an invented physical minimum separation or cross-trap geometry.
The single-plane profile in the adversarial fixtures is an explicit testing
model, not a device calibration. Interaction distance is at most the radius;
cross-gate distances are at least the restriction radius, with tolerance 1e-9
in the relevant comparison units. The latter boundary matches the pinned RFT
predicate; DasAtom paper Eq. 2 prints a strict greater-than inequality. Do not
claim this contract resolves that paper/code boundary convention.

Validation returns violations plus checked/unsupported categories. A trace with
known violations is invalid. A trace with no known violations but missing
required physical evidence is unsupported. `fully_validated_within_model` never
implies measured device validity or full original-circuit unitary equivalence.
The original worker status is retained beside the independent checker status;
an unsupported result never clears an earlier invalid result for comparisons.

Coordinates that coincide while trap ownership is unknown are unresolved, with
event/atom/site evidence, rather than a claim that two known SLM atoms can share
a trap. Explicit SLM co-occupancy fails. This matters for [D20](../phase_02/discrepancy_ledger.md).

Logical validation covers the normalized CZ skeleton. Up to eight qubits it
also checks every basis-state phase with an explicit final physical output
permutation; larger circuits receive structural gate/dependency checks. Native
logs omit one-qubit operations, so full original-QASM unitary comparison remains
unsupported. Cooling/state handoff and multiple-AOD coupling are future
capabilities, not implemented physical models in this version.

The schema is parsed and its required event fields are exercised by acceptance
tests; the dedicated checker enforces supported replay invariants. A general
JSON Schema validation engine is not installed or claimed as tested. Future
incompatible event semantics need a new decision/version. Historical source
measurements remain immutable; no corrected control has been introduced.
