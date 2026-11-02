# Phase 04 lookahead specification

NEW Phase 04 work by Codex /root,28 October2026. Specified before implementation. Phase03's accepted analytical model is the dependency; Phase01 benchmarks continue. All new work stays in btp_work. No original compiler, worker, scorer, fixture or source paper is changed. [Starting record and frozen hashes](start_record.json).

## Research basis and variant boundary

Primary local readings: [proposal Idea1 Step2](../../../Proposal/BTP_Research_Proposal.pdf), [RFT SectionsIII-C/E and Eq6](../../../Papers/Priyanshu_Aditya_ISVLSI2026_AK_O.pdf), [Enola placement Eq2](../../../Papers/5_3658617.3697778.pdf), [ZAP next-reuse placement](../../../Papers/2_ZAP_Zoned_Architecture_and_Performant_Compiler_for_Field-Programmable_Atom_Array.pdf), [C1 source correction](../../source_review/SOURCE_REVIEW.md), and the pinned RFT build_right_filled_table/_pick_idle_position/generate_hardware_instructions implementation. Rendered original equations are retained under runs/phase_04/research.

Additional primary reference: Li,Ding,Xie, *Tackling the Qubit Mapping Problem for NISQ-Era Quantum Devices*, ASPLOS2019, [arXiv1809.02573v2 SectionIV-D](https://arxiv.org/html/1809.02573v2). Its bounded successor-set heuristic motivates keeping long-range predictions modest; its superconducting SWAP topology is not imported. General lookahead is prior work, not itself a novelty claim.

The manuscript's one-partner pure-distance description differs from the pinned implementation. The implementation records next occurrence per partner, includes a current-to-site term, has2/3-layer cutoffs and only uses already targeted partner positions. It does not consume its current-layer entry between physical sub-batches. Therefore generalized h1 equality is not assumed. Preserve all of that in a real legacy_exact branch and prove full schedule equality against unmodified source under identical randomness.

## Event semantics and API

Each future item is (gate_id,partner,logical_layer_delta). Stable gate IDs are assigned from the normalized CZ circuit using FIFO occurrence matching for repeated pairs, exactly as the trace adapter does. Each schedule layer is a matching; reject duplicate-qubit/duplicate-pair layers. Layer indices retain empty-layer gaps. Events with the same partner in later layers are distinct and consume separate horizon slots.

At a parking decision: already completed gates are excluded; the current committed active batch is excluded; still-pending current-layer gates remain eligible with delta0. A gate executed in an earlier physical batch of this logical layer is consumed. Gate IDs become completed only after that batch's execute record. Completed/active sets and their layer are audited. Invalid cursor/order transitions are rejected.

FutureEventIndex stores ordered per-qubit event lists and layer arrays, using O(N+G) storage/build work, where G is the CZ population. Binary search begins at the current layer and scans to h eligible records. General API bound is O(log(degree)+h+S), S skipped records; under the scheduler's valid prefix/current-layer invariant, at most one current event per qubit is skipped, so O(log(degree)+h). No new N*N*L or dense N*L*h structure is created. An independent oracle enumerates all gate occurrences for every tiny query.

h=0 is rejected. h beyond remaining events returns all remaining events. No-future returns empty. Unknown qubits/layers and invalid options are rejected. Initial critical-path weighting is disabled: all w=1. Unsupported weight modes are rejected, not silently implemented.

## Anchors, score and numerical conventions

Freeze a decision snapshot at batch commitment: current positions overlaid by committed active target positions. Later chosen placements are not available. Generalized parking ignores the planner's subsequently growing idle-placement map. Missing partner anchors are reported; they still count toward h and are not replaced by farther events. If no selected event has a known anchor, choose the vacancy nearest the supplied batch center of mass. Candidate sites remain exactly those supplied by the original planner. New-policy ties break lexicographically by site coordinate; legacy ties retain original candidate order.

For known anchors, minimize sum_j gamma**delta_j * distance_um(site,anchor_j), with equal weights,0<gamma<=1 and fixed pilot gamma=.9. No current-to-site term is retained in the generalized policy. Distances use the explicit source spacing. A common per-query rescaling gamma**min_delta avoids underflow without changing its minimizer; report this factor and both scaled/raw scores. Future Phase05 must restore the common scale before mixing scores across different qubits. This internal rescaling is not an undisclosed objective change.

Manual check: sites(0,0),(2,1), anchors(0,1),(4,1), deltas1,2, gamma1. h1 scores1,2 and chooses(0,0); h2 scores1+sqrt17 versus4 and chooses(2,1). A separate full-evaluator fixture keeps both later gates within interaction range even without extra parking; h2's extra move then worsens E. Larger h is not assumed monotonically better.

## Parking-only integration

Read the pinned core by SHA256, load an isolated module, and add only checked hooks for layer entry, batch commitment/completion and parking selection. The on-disk upstream stays unchanged. Legacy parking calls the ORIGINAL _pick_idle_position with untouched arguments. Generalized parking uses the event index/snapshot. Synthesis, local heuristics, static layout, candidate slots, Hungarian assignment/orientation materialization and router remain original. Existing assignment future bias is disabled for every controlled variant. The known orientation discrepancy is not silently fixed.

Instrumented legacy_exact must reproduce direct unmodified-source instruction bytes under identical global/private RNG states. Also compare the existing frozen Phase00 forced-eviction control where its full state is reproducible. Preserve original set order/tie behavior in legacy; Python hash seed is controlled for fresh workers. Instrumentation records query/build/potential cost separately; direct source control timing is also recorded, so framework overhead is not sold as compiler speedup.

## Fixed pilot and validity

No tuning: development consists of analytic/oracle fixtures. Evaluation uses frozen normalized QFT5, the full-register RFT Table-II smoke, and the existing small forced-eviction case, plus a deliberately serialized synthetic case. h=1/2/4/8 and legacy_exact share gamma=.9, equal weights, layout, options and router. Quality routing seeds42/43 are distinct from timing repeats at fixed seed42. Do not select best outcomes from timing repeats. Record input/layout/profile/core hashes, table construction/query time and measured table bytes/peak allocation, evictions, moved atoms, transfer counts, full E and exact unchanged-pair behavior.

Use the common trace adapter, independent checker and Phase03 cubic retimer/evaluator. Native geometry remains unsupported until explicitly declared; any testing-plane/separation assumptions are separate from device evidence and identical across compared variants. Invalid/unsupported schedules are retained as failed outcomes and excluded from accepted physical comparisons. No route correction is hidden inside lookahead. All accepted output schedules must pass the independent model validator and shared evaluator.

## Acceptance and handoff

Required evidence: independent event-oracle checks including repeated partners and consumed current-layer operations; exact legacy schedules; explicit generalized h1 differences; no future placement access; validated/evaluated accepted outputs; measured memory/time and honest worst-case dimensions. Deliver implementation/configs, pilot raw records/results, compatibility report, this specification, change ledger and handoffs/phase_04.md. Phase05 must reuse the future-potential API; no Phase05 assignment objective is enabled here.

<!-- BEGIN concurrent Phase01 update D005 -->
During Phase04, the user stopped Phase01 benchmark/auditor execution under D005. The original controller now has an approved operational stop guard; its pre-guard hash matches the Phase04 starting snapshot. [Recorded change](concurrent_controller_change.json). Phase04 does not edit or restart that controller. Phase01 research/dataset acceptance remains incomplete; only isolated short Phase04 fixtures/pilots run here. Initial running-campaign statements describe the earlier checkpoint.
<!-- END concurrent Phase01 update D005 -->


## Implemented measurements and actual whole-wrapper bounds

[Tests](tests_06/result.json), [pilot](pilot_results.md), [compatibility](legacy_compatibility_report.md), [validation](validation_report.md), [D006](../decisions/D006_PHASE04_EVENT_LOOKAHEAD.md). All 40 pilot attempts validate under the shared declared testing geometry. Generalized parking applies to initial idle placement as well as eviction; this is not a frozen-initial-placement ablation.

The sparse index has O(N+G) retained space and construction work. Each valid scheduler query is O(log degree+h), with the stated general skipped-record term S. Preparing anchors is O(h); choosing among F candidates costs O(F*h), with lexicographic tie selection and no candidate expansion. The original legacy RFT cost remains in legacy_exact. Original assignment/router costs are not reduced by this feature.

Verbose sidecars intentionally retain candidate scores, selected events and completed/active IDs. With D parking decisions, their additional worst-case storage can be O(D*(F+G+h)); snapshot/batch logs add their recorded populations. Sorting completed IDs also costs time. These diagnostic bounds are distinct from index space and cannot be advertised as linear whole-compiler memory. Pure FutureEventIndex/FuturePotential APIs do not require these sidecars; Phase 05 should reuse them directly. Reported planner and wrapper clocks include their declared instrumentation; the event-index setup clock is separate from planner-only time.

The adapter controls the process-global routing RNG and is intended for isolated workers, as used in the pilot. All workers are serial, one-thread and short; they do not share the Phase 01 controller workspace. Phase 01 reduced reruns remain user-controlled. The pilot demonstrated correctness, not an improvement over legacy; the accepted final baseline and a matched timing region are still needed for broad comparisons.


The public event-query layer index is zero-based in the supplied schedule list; it is distinct from the common trace circuit logical_layer field, which is one-based. Empty supplied layers preserve gaps; numeric layer-name strings are not parsed to invent omitted layers. Use layer_by_name when adapting compiler callbacks. h greater than remaining events returns the available suffix, and layer_count is a legal empty terminal query.
