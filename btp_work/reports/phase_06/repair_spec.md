# Phase 06 bounded repair specification

Owner: Codex /root, 29 October 2026. This implements proposal Step 4 over the accepted, orientation-corrected Phase05 pipeline. [Decision D009](../decisions/D009_PHASE06_FULL_REPLAY_REPAIR.md), [source review](source_research.md), [fixed protocol](../../configs/studies/phase06_pilot_v1.json).

## Boundary and complete objective

The proposal unit is one placement transition, its complete destination map and its actual routed batches. Initialization is fixed. A boundary is identified by logical layer and sorted active gate IDs. The unchanged prefix ends before the first transfer/movement in that placement batch. Its snapshot includes all atom/qubit positions and carrier identities, SLM traps, accumulated heating, time, weighted per-qubit exposure, completed/active/pending gate IDs and both the router global RNG and planner private RNG states. The basic no-cooling profile has an explicitly empty cooling-resource list. Prefix events and their order/times must match exactly. The same prior overrides are replayed before testing a new one.

Candidates may flip a complete pair orientation, move a complete pair to a Phase05 candidate slot, exchange two active pair slots with legal orientations, or change an idle parking destination. An active endpoint is never proposed alone. Overlapping active slots, illegal gate/restriction distances, out-of-grid sites, duplicate occupancy, missing or extra register atoms are rejected. Idle atoms displaced by a pair are reparked using the unchanged h=4 future-event potential. All moves, temporary cycle-breaking parking, transfers and later placement decisions are routed and scored.

Acceptance uses the Phase03 common full-circuit objective E = -ln(F_proxy), including its native gate, transfer, heating gate, movement loss, cooling gate and decoherence terms. It is a modelled independent-error proxy. There is no local-score or window-estimator acceptance mode. Finite candidates improve only when E_candidate < E_parent - 1e-12; ties retain the existing incumbent. Infinite candidates cannot improve finite incumbents. A finite candidate may improve an infinite valid incumbent. Equal feasible candidate scores retain the first deterministic proposal.

## Selection, replay and commit

Transitions rank by decreasing sum of actual routed movement durations, then decreasing direct conflict-edge count, then boundary order/key. Inside a transition, moving pair/idle decisions rank by decreasing time on actual slowest movement segments, conflict degree, decision type and qubit tuple. A graph edge is diagnostic; deleting an edge does not prove that a batch disappears.

The finite neighborhood is constructed in deterministic order. Legal proposals rank by optimistic single-batch local error, then direct conflicts and a target-map hash. This predictor omits actual serialization and future effects; it only determines trial order. Each evaluated proposal consumes one evaluation, including failed routes, invalid schedules and rejected scores.

A trial creates a private override map and a fresh isolated compiler module. The entire circuit is recompiled using the unchanged planner/router options and routing seed. This deliberately recomputes the prefix as well as the affected suffix; it is not an optimized snapshot resume. At each override the complete captured prefix-state hash must match. The suffix uses the random stream resulting from routing that trial; it is not artificially synchronized after different numbers of random draws. The caller RNG is restored on success and failure. The generated schedule passes the independent common validator/evaluator, with final heating, clock and exposure checked against the planner observer. Replayed prefix events are also checked exactly.

Every round compares candidates to the same immutable parent, retains its best feasible full-score candidate, then commits once. All trials preserve the parent until commit. A visited override-map hash avoids duplicate work. Subsequent rounds start at the last committed boundary or later; this avoids invalidating an existing later prefix override by changing an earlier transition. Strict full-error improvement, finite budgets and visited states guarantee termination. This restricted neighborhood has no global-optimality guarantee.

A supplied baseline is copied, checked against the complete recipe identity, rebuilt from its instructions and independently rescored; cached validity/score fields cannot authorize acceptance. Invalid/unsupported baselines return explicit baseline_failure. Candidate exceptions, missing boundaries, prefix mismatches and invalid/unsupported physics cannot replace the incumbent. Exhausted budgets return the last complete feasible incumbent. A cooperative stop returns it too. Checkpoint callbacks receive a private copy; callback failure reports checkpoint_failure_with_incumbent. The worker saves its baseline immediately and every accepted checkpoint before terminal summaries.

## Frozen budgets and costs

