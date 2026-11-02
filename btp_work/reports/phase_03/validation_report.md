# Phase 03 validation report

Owner Codex /root,28 October2026. [Final evidence gate](gate_01.json) passes; Phase03 is complete within its declared analytical scope. [D004](../decisions/D004_PHASE03_MODEL_AND_DEPENDENCY.md), [specification](model_specification.md), [research/citations](source_research.md).

[Sixteen groups pass](tests_04/result.json); [transcript](tests_04/unittest.txt). Coverage: published/SI examples; cubic/triangular/capped intermediate positions; fixed-time scaling and acceleration-distance cancellation; unequal synchronized paths; repeated conditional loss; extreme tails against independent SciPy; event-time heating; per-qubit exposure;2CNOT cooling amplitudes with an entangled reference; exact cooling populations/time; finite banks; malformed events; stale carriers; missing resources/bad docking/duplicates; invalid probabilities; underflow and infinity. Frozen ideal/transfer ablation isolates per-atom transfer fidelity. Local prediction matches declared replay and reports omitted suffix scope.

All14 unchanged Phase02 groups pass in [regression01](phase02_regression_01/result.json), including both original-QFT5 semantic checks. Original tested files remain hash-identical to Phase02 tests05. All CLI paths return ok: [frozen rescore](../../runs/phase_03/cli_rescore_01/result.json), [cooling transform](../../runs/phase_03/cli_cooling_01/result.json), [independent check](cli_cooling_check_01.json), [evaluate](cli_cooling_evaluate_01.json).

| Mandatory criterion | Evidence and scope |
| --- | --- |
| Timing/trajectory/heating/loss/cooling/exposure consistent or approximation-labelled | Compatible cubic default, labelled surrogates, asymptotic guard, explicit primitive contract and analytic/numerical checks |
| Historical results reproducible without changed decisions | Untouched scorer, actual saved RFT/DasAtom QFT5 exact-score checks, immutable source/decision hashes and separate schedule operations |
| Terms/populations/limits/units independently checked | Published/SI examples, independent tail/amplitude checks, hand duration/exposure/count oracles and no-double-count tests |
| Resource-enabled cooling validates; unsupported cooling never free | Synthetic stress passes;2CZ+4H per atom, timed finite-bank preparation/registration and transfers; exhaustion unsupported; basic profile never resets |
| Limitations/uncalibrated parameters explicit | Source/parameter table; native/corrected/synthetic tracks;41 unsupported and3 invalid outcomes retained; no calibrated/performance claim |

The [56-row pilot](error_budget_pilot.md) is not the Phase01 campaign. Native physical coverage remains unsupported. Bank validation is within its declared primitive; no experimental cooling or continuous beam-control proof is claimed. Timed computation is the normalized CZ skeleton. Effective coherence, phase-averaged heating and independent multiplication are assumptions. Phase01 final dataset and exact manuscript provenance remain open.

Earlier failures remain archived: test01's floating equality assertion and test03's missing-time classification were fixed before tests04. Pilot01 predates the disabled-heating ablation fix. Final evidence uses tests04/pilot03 and the separate unchanged Phase02 regression.
