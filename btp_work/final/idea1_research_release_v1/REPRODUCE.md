# Reproduce the Idea1 research evidence

Run from `btp_work` with pinned CPython3.13.2 and the original29-package hash lock. Use fresh output names: scripts refuse to overwrite earlier studies/analyses. Scientific sources are preserved in each study's frozen directory. No internet, browser, document library or active agent is required for aggregate regeneration.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 analysis/idea1_hardware_counterfactuals.py --out reports/phase_08/hardware_counterfactual_new
.\.venv\Scripts\python.exe -B -X utf8 analysis/idea1_final_analysis.py --out reports/phase_08/completion_rebuild_new
.\.venv\Scripts\python.exe -B -X utf8 analysis/idea1_mechanism_audit.py --out reports/phase_08/mechanism_rebuild_new
.\.venv\Scripts\python.exe -B -X utf8 analysis/idea1_snapshot_accounting.py --out reports/phase_08/snapshot_rebuild_new
.\.venv\Scripts\python.exe -B -X utf8 tests/idea1_completion_analysis_acceptance.py --out reports/phase_08/completion_tests_new
```

The main final analysis deliberately binds the accepted `hardware_counterfactual_02` by its source CSV hash; the first command independently reconstructs that calculation for comparison. It regenerates all completion-study numerical CSVs and scientific SVG/PDF/PNG figures from frozen raw data. The mechanism audit reads existing matrices rather than compiling again. The snapshot audit streams about1.7GB of existing JSON without loading gigabyte objects.

For the earlier132/396/792/528-row matrices and the448-row factorial:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 analysis/phase08_incremental.py --out reports/phase_08/old_aggregate_rebuild_new --extension runs/idea1_extension_v1
.\.venv\Scripts\python.exe -B -X utf8 analysis/phase08_primary.py --study runs/idea1_extension_v1 --out reports/phase_08/old_primary_rebuild_new
```

An independent schedule replay of the initial portfolio takes roughly11minutes on this host and streams14.75GB of recorded artifacts. This is verification cost, not compilation timing:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 tools/audit_idea1_completion.py --study runs/remaining_experiments_6h_v2 --out reports/phase_07/replay_initial_new
.\.venv\Scripts\python.exe -B -X utf8 tools/audit_idea1_completion.py --study runs/idea1_completion_followup_v1 --out reports/phase_07/replay_followup_new
```

For a small original/full-method compile, validation,32-column original QFT5 semantic proof and figure:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 tools/reproduce_incremental_release.py --out final/reproduction_new
```

The tested clean environment is `final/repro_env`, installed from `configs/environment/requirements-py313-win64.lock`. [The original fresh-environment receipt](../reproduction_clean_01/verification.json) verifies all29 exact packages and an8.55-second tiny workflow. [The new clean rebuild](../../reports/phase_09/completion_clean_rebuild_01/verification.json) reproduces every final numerical CSV and both hardware/cooling tables; seven weighted-feature/semantic groups and five analysis hand-oracle groups also pass there.

Raw generation and capped-run commands remain in [the protocol](../../reports/phase_07/study_protocol.md) and [the original run guide](../../reports/phase_07/remaining_campaign_run_guide.md). Re-running those completed study names skips terminal cells; changing code, caps, inputs or physical assumptions requires a separately named frozen study. Do not rerun completed large matrices just to regenerate a plot.
