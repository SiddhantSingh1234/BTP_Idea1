# Phase 05 fixed routed pilot

[Protocol](../../configs/studies/phase05_pilot_v1.json), [CSV](pilot_results.csv), [JSON](pilot_results.json), [plot](pilot_results.png), [SVG](pilot_results.svg), [audit/replay](../../runs/phase_05/audit_01/audit.json).

All **308 evaluation schedules** (11 cases x 2 routing seeds x 14 variants) pass the common independent validator and Phase03 evaluator. The separate development split has 56/56 accepted schedules. There are 462 evaluation timing samples and 112 development samples; same-seed timing repeats are not independent quality trials. Evaluation wall time was 78.54s. No weights were changed after development/evaluation outcomes.

The set includes QFT5/10/15, the full-register Table-II smoke, eviction/serialization fixtures, four unseen matching-layer circuits and one explicitly labelled static-assignment adversary. These are 11 instances, not 22 independent circuits or the final paper matrix.

| Variant | Matched control | Better / tie / worse | Mean relative E change |
| --- | --- | ---: | ---: |
| composite_sum | sum_distance | 3 / 16 / 3 | +0.150% |
| bottleneck_distance | sum_distance | 4 / 4 / 14 | +4.545% |
| bottleneck_time | sum_distance | 4 / 4 / 14 | +4.545% |
| composite_bottleneck | sum_distance | 2 / 16 / 4 | +0.319% |
| composite_bottleneck_expanded | sum_distance_expanded | 10 / 8 / 4 | -1.815% |
| composite_bottleneck_all | sum_distance_all | 10 / 4 / 8 | -2.228% |
| composite_bottleneck_expanded | sum_distance | 6 / 8 / 8 | -1.050% |
| composite_bottleneck_expanded | phase04_reference | 11 / 2 / 9 | -2.234% |
| composite_bottleneck_expanded | original_legacy | 12 / 2 / 8 | -2.503% |
| sum_distance | phase04_reference | 11 / 2 / 9 | -1.395% |

Candidate expansion and objective effects must be separated. The expanded composite objective improves 10/22 and worsens 4/22 relative to expanded distance-sum, with about 1.8% lower mean relative E. Against the original CoM corrected distance-sum it is mixed (6 better, 8 tied, 8 worse). The all-slot diagnostic has a larger candidate budget and is not a selected production default. The CoM-only composite variants show no consistent aggregate gain. Bottleneck distance/time alone is worse in 14/22 comparisons.

Orientation repair is not counted as a novel-objective improvement. Both original legacy and Phase04 h4 controls remain separate; all corrected/new controls share the repair. QFT5 expanded-composite E=0.157730453169 versus corrected CoM E=0.164059155294; QFT15 is worse (1.861377837613 versus 1.812963783085). Both examples and every negative result remain in the CSV.

The replay independently rechecks 2496 actual frozen-matrix optima and 4405 applied orientations, and all 364 schedules replay with identical budgets. 824 actual placement batches have new-new move conflicts outside the frozen linear proxy. This confirms the proxy limitation; it is not an exact routing optimum.

The largest actual pilot matrix has 4 real rows and 6 candidate columns. Maximum observed worker-family peak working set was 209.54 MiB; this combines imports and all variants in a case worker, not per-variant memory. Raw artifacts occupy 314.29 MiB. Python index bytes and candidate/cost/matching clocks are in the raw records. Diagnostics are retained, so sparse-index space is not a whole-wrapper memory bound.

Timing includes two separate narrow planner/wrapper clocks and stage breakdown. It is not comparable directly with Phase01 full compilation and does not establish speedup. Every placement prediction file compares local row time with actual full-placement transport, which includes committed/eviction/cycle moves; these scopes differ explicitly.

No best k, weight setting or variant is selected from the evaluation set. These are analytical two-plane, no-cooling CZ-skeleton results, not calibrated-device fidelity or a completed final benchmark claim. The frozen Phase01/03/04 benchmark studies are unchanged.
