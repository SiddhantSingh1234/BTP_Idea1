# Bounded completion-study analysis

This analysis preserves the initial caps and all outcomes. Lower E is better. E is the negative log of an analytical success proxy on the normalized CZ skeleton, not measured device fidelity.

Status: ok. Original campaign: {'reused_quality': 24, 'ok': 470, 'unsupported': 5, 'timeout': 30}. Cap-only follow-up: {'ok': 23, 'timeout': 7}.

## Weighting and discount controls

Critical-depth weights are compared with uniform weights at the same gamma; discount controls use uniform gamma=.9. Means average routing seeds within generator/circuit first. Intervals describe this small selected corpus and are not confirmatory multi-comparison significance tests.

| comparison | paired_rows | generator_clusters | better | tie | worse | equal_generator_mean_relative_E_percent | cluster_bootstrap95_low | cluster_bootstrap95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| critical_vs_uniform_gamma0.5 | 24 | 8 | 0 | 24 | 0 | 0.0000 | 0.0000 | 0.0000 |
| critical_vs_uniform_gamma0.9 | 24 | 8 | 3 | 21 | 0 | -0.0648 | -0.1943 | 0.0000 |
| critical_vs_uniform_gamma1.0 | 24 | 8 | 6 | 9 | 9 | 0.1743 | -2.2329 | 2.7831 |
| uniform_gamma0.5_vs0.9 | 24 | 8 | 3 | 9 | 12 | 0.9232 | -0.9547 | 2.7948 |
| uniform_gamma1.0_vs0.9 | 24 | 8 | 9 | 6 | 9 | 0.1154 | -2.5128 | 2.5292 |

## Assignment terms

Each term is removed separately. A positive change means its removal worsened E; a negative change means removal helped. No winner is substituted into the frozen proposed method.

| comparison | paired_rows | better | tie | worse | equal_generator_mean_relative_E_percent | cluster_bootstrap95_low | cluster_bootstrap95_high |
| --- | --- | --- | --- | --- | --- | --- | --- |
| without_conflict | 24 | 8 | 9 | 7 | 0.2439 | -0.2494 | 0.8315 |
| without_future | 24 | 0 | 24 | 0 | 0.0000 | 0.0000 | 0.0000 |
| without_heating | 24 | 0 | 24 | 0 | 0.0000 | 0.0000 | 0.0000 |
| without_transfer | 24 | 0 | 24 | 0 | 0.0000 | 0.0000 | 0.0000 |

## Profile-driven replanning

The control decisions are retimed and rescored under exactly the same changed profile and geometry as the replanned result. Grid20/35 expands parking area with the same six static slots. Cooling is a separate finite-resource transform of a fixed synthetic route.

| comparison | paired_rows | decision_sequences_changed | better | tie | worse | equal_generator_mean_relative_E_percent |
| --- | --- | --- | --- | --- | --- | --- |
| acceleration_double | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| acceleration_half | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| coherence_long | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| coherence_short | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| heating_double | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| heating_half | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| parking_area_grid20 | 12 | 12 | 6 | 0 | 6 | 0.9321 |
| parking_area_grid35 | 12 | 12 | 3 | 0 | 9 | 3.8044 |
| transfer_higher | 12 | 0 | 0 | 12 | 0 | 0.0000 |
| transfer_lower | 12 | 0 | 0 | 12 | 0 | 0.0000 |

## Larger/deeper genuine QAOA and QV inputs

N=10/12; QAOA p=2/4 with graph seed900+N; QV depth8/16 with generator seed1000+N; routing seeds41–43. Depth variants share a generator and remain in one cluster. There are only two generator identities per family, four overall; intervals cannot support broad population claims.

