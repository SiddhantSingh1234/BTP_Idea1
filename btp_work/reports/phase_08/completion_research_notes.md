# Idea 1: interpretation of the completed non-scaling analyses

This note records scientific conclusions from the original matrices, the frozen factorial extension, and the 529-cell bounded campaign. The higher-cap QFT follow-up has a separate ledger and must finish before the final release is accepted. Formal report and presentation formatting is deferred by the user's instruction; these are reusable research notes.

## What has been established

The implemented pipeline has independently checked event semantics, orientation-corrected assignment, explicit physical accounting, and a conservative full-replay repair rule. It can improve its RFT starting point on selected inputs. The evidence does **not** support universal superiority over corrected DasAtom, a generally best lookahead horizon, or a free quality improvement. The strongest contribution is a validated integration and a controlled explanation of its benefits, limits and costs.

The old common-profile comparison improves summed total E by 1.504% over the RFT snapshot, winning 53 of 66 circuit/grid targets and losing 13. In the added N=10/12 QAOA/QV study, the frozen small-repair method wins 21 of 24 circuit/seed pairs versus the RFT snapshot, with an equal-generator mean relative E change of -2.819%. Corrected DasAtom nevertheless has lower E on all 24 new pairs, just as it does on all 20 earlier new-family pairs and 64 of 66 original targets. These denominators belong to separate studies; they are not independent populations and must not be pooled into a significance claim.

Sources: [old budget pairs](integrated_analysis_02/transport_budget.csv), [new workload pairs](completion_initial_02/new_workload_pairs.csv), [new workload statistics](completion_initial_02/new_workload_summary.csv), [earlier new-family analysis](new_primary_analysis_01/summary.json). The final release replaces the interim completion-analysis links with its final aggregate version.

## RQ1: physical accounting changes the comparison

The 132-row model study keeps compiler decisions fixed and changes timing/accounting. All 66 RFT and 66 DasAtom analytical fidelities decrease under the extended profile. Median extended/legacy makespan ratios are 3.094 for RFT and 2.570 for DasAtom; median fidelity-proxy ratios are 0.08358 and 0.72956. Explicit atom transfers, transport timing, heating/loss and effective all-time exposure all contribute. This is not an isolated estimate of heating alone.

On the old final-method comparison, native gate error is about 50.14% of summed original E and is unchanged by routing. A 1.504% total-E reduction corresponds to a 3.016% reduction in the remaining transport-sensitive error. Both denominators should be shown: suppressing the gate term makes routing gains look larger, while showing only total error can hide where the method acts. Neither is a fidelity-percentage-point improvement. E=-ln(F_proxy); an E reduction is a multiplicative change of the modelled proxy.

The physical model combines explicitly documented source parameters and adaptations. It omits physical one-qubit timing, assumes declared two-plane geometry and a serial reconstructed movement schedule, and has no device calibration. Small original-unitary checks restore omitted one-qubit operations for semantics; they do not validate those physical assumptions.

Evidence: [baseline/model report](../final_benchmark_analysis_01/report.md), [model specification](../phase_03/model_specification.md), [transport budgets](integrated_analysis_02/transport_budget.csv), [profile](../../configs/hardware/extended_no_cooling.json).

## RQ2: future information needs an opportunity to affect parking

Horizon effects depend on the workload and the aggregation rule. On 27 distinct circuits represented by 66 circuit/grid targets, h4 has an equal-circuit mean relative change of -1.300% but a summed-E change of +1.349%. Its descriptive circuit-cluster interval crosses zero. This reversal is a consequence of weighting, not two conflicting executions. h1 is favorable on this corpus; that does not authorize selecting it after evaluation as a predeclared optimum. h8 can be worse. Exact legacy remains a distinct control rather than a claim that generalized h1 reproduces upstream behavior.

In the small N=6/8 depth4 QV factorial cases, lookahead and every interaction involving lookahead are exactly zero: all ten baseline case/seed observations have zero parking and eviction calls. The larger/deeper inputs reveal the boundary of that explanation. QV10 depth8 still has zero parking; QV10 depth16 and QV12 depth8 have two calls, while QV12 depth16 has nine to eleven in the full method. The full-method improvement on those larger inputs combines assignment, lookahead and repair, so it cannot be attributed to lookahead alone without another factorial. That attribution is not needed for the present bounded claim.

