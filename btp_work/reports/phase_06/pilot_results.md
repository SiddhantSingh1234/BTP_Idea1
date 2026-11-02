# Phase 06 pilot results

All 40 development and 160 evaluation outputs validate in the declared analytical model. The independent audit reconstructed all 616 candidate evaluations, including rejected proposals, and replayed all 200 final outputs. It confirmed 53 accepted strict full-error improvements and 53 valid local/full-score traps rejected (15/38 accepted repairs and 9/44 traps in development/evaluation respectively). [Raw development](../../runs/phase_06/development_01/pilot_results.json), [raw evaluation](../../runs/phase_06/pilot_01/pilot_results.json), [complete independent audit](../../runs/phase_06/audit_02/audit.json), [CSV](pilot_results.csv), [candidate audit](repair_audit.csv), [plot](pilot_results.png).

## Fixed comparisons

Five development circuits use routing seed 42: known QFT5 plus matching generators 300-303. Ten evaluation circuits use routing seeds 42 and 43: prior Table-II/eviction/serialization/QFT10/QFT15 regression cases, previously unseen matching generators 400-403 and an analytic no-movement case. Prior benchmark cases are regression data, not newly held-out workloads. Random matching-layer fixtures are not QAOA or quantum volume. All comparisons hold the Phase05 assignment choice, h=4 parking, declared geometry, physical model and seed fixed while changing repair budget.

| Starting assignment | Budget | Better / tied / worse | Mean relative E change | Median repair seconds | Maximum repair seconds |
| --- | --- | --- | ---: | ---: | ---: |
| sum_distance | small | 7 / 13 / 0 | -0.1278% | 0.2459 | 2.3278 |
| sum_distance | standard | 12 / 8 / 0 | -0.4919% | 0.6978 | 5.5811 |
| composite_bottleneck_expanded | small | 7 / 13 / 0 | -0.4053% | 0.2516 | 2.0821 |
| composite_bottleneck_expanded | standard | 12 / 8 / 0 | -0.7431% | 0.6973 | 6.6733 |

Each row compares 20 case/seed pairs with its own disabled baseline. Disabled and zero-budget outputs are exactly identical to the corresponding pre-repair schedules in all 50 baseline case/seed/policy combinations. They perform no candidate evaluation, although copying and verifying a supplied baseline still costs time. The common full E is an analytical error proxy, not measured device fidelity.

Standard reduces mean E by 0.4919% after corrected sum-distance and 0.7431% after expanded composite. Maximum reductions are 1.6123% and 1.8013%. Small improves 7/20 and standard improves 12/20 for each policy; neither worsens its own baseline because only full-error improvements commit. Standard beats small in 11 sum-distance and 10 composite comparisons, tying the rest here. The different neighborhood order means increasing budgets is not a theorem of dominance between configurations.

The Table-II, forced-eviction, serialized and no-movement cases tie for both seeds at the standard budget. These failures to find a better candidate are retained. Most standard trials spend the evaluation cap in their first round; actual pilot rounds are 0 or 1 despite a maximum of 2. A separate acceptance fixture exercises second-round continuation. The limits were fixed before evaluation and no production winner is selected from these outcomes; safe default remains disabled.

## Worked accepted and rejected proposals

[Straggler evidence](../../runs/phase_06/audit_02/examples/straggler/evidence.json): development matching seed300, expanded composite, standard r1_c8. A joint pair-slot exchange shortens the largest actual segment from 36.6197 to 27.0000 um and routed movement time from 1363.4479 to 1260.8318 us. The route still has four batches and its direct conflict count increases from 8 to 10. Complete E nevertheless improves from 0.199589360313 to 0.199440217757 after downstream replay. This demonstrates why segment, graph and full-error axes must remain separate.

[Conflict evidence](../../runs/phase_06/audit_02/examples/conflict/evidence.json): development matching seed302, expanded composite, small r1_c1. A legal pair exchange reduces direct conflicts from 10 to 9 and actual routed batches from 5 to 4; movement time falls from 1821.9883 to 1446.9485 us. Final E changes from 0.207101099777 to 0.207077708120. The modest final gain, despite a larger immediate improvement, includes downstream costs.

[Rollback evidence](../../runs/phase_06/audit_02/examples/local_global_trap/evidence.json): development matching seed300, sum-distance, small r1_c1. Exact local transition E improves by 0.000478974855, while complete E worsens from 0.202942755152 to 0.205917226732. The candidate is valid and prefix-preserving but rejected; the entire parent and caller RNG remain unchanged. Each example retains full before/after schedules and an indexed event diff.

## Runtime, resources and interpretation

All rejected trials, full prefix/suffix recompilation, validation, scoring, local diagnostic scoring, baseline copy/revalidation, generation and incumbent handling are included in complete repair time. The evaluation performs 456 candidate trials; development performs 160. There is one quality/timing execution per seed, with no independent repeated-time confidence estimate and no speedup claim. The first worker baseline includes cold imports. Raw process wall time also includes writing artifacts/checkpoints outside the repair timer. The independent reconstruction audit took 81.98 seconds, reported separately from algorithm timing.

Maximum observed process-family peak is 465.89 MiB and raw pilot storage is 147.07 MiB. The peak includes imports and the whole worker control set; it is an observed sum of family peak working sets, not a hard allocation bound. Worker wall cap is 240 seconds and monitored memory safeguard is 4 GiB. No pilot output timed out, failed validation or became unavailable.

The result is a safe conditional improvement on this small pilot, with measurable additional compilation work. A guaranteed non-worsening retained incumbent is a property of acceptance, not evidence that all workloads benefit. Two routing seeds are not independent workload families. Full matched benchmark results, calibration, cooling-enabled planning, original one-qubit physical timing and generalization remain for Phases07-08. [Specification and complete complexity](repair_spec.md), [validation](validation_report.md), [handoff](../../handoffs/phase_06.md).
