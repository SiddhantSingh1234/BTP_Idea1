# Phase 05 change ledger

New implementation: implementation/assignment/{matching,costs,integration,oracle,fixtures}.py and package init. The matching solver exposes forbidden edges, rectangular row coverage and (maximum,sum) optimization. Cost construction reuses accepted FutureEventIndex/FuturePotential and Phase03 local physics. The isolated compiler hooks change unresolved assignment/orientation only; a read-only emitted-route observer tracks already realized heating.

New controls: configs/variants/assignment.*.json (13), and configs/studies/phase05_pilot_v1.json. Weights, normalizers, factor2 expansion and development/evaluation identity hashes were frozen before measurement. The extra original_legacy worker label uses the passthrough assignment with legacy parking. Neither candidate expansion nor correction is hidden in a novel-objective comparison.

New tools: phase05_worker.py, run_phase05_pilot.py, finalize_phase05_evidence.py, check_phase05.py. New tests: phase_05_acceptance.py (17 groups). Reports/handoff preserve all controls, failures, semantic proofs, metadata and measured dimensions.

Research additions are archived in source_review/phase05_primary, including three PDFs, page-marked extracted text, checksums, source URLs, README and references.bib. Existing seven supplied PDFs/proposal and existing source excerpts were read without changes. Intern_Report was excluded.

The original planning files are archived at reports/phase_05/original_planning. README/status/Phase05 brief are updated to link final evidence. Original sources, shared model/validator/evaluator, Phase04 package, benchmark launchers/controllers and all frozen executable studies are unchanged by hash. Native raw results are never overwritten.

The first zero-capacity check caught an inherited uninitialized center variable. The new entrypoint now raises a finite explicit AssignmentInfeasible before that code path. Tests03 add normalization/displacement coverage. No weight tuning or outcome-selected removal occurred. Graph generation seeds and static-adversary labels stay in the fixed protocol. Phase06 repair, new router logic and cooling are not introduced.
