# Idea 1: final research analysis

The agreed bounded Idea1 research programme is complete. Every planned experiment has a terminal outcome, all accepted final schedules have passed independent replay, and the analyses are saved here with their limitations. Timeouts and finite-resource failures remain results. The formal report and presentation will be formatted later as the user requested; this is the final Markdown research source.

## What has been established

The implemented pipeline has independently checked event semantics, orientation-corrected assignment, explicit physical accounting, and a conservative full-replay repair rule. It can improve its RFT starting point on selected inputs. The evidence does **not** support universal superiority over corrected DasAtom, a generally best lookahead horizon, or a free quality improvement. The strongest contribution is a validated integration and a controlled explanation of its benefits, limits and costs.

The old common-profile comparison improves summed total E by 1.504% over the RFT snapshot, winning 53 of 66 circuit/grid targets and losing 13. In the added N=10/12 QAOA/QV study, the frozen small-repair method wins 21 of 24 circuit/seed pairs versus the RFT snapshot, with an equal-generator mean relative E change of -2.819%. Corrected DasAtom nevertheless has lower E on all 24 new pairs, just as it does on all 20 earlier new-family pairs and 64 of 66 original targets. These denominators belong to separate studies; they are not independent populations and must not be pooled into a significance claim.

Sources: [old budget pairs](../../reports/phase_08/integrated_analysis_02/transport_budget.csv), [new workload pairs](../../reports/phase_08/completion_final_01/new_workload_pairs.csv), [new workload statistics](../../reports/phase_08/completion_final_01/new_workload_summary.csv), [earlier new-family analysis](../../reports/phase_08/new_primary_analysis_01/summary.json). The final release replaces the interim completion-analysis links with its final aggregate version.

## RQ1: physical accounting changes the comparison

The 132-row model study keeps compiler decisions fixed and changes timing/accounting. All 66 RFT and 66 DasAtom analytical fidelities decrease under the extended profile. Median extended/legacy makespan ratios are 3.094 for RFT and 2.570 for DasAtom; median fidelity-proxy ratios are 0.08358 and 0.72956. Explicit atom transfers, transport timing, heating/loss and effective all-time exposure all contribute. This is not an isolated estimate of heating alone.

On the old final-method comparison, native gate error is about 50.14% of summed original E and is unchanged by routing. A 1.504% total-E reduction corresponds to a 3.016% reduction in the remaining transport-sensitive error. Both denominators should be shown: suppressing the gate term makes routing gains look larger, while showing only total error can hide where the method acts. Neither is a fidelity-percentage-point improvement. E=-ln(F_proxy); an E reduction is a multiplicative change of the modelled proxy.

The physical model combines explicitly documented source parameters and adaptations. It omits physical one-qubit timing, assumes declared two-plane geometry and a serial reconstructed movement schedule, and has no device calibration. Small original-unitary checks restore omitted one-qubit operations for semantics; they do not validate those physical assumptions.

Evidence: [baseline/model report](../../reports/final_benchmark_analysis_01/report.md), [model specification](../../reports/phase_03/model_specification.md), [transport budgets](../../reports/phase_08/integrated_analysis_02/transport_budget.csv), [profile](../../configs/hardware/extended_no_cooling.json).

## RQ2: future information needs an opportunity to affect parking

Horizon effects depend on the workload and the aggregation rule. On 27 distinct circuits represented by 66 circuit/grid targets, h4 has an equal-circuit mean relative change of -1.300% but a summed-E change of +1.349%. Its descriptive circuit-cluster interval crosses zero. This reversal is a consequence of weighting, not two conflicting executions. h1 is favorable on this corpus; that does not authorize selecting it after evaluation as a predeclared optimum. h8 can be worse. Exact legacy remains a distinct control rather than a claim that generalized h1 reproduces upstream behavior.

In the small N=6/8 depth4 QV factorial cases, lookahead and every interaction involving lookahead are exactly zero: all ten baseline case/seed observations have zero parking and eviction calls. The larger/deeper inputs reveal the boundary of that explanation. QV10 depth8 still has zero parking; QV10 depth16 and QV12 depth8 have two calls, while QV12 depth16 has nine to eleven in the full method. The full-method improvement on those larger inputs combines assignment, lookahead and repair, so it cannot be attributed to lookahead alone without another factorial. That attribution is not needed for the present bounded claim.

