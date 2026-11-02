# Phase 03 fixed error-budget pilot

NEW Phase03 results,28 October2026. [Canonical manifest](../../runs/phase_03/pilot_03/pilot_manifest.json), [CSV](error_budget_pilot.csv), [JSON/hashes](error_budget_pilot.json), [raw schedules/results](../../runs/phase_03/pilot_03/raw), [SVG](error_budget_pilot.svg), [PNG](error_budget_pilot.png). Report exports are byte-identical to canonical pilot03 exports.

56 saved evaluations:12 ok,41 unsupported,3 invalid. Runtime8.33s includes adaptation, validation, serialization and plots, not compilation. Peak RAM was not measured. Inputs: saved RFT/DasAtom QFT5 and Table-II smoke pairs, D003's separate corrected DasAtom QFT10, and a synthetic two-atom stress route. Source two-transfer-stage timing is a declared reconstruction, not native observation. Complete profiles/source/code hashes accompany the results. Invalid/unsupported outcomes remain in the CSV.

Scoring axes distinguish historical accounting, frozen_ideal versus transfer_only on IDENTICAL events/exposure, explicit linear-heating surrogate rescoring, cubic retiming, extra-resource cooling, and triangular timing with surrogate heating. Historical versus extended default also changes timing/exposure conventions; that comparison is not an isolated transfer-error ablation.

| Fixed diagnostic | Historical source E | Cubic extended E | Scope |
| --- | ---: | ---: | --- |
| Native RFT QFT5 | .133733991262 | .160503219162 | Conditional normalized-CZ proxy; physical coverage unsupported |
| Native DasAtom QFT5 | .130339954079 | .130343420745 | No movement in this saved tiny case; physical coverage unsupported |
| Corrected DasAtom QFT10 | .826673194502 |2.210048934041 | Valid within D003's assumed geometry; corrected routing, not native output |

[Conditional rankings](../../runs/phase_03/pilot_03/rankings.json) retain DasAtom before RFT on this QFT5 pilot under every defined variant. No reversal is claimed. Invalid heating-surrogate factors are not ranked. These native comparisons are not accepted physical rankings. The native Table-II DasAtom case drops the original declared register, preventing a matched full-register comparison.

## Same stress route, different hardware

This is a fixed synthetic demonstration, not a compiler benchmark. Both variants preserve five parallel15um movement batches and five original CZs. Explicit stress assumptions: acceleration .05um/us^2, initial n3,80kHz source-like heating; no device fitting.

| Term/metric | No cooling | Explicit registered-bank hardware |
| --- | ---: | ---: |
| E_native_gate | .025062709118 | .025062709118 |
| E_transfer | .020010006672 | .032016010675 |
| E_heating_gate | .245985114988 | .185814896592 |
| E_movement_loss |46.293356235522 | .554519766384 |
| E_cooling_gate |0 | .062070578687 |
| E_decoherence | .000550842712 | .003134042712 |
| Total E |46.584964909012 | .862618004168 |
| Success proxy |5.8669e-21 | .422055691123 |
| Makespan(us) |413.132034356 |2350.532034356 |
| Cooling episodes/atom-events |0/0 |3/6 |

Cooling consumes three of four banks,12CZ+24H,12 additional physical transfers and1937.4us extra elapsed time. The8x8 model declares256 initial spare atoms. Lower predicted loss uses additional hardware/time; it is not an RFT algorithmic or measured device gain. [Intermediate atom states and time derivation](worked_budget.md).

## Sensitivity and retained failures

Predeclared sweeps cover40/80kHz, heating multipliers.5/1/2, accelerations .0005/.002 and nominal2.75 source-bound stress, transfer fidelities1/.9932, effective coherence15s, and cooling thresholds12/25. Resolved profiles are saved. No heuristic weights or threshold optimum are tuned from this pilot.

Fast source-bound stress leaves the asymptotic heating regime and can produce invalid gate survival. Blindly applying cubic heating to fast legacy linear timing also fails on some routes. Threshold12 exhausts the four-bank budget: unsupported, with no partial schedule accepted. Threshold25 uses fewer banks while accepting more movement risk.

[Prediction versus replay](../../runs/phase_03/pilot_03/prediction_vs_replay.json) agrees for one batch/one next gate to3.5e-18E. Omitting another CZ misses5.9521e-6E. Later optimization must use full replay to accept changes.

Development evidence remains: pilot01 predates correction of the disabled-heating ablation; pilot02 includes that fix; pilot03 freezes the final validator. Only pilot03 supports final results. Test01 found a floating equality assertion; test03 found malformed time fields incorrectly classified unsupported. Both are fixed in tests04; failed records were retained.