Critical-remaining-depth weighting is implemented as a scoped parking-only extension, with a reverse-DAG gate-depth oracle. At matched gamma=.5 it changes none of 24 scores; at gamma=.9 it improves three pairs belonging to one QAOA circuit and ties the other 21. The equal-circuit mean is -0.06475%, and the descriptive interval reaches zero. At gamma=1 it has six wins, nine ties and nine losses. This does not justify a new tuned default or a claim that criticality reliably helps.

Evidence: [horizon uncertainty](integrated_analysis_02/clustered_comparisons.csv), [factorial contrasts](integrated_analysis_02/factorial_effects.csv), [weighting controls](completion_initial_02/weighting_summary.csv), [larger-input parking counts](completion_initial_02/parking_opportunities.csv), [independent weighting tests](../phase_09/clean_completion_weighting_tests_01/result.json).

## RQ3: candidate capacity, objective and physical prediction are different effects

The earlier full assignment study separates original/expanded candidates, orientation correction, sum/bottleneck objectives and optional predictors. Expanded composite can help relative to the starting implementation, but its same-expanded-candidate effect is small and its circuit-cluster interval crosses zero. The proxy includes committed-move and within-row conflicts; conflicts between newly assigned rows remain outside the separable matrix. A low predicted cost therefore does not guarantee fewer actual router batches or lower complete E.

The new expanded-candidate ablations close the missing term-isolation comparison: removing conflict wins eight, ties nine and loses seven of 24 pairs; removing future, heating or transfer changes neither the final instruction text nor E in any pair. These nulls are not caused by all three costs being absent. Of 243 selected reference edges, 192 have positive future, heating and transfer components. Removing future changes 153 of 183 aligned cost matrices nonuniformly; heating changes 150, transfer 48. The alternatives still select the same realized final instructions. This is evidence of local decision stability at these weights and on these trajectories, not a proof that the terms are globally unnecessary.

The heating component is especially small with the frozen normalizer: its largest selected normalized component is 0.0005933, compared with selected distance components up to 3.814 and conflict up to 6. Transfer removal is a uniform shift in 135 of 183 aligned matrices; shifts can leave a matching unchanged. These diagnostics explain why a physically motivated term may carry little observable decision power without requiring a post-hoc coefficient search.

Evidence: [earlier assignment study](../phase_04_05_detailed_analysis_01/report.md), [term pairs](completion_initial_02/assignment_term_pairs.csv), [saved-matrix mechanism audit](mechanism_audit_01/verification.json), [oriented objective specification](../phase_05/assignment_spec.md).

## RQ4: strict acceptance is valuable, but complete replay is expensive

Repair accepts only a valid prefix-preserving strict reduction of complete E. This protects its own prepared parent, not the original RFT baseline across other simultaneous changes, and does not prove a global optimum. The original independent audit reconstructs all 616 candidate trials and confirms 53 accepted strict improvements and 53 local-better/global-worse rollbacks. The new non-scaling study adds 96 recorded trials and 11 strict commits. Its final schedules are independently replayed, but the new audit does not claim to recompile every rejected trial again.

The preserved worked examples show why neither bottleneck distance nor graph edges suffice. In one accepted pair-slot exchange, the longest segment falls from 36.620 to 27.000 um, movement time falls from 1363.448 to 1260.832 us, routed batches remain four, and direct conflicts increase from eight to ten. Complete E still improves. A different candidate improves its exact local transition E by 0.00047897 while worsening complete E from 0.202943 to 0.205917, and is correctly rejected. These examples identify mechanisms rather than selecting only successful proxies.

On the old 66-target comparison, standard repair costs a median 11.86 times its matched disabled control under the same timer, and 45 of 66 standard-composite choices are observationally dominated by another recorded same-scope alternative. The observations use noisy single samples and do not prove dominance on every future execution. The safe default remains disabled; fixed small/standard budgets are research controls, not demonstrated production optima.

Evidence: [repair specification](../phase_06/repair_spec.md), [worked traces and rollbacks](../phase_06/pilot_results.md), [cost effectiveness](integrated_analysis_02/repair_cost_effectiveness.csv), [Pareto choices](integrated_analysis_02/pareto_choices.csv), [new final-schedule audit](../phase_07/completion_audit_02/verification.json).

## RQ5: hardware assumptions and scale bound the conclusion