Critical-remaining-depth weighting is implemented as a scoped parking-only extension, with a reverse-DAG gate-depth oracle. At matched gamma=.5 it changes none of 24 scores; at gamma=.9 it improves three pairs belonging to one QAOA circuit and ties the other 21. The equal-circuit mean is -0.06475%, and the descriptive interval reaches zero. At gamma=1 it has six wins, nine ties and nine losses. This does not justify a new tuned default or a claim that criticality reliably helps.

Evidence: [horizon uncertainty](../../reports/phase_08/integrated_analysis_02/clustered_comparisons.csv), [factorial contrasts](../../reports/phase_08/integrated_analysis_02/factorial_effects.csv), [weighting controls](../../reports/phase_08/completion_final_01/weighting_summary.csv), [larger-input parking counts](../../reports/phase_08/completion_final_01/parking_opportunities.csv), [independent weighting tests](../../reports/phase_09/clean_completion_weighting_tests_01/result.json).

## RQ3: candidate capacity, objective and physical prediction are different effects

The earlier full assignment study separates original/expanded candidates, orientation correction, sum/bottleneck objectives and optional predictors. Expanded composite can help relative to the starting implementation, but its same-expanded-candidate effect is small and its circuit-cluster interval crosses zero. The proxy includes committed-move and within-row conflicts; conflicts between newly assigned rows remain outside the separable matrix. A low predicted cost therefore does not guarantee fewer actual router batches or lower complete E.

The new expanded-candidate ablations close the missing term-isolation comparison: removing conflict wins eight, ties nine and loses seven of 24 pairs; removing future, heating or transfer changes neither the final instruction text nor E in any pair. These nulls are not caused by all three costs being absent. Of 243 selected reference edges, 192 have positive future, heating and transfer components. Removing future changes 153 of 183 aligned cost matrices nonuniformly; heating changes 150, transfer 48. The alternatives still select the same realized final instructions. This is evidence of local decision stability at these weights and on these trajectories, not a proof that the terms are globally unnecessary.

The heating component is especially small with the frozen normalizer: its largest selected normalized component is 0.0005933, compared with selected distance components up to 3.814 and conflict up to 6. Transfer removal is a uniform shift in 135 of 183 aligned matrices; shifts can leave a matching unchanged. These diagnostics explain why a physically motivated term may carry little observable decision power without requiring a post-hoc coefficient search.

Evidence: [earlier assignment study](../../reports/phase_04_05_detailed_analysis_01/report.md), [term pairs](../../reports/phase_08/completion_final_01/assignment_term_pairs.csv), [saved-matrix mechanism audit](../../reports/phase_08/mechanism_audit_01/verification.json), [oriented objective specification](../../reports/phase_05/assignment_spec.md).

## RQ4: strict acceptance is valuable, but complete replay is expensive

Repair accepts only a valid prefix-preserving strict reduction of complete E. This protects its own prepared parent, not the original RFT baseline across other simultaneous changes, and does not prove a global optimum. The original independent audit reconstructs all 616 candidate trials and confirms 53 accepted strict improvements and 53 local-better/global-worse rollbacks. The new non-scaling study adds 96 recorded trials and 11 strict commits. Its final schedules are independently replayed, but the new audit does not claim to recompile every rejected trial again.

The preserved worked examples show why neither bottleneck distance nor graph edges suffice. In one accepted pair-slot exchange, the longest segment falls from 36.620 to 27.000 um, movement time falls from 1363.448 to 1260.832 us, routed batches remain four, and direct conflicts increase from eight to ten. Complete E still improves. A different candidate improves its exact local transition E by 0.00047897 while worsening complete E from 0.202943 to 0.205917, and is correctly rejected. These examples identify mechanisms rather than selecting only successful proxies.

On the old 66-target comparison, standard repair costs a median 11.86 times its matched disabled control under the same timer, and 45 of 66 standard-composite choices are observationally dominated by another recorded same-scope alternative. The observations use noisy single samples and do not prove dominance on every future execution. The safe default remains disabled; fixed small/standard budgets are research controls, not demonstrated production optima.

