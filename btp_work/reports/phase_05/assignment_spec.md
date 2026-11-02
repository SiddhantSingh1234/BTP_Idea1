# Phase 05 oriented bottleneck and composite assignment

Owner: Codex /root. Scope: proposal Step 3, using accepted Phase 3 physics and Phase 4 future-potential APIs. [Source research](source_research.md), [additional references](../../source_review/phase05_primary/README.md), [frozen pilot protocol](../../configs/studies/phase05_pilot_v1.json). The upstream compiler/router, common validator/evaluator, Phase 4 implementation and frozen benchmark studies are not edited.

## Object, legality and controls

A real row is one unresolved logical pair (a,b); a column is one safe two-site interaction slot (s0,s1). Each row-column edge has two explicit orientations. Slots must be in the grid, have distinct endpoints within interaction range, avoid already committed target sites, and obey cross-gate restriction distances from committed pairs. Candidate columns must themselves be mutually blockade-safe; an arbitrary unsafe column collection is rejected rather than incorrectly treated as a linear assignment.

Current occupancy does not make every destination forbidden: active qubits may move and idle atoms may be evicted by the unchanged router. Committed target occupancy is forbidden. Both endpoint directions and legal masks survive cost construction and materialization. Forbidden edges are positive infinity internally, never a large finite penalty; JSON audits store null plus a separate legal mask. There are no dummy rows/columns interpreted as physical placements.

Controls include the original legacy parking/compiler, Phase 4 h4 passthrough, orientation-corrected sum distance, bottleneck maximum endpoint distance, bottleneck one-batch transport time, composite sum and composite bottleneck. Candidate policies com, expanded (factor2), and all are independent of cost/solver objective. Additional no-conflict, no-future and displacement-estimator variants expose individual terms. All new controls use the same orientation correction. Legacy/passthrough preserve the original materialization issue intentionally for historical comparison.

The unchanged local keep-adjacent/one-qubit heuristics and source capacity serialization run first. Only unresolved fallback assignment changes. Original assignment future bias remains disabled. Phase04 parking h4/gamma .9 is held fixed for corrected/new comparisons; this is a declared control, not selection of a best horizon.

## Fixed oriented cost

For an orientation o, endpoint displacements are measured in micrometres. Their actual nonzero movements determine transfer population and the Phase03 single-batch duration. Unknown initial positions incur no physical movement; pure-distance controls retain the source's virtual grid-center scoring fallback for unplaced endpoints. This distinction is recorded rather than charging loading as in-circuit transport.

The normalized composite is:

```text
c = wd * sum(nonzero endpoint/optional predicted displaced distances_um) / 15
  + wc * (committed incompatibilities + internal-row incompatibilities) / 1
  + wt * (2 * moving population) / 4
  + wh * (predicted marginal heating-gate E + movement-loss E) / .01
  + wf * (future_potential(a,target_a) + future_potential(b,target_b)) / (2*h*15)
```

Frozen weights are wd=wc=wt=wh=1, wf=.25. Every coefficient and normalizer is in the assignment JSON, not a device constant inside the heuristic. These are transparent untuned design choices, not experimentally calibrated optima. Zero-weight terms contribute zero. The future normalization is declared explicitly, so a horizon change would be a distinct controlled experiment.

The heating component adapts the proposal's delta-n term into the common model's marginal heating-gate/loss error. Both endpoints are predicted together by Phase03 local_batch_cost using their current prefix states, the pair's next CZ and the full-register exposure population. The model also returns transfer and exposure terms for diagnostics. Those diagnostic terms are not secretly added a second time to the displayed composite. The time-only control uses the model's move duration plus load/unload stages.

The committed reference is an immutable snapshot of already accepted dynamic targets overlaid on current positions, converted into nonzero movements. Every row/orientation is scored against exactly this set. Internal conflicts between the two endpoints of the same row can also be evaluated before matching; they are recorded separately. Conflicts between different new rows are not in this separable matrix. A one-batch prediction is optimistic when its own endpoint moves conflict; its compatibility flag and actual routed outcome are saved.

After minimizing over the two orientations for an entry, retain the winning orientation index (0 wins an exact tie). The assignment is materialized from this stored orientation, without rechecking only the first endpoint's distance.

## Known state, future events and displaced atoms

The new observer reads only router instructions that have already been emitted. It applies Phase03 movement_time/heating_increment to each actual routed batch, including cycle-breaking motions, to maintain prefix vibrational state. It does not cool/reset atoms between solves. The full evaluator independently recomputes final state; the worker requires agreement within 1e-12.

FutureEventIndex and FuturePotential are imported unchanged from Phase04. Pending/active/completed gate identities are explicit. At each solve all gate IDs committed to that physical batch are excluded; a serialized suffix remains pending. Only current locations and already committed dynamic targets provide anchors. No final future placement map is read. The potential's raw score restores its common exponential scale before adding values across qubits, avoiding accidental mixing of independently rescaled scores.

By default the local cost predicts the assigned pair, not all downstream eviction choices. A separately enabled displacement estimator identifies idle occupants of this candidate's endpoints and parks them deterministically using the same Phase04 potential over vacancies known at the snapshot. It reserves current occupancy, committed targets and its own slot, and handles at most two displaced atoms per row. This is a costed conservative predictor, not access to eventual parking output; different new rows' estimates may interfere. If that estimator has no vacancy it marks the candidate forbidden for that option. Actual parking remains the unchanged callback/router, and all outcomes are independently checked.

