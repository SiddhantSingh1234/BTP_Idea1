# Phase 03 changes versus original work

All implementation below is NEW Phase03 work. All new files remain in btp_work. Source papers, Intern_Report, vendor compilers, original benchmarks, trace-v1 fixtures/adapters/scorer, native worker and live controller were not edited.

| New location | Purpose |
| --- | --- |
| [movement_error](../../implementation/movement_error) | Profiles, physics, immutable transformation, independent validation, scoring and local predictor |
| [hardware profiles](../../configs/hardware) | Seven source-annotated model/ablation profiles |
| [envelope schema](../../configs/schemas/schedule_phase03_v1.schema.json) | Separate format; trace-v1 stays unchanged |
| [CLI](../../tools/phase03_model.py) | Rescore, transform, check and evaluate |
| [tests](../../tests/phase_03_acceptance.py) | Physics/adversarial checks and old artifact hashes |
| [pilot runner](../../tools/run_phase03_pilot.py) | Fixed inputs, sensitivity, raw schedules/budgets/rankings/figures |
| [research tool](../../tools/research_phase03_sources.py), [profile materializer](../../tools/create_phase03_profiles.py) | Isolated source evidence and reproducible profiles |
| reports/phase_03, runs/phase_03, handoffs/phase_03.md | Research, tests, raw records and handoff |
| source_review/phase03_atomique, source_review/phase03_additional, .phase03-tools | Isolated source evidence/renderer; benchmark environment unchanged |

README, STATUS, Phase03 brief and Phase02 handoff receive marked BEGIN PHASE03/END PHASE03 updates under D004. Original planning bytes are retained as `.original.txt` in [original_planning](original_planning). Older Phase02 gate/report results remain historical evidence; no final dataset audit is fabricated. Phase01 remains in progress.

[Final tests](tests_04/result.json) report no original Phase02 tested artifact changes. The [unchanged Phase02 suite](phase02_regression_01/result.json) passes. New modules carry Phase03 docstrings. SHA256 manifests identify the implementation; no Git commit identity is invented. Earlier failed tests and pilot versions remain archived with explicit supersession.