| Control | Rounds | Transitions/round | Decisions/transition | Trials/decision | Total evaluations |
| --- | ---: | ---: | ---: | ---: | ---: |
| disabled | 0 | 3 | 2 | 3 | 0 |
| zero | 0 | 3 | 2 | 3 | 0 |
| small | 1 | 2 | 2 | 2 | 4 |
| standard | 2 | 3 | 2 | 3 | 12 |

All controls cap each replay at 5,000 router calls, scan at most 8 recorded Phase05 slots, 4 other pairs and 16 nearest free parking alternatives per selected decision. Idle eviction and nearest-free selection still enumerate the finite device grid; the scan limit bounds proposals rather than grid enumeration. The core wall cap is null for reproducible operation counts. An optional wall safeguard is cooperative, checked between trials and before accepting an over-time candidate; it cannot interrupt a running router call. Isolated pilot workers add a 240-second process-family wall cap and a monitored 4-GiB memory safeguard. A killed worker is censored and keeps durable checkpoints; it is never represented as a successful returned repair.

Report baseline compilation/validation time, baseline copy/revalidation time, all candidate compilation and validation/scoring time, exact local-prefix diagnostics, generation, every rejected evaluation and complete repair wall time. The independent post-run reconstruction audit is a separate verification expense. Initial imports affect the first baseline in a worker; there is one timed quality run per routing seed and no compilation-speedup claim. Shared baselines are reused between budgets, with that baseline cost added to each row for comparison. Artifact writing/checkpoint overhead outside the algorithm timer is covered by process wall time, not silently called algorithm speed.

## Complexity and storage

Let N be register size, G device grid sites, P placement transitions, S emitted physical events, h fixed parking horizon, R/T/D/C the four round/neighborhood caps, B total evaluation cap, and H the raw alternatives per selected decision. H <= max(1 + 2*slot_scan_limit + 4*swap_pair_scan_limit, parking_site_scan_limit). The number of evaluated complete trials is Q <= min(B, R*T*D*C); invalid and failed trials also count.

Ranking scans all P transitions and constructs direct pairwise conflict diagnostics, costing O(P*N^2 + P log P) per round plus reading routed records. Candidate generation costs conservatively O(R*T*D*H*(N^2 + N*G*h)); legal evictions and free-site enumeration are included. Sorting raw candidates adds O(R*T*D*H log H). The pinned router rebuilds a graph with O(N^2) edges for remaining clear moves and selects a maximal independent set. With unique legal targets and a spare temporary site, each iteration completes at least one pending move or breaks a finite occupancy cycle. A conservative per-transition bound is O(N^3 + N*G), including temporary-site scans, with O(N^2 + G) working space. A full grid can return an explicit routing failure and be rejected.

Let A(P,N) be the unchanged Phase05 non-routing planning cost, V(S,N) common validation/scoring cost, and M the size of a complete compilation/bundle including diagnostic boundary snapshots. Trial work is O(A(P,N) + P*(N^3 + N*G) + V(S,N) + M). Exact local-prefix diagnostics add up to two common prefix evaluations per candidate plus one cached parent evaluation pair per distinct tested boundary; each is bounded by a complete replay validation cost. Total repair cost includes the baseline copy/revalidation, ranking/generation, and Q times that full replay/validation work. Bounded iterations therefore do not mean constant cost as circuit length grows. The 5,000-call cap bounds the number of router invocations, not the internal work of one invocation.

Only one trial plus its round winner and incumbent need be live, but accepted-history bundles are retained up to R times and detailed audit maps/prefix evidence up to Q times. Conservatively storage is O((R+1)*M + Q*R*N + Q*P) with serialized override plans and metadata; the diagnostic implementation is not claimed to be memory-minimal. Persisted baseline/accepted schedules, every trial plan and reconstruction evidence are charged in the raw storage report. Actual process-family peak memory includes imports and all eight control/budget rows.

## Scope and Phase07 entry

Safe default remains disabled; small and standard are fixed demonstration caps, not a tuned production winner. Phase05 sum-distance and expanded composite starting policies both remain explicit. This phase establishes a safe bounded heuristic and a small analytical pilot. Declared two-plane geometry, CZ-only timing scope, surrogate model calibration and absent cooling-resource planning remain limitations inherited from accepted Phases03-05. Enabled cooling profiles are rejected, not silently approximated. Full matched paper-matrix evaluation, calibrated device evidence and generalization belong to Phases07-08.