## Matching and finite failure

For sum, a rectangular shortest-augmenting-path Hungarian implementation covers all m real rows using distinct columns. Increasing row/column iteration gives deterministic ties; no epsilon cost perturbation changes the objective.

For bottleneck_sum:
1. Sort distinct finite legal entry costs.
2. Binary search the least threshold whose legal-edge graph has a matching covering all real rows, using deterministic BFS augmenting paths.
3. Restrict the matrix to entries at or below that exact threshold.
4. Minimize the sum over those entries with rectangular Hungarian.

The exact objective is (maximum chosen entry, summed chosen entries). This is not the stronger full sorted-vector lexicographic bottleneck assignment. Composite thresholds optimize composite c, not routed makespan or physical error.

If full coverage fails, binary search a maximum feasible deterministic row prefix, rebuild that prefix with its correct active-gate set, and solve it. The remaining pairs are deferred to the source's next physical sub-batch. Already accepted dynamic pairs can execute alone. If no pair/dynamic group can progress, raise AssignmentInfeasible; empty layouts/insufficient register capacity fail before inherited undefined-variable paths. A rebuilt prefix that is still infeasible fails explicitly. Work terminates without unbounded expansion/retries.

## Actual routing and evaluation

Every resulting mapping is routed by the original generate_safe_shuttle_instructions function. Its conflict graph, independent-set selection and cycle handling are unchanged. Audits associate row predictions with actual full-placement routing batches. The latter also include committed moves, idle evictions and cycle breaks; row-local predicted sums and actual whole-placement durations are different quantities, and are labelled accordingly.

Traces pass the unchanged independent checker and Phase03 retimer/evaluator under the same declared two-plane analytical geometry as Phase04. Original missing native geometry is not retroactively established. Timing/scoring covers the normalized CZ skeleton; original one-qubit semantics require a separate explicit restoration check. Cooling and Phase06 repair are not enabled.

## Complexity and memory

Let N be register size, G normalized CZ count, m unresolved real rows, S0 compatible static slots before filtering, s selected columns, h future horizon, A committed nonzero moves and F grid-site count.

- Shared sparse event index: O(N+G) construction/storage. Pair queries cost O(m*(log degree+h)) under the scheduler's consumed-prefix invariant, with skipped-event term S for arbitrary external queries.
- CoM candidate ordering: O(S0 log S0), producing s=min(S0,m), min(S0,2m), or S0. Independent mutual-column safety checking costs O(s^2); masks/reference comparisons add O(ms*A).
- Ordinary cost construction: O(m*(log degree+h) + s^2 + ms*(N+A+h)). The N term is real: the common local predictor copies/exposes the full register for each orientation. It is not hidden inside a claimed O(ms) bound.
- With displacement prediction, vacancy construction and parking queries add up to O(ms*(F*h+N+log degree)); only two candidate occupants are estimated, not a new search tree.
- Working cost/potential storage: O(ms + m*h + N + A), excluding the shared index and retained diagnostic logs. Per-entry predictor state is compacted to affected atoms after calculation.
- BFS feasibility and rectangular Hungarian each cost O(m^2*s) time, with O(m+s) work arrays beyond the matrix. Bottleneck sort/search plus secondary sum costs O(ms log(ms) + m^2*s log(ms)). Prefix fallback adds O(m^2*s log m), at most one cost rebuild and one final solve. Square estimates alone do not cover expanded candidates.
- The unchanged router retains its own conflict-graph and iterative cycle costs. No assignment bound is advertised as a bound on the entire compiler.
- Verbose sidecars retain matrices, selected costs, prefix states, completed IDs and Phase04 parking audits. Over D_a assignment and D_p parking decisions, storage can include O(D_a*(ms+N+G) + D_p*(F+h+G)) plus actual route/batch logs. These are not linear-memory whole-wrapper claims. The pilot records actual Python index bytes, process-family peak working-set observations, artifact sizes and stage clocks.

Timing distinguishes candidate construction, cost prediction, threshold/matching, index setup, narrow planner time and whole wrapper setup. Two fixed-seed samples at seed42 are timing repeats; seed43 is a separate routing seed, not a timing-selected quality result. Small-pilot clocks under a shared host do not prove speedups against Phase1's different full timer.

## Verification and reproducibility

The independent factorial oracle enumerates every injection and endpoint orientation for m<=6, s<=8. Tests cover 800 randomized objective checks, six-row rectangular enumeration, Hall failures, too few slots, forbidden/infinite edges, ties, empty problems, committed conflicts, the unresolved new-new limitation, stored orientations, predictor/full-model agreement, source serialization and exact Phase04 passthrough. All frozen scientific sources and benchmark snapshot files are checked by hash.

The [protocol](../../configs/studies/phase05_pilot_v1.json) fixes four development matching-layer instances (seeds100-103) separately from the 11-case evaluation set (QFT5/10/15, Table-II smoke, eviction/serialization fixtures and seeds200-204). Matching-layer microbenchmarks are not mislabeled as complete QAOA/QV circuits. All 14 variants, two evaluation routing seeds, accepted/invalid/unsupported/error outcomes and timing repeats are retained. Gamma/weights are not tuned on evaluation outcomes; no best default is promoted from this pilot.