The fixed-trace transfer/coherence sweep changes the old aggregate gain from approximately 0.373% to 2.694% across nine hypothetical settings, while corrected DasAtom remains better on 64 of 66 targets. These are model scenarios, not statistical device confidence intervals. Seven positive coherence crossing points are derived and one representative transformation is checked with the full evaluator.

The new profile-driven study separates planning from scoring by retiming the default decisions under exactly the same changed profile and geometry as each replanned schedule. All 96 heating/acceleration/coherence/transfer comparisons retain exactly the same decision sequence and E as this matched counterfactual. This is limited-range decision insensitivity on four selected circuits, not invariance of the physical score. Enlarging parking area while retaining the same six static slots changes all 24 plans: grid20 wins six and loses six; grid35 wins three and loses nine. Extra parking space does not ensure lower E.

Cooling is a separate resource-enabled transform on a deliberately hot synthetic route (initial n=3, acceleration=.05). Five of nine bank/threshold combinations exhaust finite prepared cold banks. Four validate, paying added gate, transfer, preparation, registration, exposure and carrier handoff costs. The no-cooling E is 46.585; the successful transforms produce E=0.329–1.261 and increase makespan from 413.132 us to 1704.732–3642.132 us. This demonstrates the resource/time tradeoff of that stress condition, not a general hardware gain or an optimized cooling planner.

The original QFT65–100 portfolio completes all 64 capped attempts but times out all 16 proposed-small executions at 150 seconds. The cap-only follow-up retains these censors and tests the same frozen scientific program under larger finite limits. Its final results must be read from the final scaling ledger; an exported baseline from a killed repair is not a completed proposed-method result.

The storage audit already explains a concrete scaling cost. QFT65,80,100 have 4256,6440,10050 normalized CZs and 1141,1640,2451 stored prefix boundaries. Completed and pending gate-ID lists together contain exactly P times CZ entries: 4.856 million, 10.562 million and 24.633 million respectively. Their baseline compilation JSON sizes are 258,488,926, 480,135,860 and 993,066,271 bytes. Sparse event-index O(N+CZ) storage therefore does not imply whole-wrapper linear storage. This is a measured property of the current diagnostic representation, not a lower bound for a redesigned compiler.

Evidence: [fixed-trace scenarios](integrated_analysis_02/sensitivity_summary.csv), [matched-profile counterfactual recipes](hardware_counterfactual_02/replay_recipes.json), [finite cooling outcomes](hardware_counterfactual_02/finite_cooling_cases.csv), [snapshot accounting](snapshot_accounting_01/verification.json).

## Statistical and interpretation rules

The old corpus has 27 distinct circuits and 66 circuit/grid targets. The factorial has eight inputs and five routing seeds; 128 additional executions are timing repeats and are not independent quality samples. The larger QAOA/QV study has eight case IDs but only four underlying generator identities: two graph seeds and two QV seeds, each reused across depth. Average paired seeds/depths within each generator before computing equal-generator means. Two generators per family cannot justify population-level confidence claims, even when descriptive bootstrap endpoints lie on one side of zero.

No heuristic default or hardware profile is selected from these results. Fixed profile/candidate comparisons, summed error and equal-circuit means answer different questions and remain labelled. Completed-only quality and time summaries exclude censored measurements explicitly while retaining every censored cell in coverage. Observed process-family wall time includes imports and artifact work; inner native and wrapper timers have different scopes and cannot establish cross-method algorithmic speedups. Source snapshots, licensing/provenance, original bad runs and all current limitations remain part of the research record.

## Novelty and final contribution wording

Use: “A validated experimental integration of explicit next-event parking, orientation-corrected composite/bottleneck assignment and bounded full-error replay repair for a pinned RFT compiler, with controlled comparisons and identified opportunity, prediction and scalability limits.” Avoid claiming invention of future-aware placement, bottleneck matching or search-based routing. Current primary literature and the pinned upstream future-biased switches establish those as prior ideas; see [related-work update](related_work_update.md).

The final research conclusion can be solid while mixed: limited RFT-relative improvements are real in the declared model, corrected DasAtom is consistently stronger on the added families, several cost components do not change decisions at the tested scales/weights, and replay/snapshot cost limits practicality. None of these findings requires inventing a positive result or leaving an unbounded optimization search open.
