# Phase 05 validation report

Status: complete within the implementation/pilot scope; [final gate](gate_01.json) passes all32 checks. Owner Codex /root, 29 October 2026.

All [17 acceptance groups](tests_03/result.json) pass; [transcript](tests_03/unittest.txt). The independent factorial oracle checks 800 randomized sum/bottleneck objective cases and a six-row seven-column case over all injections/orientations. It covers negative finite costs, Hall failure, true forbidden/infinite edges, too few columns, ties, empty problems and a hand case where minimum sum has the worse maximum.

The source orientation counterexample uses current sites (0,0)/(0,1), slot (1,1)/(2,1): the first-endpoint rule materializes 2+sqrt2, while the scored orientation is 1+sqrt5 (grid distance). The new control chooses/materializes the latter. All objective variants share this correction. It is not attributed to bottleneck gains.

| Mandatory criterion | Evidence |
| --- | --- |
| Tiny exact frozen-matrix optima agree | 800 randomized objective checks, six-row rectangular orientation enumeration, plus independent enumeration of all 2,496 actual pilot matrices |
| Applied orientations equal scored orientations | Adversarial manual example and all 4,405 selected oriented placements checked against the actual emitted batch targets |
| Infeasible instances terminate | Hall/insufficient-column tests, source serialization fixtures and explicit zero-slot/register-capacity failure; no fake dummy placements |
| Candidate and objective effects independent | 13 assignment configs, 14 named pilot variants; CoM/expanded/all controls and matched-policy comparisons |
| Actual schedules validate/evaluate | 56 development + 308 evaluation schedules accepted and replayed with identical budgets; separate row-proxy/actual full-placement records |
| Rectangular costs/complexity documented | [Specification](assignment_spec.md), measured candidate/cost/matching clocks, actual 4x6 maximum pilot matrix and observed 209.54MiB whole-worker family peak |

The [audit](../../runs/phase_05/audit_01/audit.json) independently checks 364 current-model replays, raw worker artifact hashes, 2,496 frozen-matrix optima and 4,405 applied orientations. It observes 824 placement batches with new-new conflicts omitted by the separable matrix, documenting the limitation rather than claiming exact routing optimization. Historical Phase04 controls reproduce 16 case/seed/parking instruction hashes.

The new [corrected control](full_original_corrected_01/comparison.json) and [expanded composite](full_original_composite_01/comparison.json) both pass all 32 full-original-QFT5 basis columns at maximum error 8.33e-16, with explicit one-qubit restoration and final permutation handling by the unchanged independent verifier. That sidecar proves semantics, not original one-qubit timing/device fidelity.

The Phase04 foundation suite passed all 17 groups [before edits](phase04_regression_start_01/result.json). Starting hashes and final tests verify the original compiler, Phase03/04 implementation, validator/evaluator, benchmark tools and frozen study files remain unchanged. No baseline controller was stopped, resumed or edited.

Tests01 exposed the inherited no-slot uninitialized center path; the new entrypoint now rejects that case explicitly. Tests02 passed 15 groups; tests03 add direct cross-qubit raw-discount/repeated-event and displaced-atom transfer checks. Earlier failed/development artifacts are preserved. Production code and frozen pilot settings were not changed after the routed outcomes.

Results are conditional: expanded composite versus expanded corrected distance-sum is 10 wins/8 ties/4 losses, mean relative E -1.815%; bottleneck distance/time alone is worse in 14/22. The common-CoM comparisons remain mixed. No best variant, calibrated gain, compilation speedup or full final-study acceptance is claimed.