Evidence: [repair specification](../../reports/phase_06/repair_spec.md), [worked traces and rollbacks](../../reports/phase_06/pilot_results.md), [cost effectiveness](../../reports/phase_08/integrated_analysis_02/repair_cost_effectiveness.csv), [Pareto choices](../../reports/phase_08/integrated_analysis_02/pareto_choices.csv), [new final-schedule audit](../../reports/phase_07/completion_audit_02/verification.json).

## RQ5: hardware assumptions and scale bound the conclusion

The fixed-trace transfer/coherence sweep changes the old aggregate gain from approximately 0.373% to 2.694% across nine hypothetical settings, while corrected DasAtom remains better on 64 of 66 targets. These are model scenarios, not statistical device confidence intervals. Seven positive coherence crossing points are derived and one representative transformation is checked with the full evaluator.

The new profile-driven study separates planning from scoring by retiming the default decisions under exactly the same changed profile and geometry as each replanned schedule. All 96 heating/acceleration/coherence/transfer comparisons retain exactly the same decision sequence and E as this matched counterfactual. This is limited-range decision insensitivity on four selected circuits, not invariance of the physical score. Enlarging parking area while retaining the same six static slots changes all 24 plans: grid20 wins six and loses six; grid35 wins three and loses nine. Extra parking space does not ensure lower E.

Cooling is a separate resource-enabled transform on a deliberately hot synthetic route (initial n=3, acceleration=.05). Five of nine bank/threshold combinations exhaust finite prepared cold banks. Four validate, paying added gate, transfer, preparation, registration, exposure and carrier handoff costs. The no-cooling E is 46.585; the successful transforms produce E=0.329–1.261 and increase makespan from 413.132 us to 1704.732–3642.132 us. This demonstrates the resource/time tradeoff of that stress condition, not a general hardware gain or an optimized cooling planner.

The original QFT65–100 portfolio completes all 64 capped attempts but times out all 16 proposed-small executions at 150 seconds. The cap-only follow-up retains these censors and tests the same frozen scientific program under larger finite limits. Its final results must be read from the final scaling ledger; an exported baseline from a killed repair is not a completed proposed-method result.

The storage audit already explains a concrete scaling cost. QFT65,80,100 have 4256,6440,10050 normalized CZs and 1141,1640,2451 stored prefix boundaries. Completed and pending gate-ID lists together contain exactly P times CZ entries: 4.856 million, 10.562 million and 24.633 million respectively. Their baseline compilation JSON sizes are 258,488,926, 480,135,860 and 993,066,271 bytes. Sparse event-index O(N+CZ) storage therefore does not imply whole-wrapper linear storage. This is a measured property of the current diagnostic representation, not a lower bound for a redesigned compiler.

Evidence: [fixed-trace scenarios](../../reports/phase_08/integrated_analysis_02/sensitivity_summary.csv), [matched-profile counterfactual recipes](../../reports/phase_08/hardware_counterfactual_02/replay_recipes.json), [finite cooling outcomes](../../reports/phase_08/hardware_counterfactual_02/finite_cooling_cases.csv), [snapshot accounting](../../reports/phase_08/snapshot_accounting_01/verification.json).

## Statistical and interpretation rules

The old corpus has 27 distinct circuits and 66 circuit/grid targets. The factorial has eight inputs and five routing seeds; 128 additional executions are timing repeats and are not independent quality samples. The larger QAOA/QV study has eight case IDs but only four underlying generator identities: two graph seeds and two QV seeds, each reused across depth. Average paired seeds/depths within each generator before computing equal-generator means. Two generators per family cannot justify population-level confidence claims, even when descriptive bootstrap endpoints lie on one side of zero.

No heuristic default or hardware profile is selected from these results. Fixed profile/candidate comparisons, summed error and equal-circuit means answer different questions and remain labelled. Completed-only quality and time summaries exclude censored measurements explicitly while retaining every censored cell in coverage. Observed process-family wall time includes imports and artifact work; inner native and wrapper timers have different scopes and cannot establish cross-method algorithmic speedups. Source snapshots, licensing/provenance, original bad runs and all current limitations remain part of the research record.

## Novelty and final contribution wording