| comparison | family | paired_rows | generator_clusters | better | tie | worse | equal_generator_mean_relative_E_percent | cluster_bootstrap95_low | cluster_bootstrap95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposed_small_vs_dasatom_corrected | all | 24 | 4 | 0 | 0 | 24 | 30.3818 | 18.6041 | 42.1595 |
| proposed_small_vs_dasatom_corrected | qaoa | 12 | 2 | 0 | 0 | 12 | 42.1595 | 36.1635 | 48.1556 |
| proposed_small_vs_dasatom_corrected | quantum_volume | 12 | 2 | 0 | 0 | 12 | 18.6041 | 18.5924 | 18.6159 |
| proposed_small_vs_rft_corrected | all | 24 | 4 | 18 | 3 | 3 | -2.3987 | -4.7965 | -0.4550 |
| proposed_small_vs_rft_corrected | qaoa | 12 | 2 | 12 | 0 | 0 | -1.8327 | -2.6334 | -1.0320 |
| proposed_small_vs_rft_corrected | quantum_volume | 12 | 2 | 6 | 3 | 3 | -2.9647 | -6.0514 | 0.1221 |
| proposed_small_vs_rft_snapshot | all | 24 | 4 | 21 | 0 | 3 | -2.8187 | -5.1744 | -0.1656 |
| proposed_small_vs_rft_snapshot | qaoa | 12 | 2 | 12 | 0 | 0 | -3.1162 | -3.9070 | -2.3255 |
| proposed_small_vs_rft_snapshot | quantum_volume | 12 | 2 | 9 | 0 | 3 | -2.5213 | -6.1240 | 1.0815 |
| rft_corrected_vs_rft_snapshot | all | 24 | 4 | 14 | 0 | 10 | -0.4367 | -2.0959 | 0.6873 |
| rft_corrected_vs_rft_snapshot | qaoa | 12 | 2 | 8 | 0 | 4 | -1.2879 | -2.9040 | 0.3283 |
| rft_corrected_vs_rft_snapshot | quantum_volume | 12 | 2 | 6 | 0 | 6 | 0.4144 | -0.1314 | 0.9603 |

## QFT65–100 scaling and censoring

Eight sizes, two paired routing seeds, four methods, fixed11×11 geometry. A timeout contributes no final quality or completed runtime. Partial baseline snapshots are not relabelled completed proposed runs. Follow-up selection includes every initial timeout, with unchanged scientific source and larger declared caps; original timing evidence is retained.

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

Cross-method process wall includes imports/validation/artifacts, whose scope and snapshot sizes differ. It is descriptive operational cost, not a fair isolated algorithm speedup. Method-specific inner timers are not divided into cross-method speedup ratios.

Quality below is conditional on both methods finishing; it is not a bound on censored cases.

| comparison | paired_rows | better | tie | worse | equal_generator_mean_relative_E_percent |
| --- | --- | --- | --- | --- | --- |
| proposed_small_vs_dasatom_corrected | 10 | 0 | 0 | 10 | 73.3181 |
| proposed_small_vs_dasatom_corrected | 10 | 0 | 0 | 10 | 73.3181 |
| proposed_small_vs_rft_corrected | 10 | 8 | 0 | 2 | -4.7890 |
| proposed_small_vs_rft_corrected | 10 | 8 | 0 | 2 | -4.7890 |
| proposed_small_vs_rft_snapshot | 10 | 8 | 0 | 2 | -4.0161 |
| proposed_small_vs_rft_snapshot | 10 | 8 | 0 | 2 | -4.0161 |

## Finite cooling resources

| banks | threshold | status | without_cooling_E | cooling_E | delta_E | cooling_episodes | without_cooling_makespan_us | cooling_makespan_us |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 12 | unsupported | 46.584964909012456 |  |  |  | 413.1320343559642 |  |
| 1 | 15 | unsupported | 46.584964909012456 |  |  |  | 413.1320343559642 |  |
| 1 | 25 | unsupported | 46.584964909012456 |  |  |  | 413.1320343559642 |  |
| 2 | 12 | unsupported | 46.584964909012456 |  |  |  | 413.1320343559642 |  |
| 2 | 15 | unsupported | 46.584964909012456 |  |  |  | 413.1320343559642 |  |
| 2 | 25 | ok | 46.584964909012456 | 1.2614185750217488 | -45.323546333990706 | 2 | 413.1320343559642 | 1704.7320343559647 |
| 8 | 12 | ok | 46.584964909012456 | 0.3289272883711592 | -46.256037620641294 | 5 | 413.1320343559642 | 3642.132034355962 |
| 8 | 15 | ok | 46.584964909012456 | 0.8626180041677581 | -45.7223469048447 | 3 | 413.1320343559642 | 2350.5320343559642 |
| 8 | 25 | ok | 46.584964909012456 | 1.2614185750217488 | -45.323546333990706 | 2 | 413.1320343559642 | 1704.7320343559647 |

All five unsupported outcomes exhaust prepared cold banks; no implicit refill is introduced. Successful cooling pays its added CZ/H, registration, preparation, transfer, carrier handoff and elapsed-time costs. This synthetic stress test is not evidence of general compiler or hardware advantage.

## Regeneration and evidence

All numeric tables are CSV beside this Markdown. Profile counterfactual recipes and hashes are in reports/phase_08/hardware_counterfactual_02. Independent schedule replay/provenance receipts are in reports/phase_07/completion_audit_02 and the follow-up audit. See runtime_stages.csv and snapshot_storage.csv for stage and storage evidence.

Figures are exported as SVG/PDF/PNG under figures/. Scientific assumptions and source-literature limits remain those documented in the Idea1 claims ledger.
