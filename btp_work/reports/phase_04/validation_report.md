# Phase 04 validation report

Owner Codex /root, 28 October 2026. Status: complete within the declared implementation/pilot scope; [final gate](gate_01.json) passes. [Specification](lookahead_spec.md), [sources](source_research.md), [decision D006](../decisions/D006_PHASE04_EVENT_LOOKAHEAD.md).

[Seventeen Phase 04 test groups pass](tests_06/result.json), with the [transcript](tests_06/unittest.txt). The independent scan compares 121,600 queries on all 1,000 three-layer four-qubit matching schedules. Additional cases cover repeated partners, empty layers, h0 rejection, oversized horizons, no future, missing anchors without refilling h, pending/active/consumed current-layer gates, serialization, immutable snapshots, forbidden future maps, ties, disabled critical weights, stable IDs, discount underflow, cursor transitions and sparse large-register storage.

The [unchanged Phase 03 suite](phase03_regression_01/result.json) passes all 16 groups. New h1/h4 QFT5 realizations pass [full original semantics](full_original_h1_01/comparison.json) and [h4 semantics](full_original_h4_01/comparison.json) at error 8.33e-16. [CLI legacy smoke](../../runs/phase_04/cli_legacy_01/result.json) and [h4 smoke](../../runs/phase_04/cli_h4_01/result.json) pass.

| Mandatory Phase 04 criterion | Evidence |
| --- | --- |
| Independent oracle, including repeated/consumed events | Exhaustive oracle group plus repeated/current-layer tests; normalized FIFO gate IDs |
| Exact legacy schedule under controlled randomness | Eight pilot controls match instructions and final RNG hashes; existing frozen eviction fixture matches byte-for-byte |
| Generalized h1 differences explicit | [Compatibility report](legacy_compatibility_report.md); four changed case/seed schedules and isolated hand example |
| Produced schedules validate/evaluate | All 40 accepted pilot schedules plus both counterexample traces pass common independent checking and Phase 03 evaluation under declared geometry |
| No unknown future chosen placement access | Snapshot-only potential API, forbidden-map negative test, committed-batch/decision sidecars |
| Actual costs and worst-case dimensions documented | Per-worker build/query clocks, separate tracemalloc/reachable-size diagnostics and complexity addendum in [specification](lookahead_spec.md) |

The first test run's sole failure detected an independently authorized Phase 01 controller guard. [Receipt and diff](concurrent_controller_change.json), D005. It was preserved, not reverted or silently ignored. Tests now require that exact audited exception while asserting all scientific-source/model/worker/plan hashes. Initial JSON pair arrays also required tuple normalization at the interface; this does not alter planner choices. [Development record](development_record.json). Earlier outputs remain intact.

Acceptance concerns implementation and the small pre-evaluation model scope. It does not establish physical calibration, end-to-end speedup, improvement over legacy, a full original-circuit timing model or completed Phase 01 coverage. Full verbose decision/candidate audits have a separate storage/time cost; sparse-index bounds do not imply a linear-memory full audit.


Final accepted implementation tests are tests06 (17 groups). They include an actual static-slot source-planner case where later physical sub-batches evict qubits whose current-layer gate already ran; every such query matches the independent scan. Tests05 exposed a stale gate site in the refined two-vacancy fixture; the independent validator rejected it, and the final fixture now derives sites from its actual anchors. Pilot03 replays all 40 cached compiler schedules identically and regenerates only the refined counterexample. Original timing records are not relabelled as new compilation.

## Fresh completion review

[Completion review](completion_review.md) reruns the 17 lookahead and 16 model groups, verifies all 29 gate checks, and independently replays the 40 saved schedules with identical budgets. The phase brief now records all six acceptance criteria as complete. No implementation change was needed.