Use: “A validated experimental integration of explicit next-event parking, orientation-corrected composite/bottleneck assignment and bounded full-error replay repair for a pinned RFT compiler, with controlled comparisons and identified opportunity, prediction and scalability limits.” Avoid claiming invention of future-aware placement, bottleneck matching or search-based routing. Current primary literature and the pinned upstream future-biased switches establish those as prior ideas; see [related-work update](../../reports/phase_08/related_work_update.md).

The final research conclusion can be solid while mixed: limited RFT-relative improvements are real in the declared model, corrected DasAtom is consistently stronger on the added families, several cost components do not change decisions at the tested scales/weights, and replay/snapshot cost limits practicality. None of these findings requires inventing a positive result or leaving an unbounded optimization search open.


## Final QFT scaling outcomes

The initial 64-cell matrix and all 30 cap-only follow-up cells are terminal. The complete original timing ledger is preserved. Only time limits changed; scientific code, inputs, options, geometry and routing seeds remained frozen. Completed-only quality below uses matched successful pairs and says nothing about the unobserved quality of censored cases.

| scope | variant | planned | ok | timeout | out_of_memory | completed_median_wall_seconds | all_attempts_max_observed_peak_GiB | min_cap_seconds | max_cap_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| initial_caps | dasatom_corrected | 16 | 14 | 2 | 0 | 39.2941 | 0.3268 | 90.0000 | 90.0000 |
| initial_caps | proposed_small | 16 | 0 | 16 | 0 | None | 1.4702 | 150.0000 | 150.0000 |
| initial_caps | rft_corrected | 16 | 12 | 4 | 0 | 34.7341 | 1.2134 | 75.0000 | 75.0000 |
| initial_caps | rft_snapshot | 16 | 8 | 8 | 0 | 25.6758 | 0.5541 | 45.0000 | 45.0000 |
| after_cap_only_followup | dasatom_corrected | 16 | 16 | 0 | 0 | 42.0183 | 0.3552 | 90.0000 | 180.0000 |
| after_cap_only_followup | proposed_small | 16 | 10 | 6 | 0 | 328.7156 | 3.1930 | 360.0000 | 720.0000 |
| after_cap_only_followup | rft_corrected | 16 | 15 | 1 | 0 | 43.3787 | 1.3289 | 75.0000 | 180.0000 |
| after_cap_only_followup | rft_snapshot | 16 | 16 | 0 | 0 | 44.0878 | 1.0613 | 45.0000 | 180.0000 |

| comparison | paired_rows | better | tie | worse | equal_generator_mean_relative_E_percent |
| --- | --- | --- | --- | --- | --- |
| proposed_small_vs_dasatom_corrected | 10 | 0 | 0 | 10 | 73.3181 |
| proposed_small_vs_dasatom_corrected | 10 | 0 | 0 | 10 | 73.3181 |
| proposed_small_vs_rft_corrected | 10 | 8 | 0 | 2 | -4.7890 |
| proposed_small_vs_rft_corrected | 10 | 8 | 0 | 2 | -4.7890 |
| proposed_small_vs_rft_snapshot | 10 | 8 | 0 | 2 | -4.0161 |
| proposed_small_vs_rft_snapshot | 10 | 8 | 0 | 2 | -4.0161 |

The proposed-small implementation completes 10/16 large-QFT cells under the higher finite caps, times out on 6/16 and has 0 memory-guard stops. These are method-specific limits, not an equal-time contest. Full-replay safety does not imply practical scalability. The measured P×Q prefix representation and complete recompilation provide concrete cost mechanisms; they do not establish how a redesigned implementation would behave.

A monitor-level Windows atomic-log-write error is retained in the attempt history and retried with a bounded logging-only I/O shim. It is not an algorithm failure or an accepted timing/quality sample. No successful old result was rerun to improve its score.

Cumulative experiment-controller time is 4.633 hours within the original six-hour budget. Independent post-run audits and analysis are separate verification costs. [Full final tables](../../reports/phase_08/completion_final_01/analysis.md), [raw initial coverage](../../runs/remaining_experiments_6h_v2/results.csv), [raw follow-up coverage](../../runs/idea1_completion_followup_v1/results.csv), and [completion gate](completion_gate.json) bind this conclusion.
