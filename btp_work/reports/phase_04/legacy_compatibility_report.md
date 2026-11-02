# Phase 04 legacy compatibility and generalized h1 differences

NEW Phase 04 work, 28 October 2026. [Raw compatibility record](../../runs/phase_04/pilot_03/legacy_compatibility.json), [tests](tests_06/result.json), [source decision](../decisions/D006_PHASE04_EVENT_LOOKAHEAD.md).

All eight exact controls (four cases, routing seeds 42/43) reproduce unmodified pinned-source instruction text and final RNG-state hashes. Fixed-seed timing repeats retain identical instruction hashes. The existing Phase 00 forced-eviction fixture at seed 42 is reproduced exactly, not merely by counts or score. The wrapper delegates every legacy parking call to the original function and preserves candidate order, cutoffs, current-distance term, source anchors and fallback.

The frozen compiler file is not patched. An isolated loaded module has checked layer/batch hooks and a replaced parking callback. Source synthesis, layouts, local heuristics, slot candidates, assignment, orientation materialization and router remain original. Existing assignment future bias is disabled. The source's known orientation-cost mismatch is not silently repaired. JSON list-to-tuple normalization is an interface conversion applied to both direct and hooked controls.

Generalized h1 differs on four of eight case/seed schedules: QFT5 and the full-register Table-II smoke, for both seeds. It matches the old forced-eviction and serialized fixtures in this pilot. h1 is therefore a named heuristic variant, not an exact reproduction claim. Later horizons are compared with both legacy and generalized h1.

Why equality fails in general: the source picker can minimize current-to-site plus site-to-partner distance; it has finite cutoffs and only uses its current partial target map. The new policy minimizes weighted future distance using a frozen current/committed-active snapshot, excludes consumed and active gates, counts repeated events and has deterministic coordinate ties. Both initial idle placement and eviction use the parking callback, so changes can appear without a later eviction. The static layout and active assignment rules remain fixed.

A hand counterexample isolates the current-distance term. Current site (0,0), partner (0,6), vacancies [(0,1),(0,5)]: source costs tie at 6 and original order selects (0,1); pure future distance chooses (0,5). A positive single-event gamma factor does not change that pure-distance minimizer. It does not prove a complete manuscript schedule: future-position estimation and other conventions must also match.

[Full original-QFT5 checks](full_original_h1_01/comparison.json) for h1 and [h4](full_original_h4_01/comparison.json) both pass all 32 basis columns with maximum error 8.33e-16. They explicitly restore omitted one-qubit operations and undo the final transport permutation using the unchanged independent Phase 02 verifier. This proves the tested semantic realization, not native one-qubit timing or physical device fidelity.
