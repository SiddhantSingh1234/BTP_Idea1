# Reproduction

Use CPython 3.13.2 and the pinned environment recorded in
btp_work/configs/environment/requirements-py313-win64.lock.
Run setup, verification and small reproductions from the repository root as
described in README.md.

## Research evidence

- Methods, configurations, experiment runners, tests and benchmark inputs.
- Complete outcome tables for the selected authoritative studies, including
  timeouts and unsupported outcomes.
- Statistical analysis, scientific plots and full-precision result tables.
- A complete QFT5 control/full-method example with trace, schedule, independent
  replay and all 32 basis-column semantic checks.

Read btp_work/final/idea1_research_release_v1/RESEARCH_ANALYSIS.md for the findings.

## Data and integrity

Run python prepare_data.py to restore the upstream QASM inputs from data_archives/.
Run python verify_package.py to check repository files and archived data.
Add --extracted to also check restored data against its recorded hashes.
PACKAGE_MANIFEST.json records file sizes and SHA-256 hashes.

## Requirements for larger replays

Full large-circuit schedule replay and hardware counterfactual regeneration
require the full raw experiment history, which is not distributed in this
repository. Saved result tables, matched hardware tables and snapshot accounting
are included for analysis and inspection.

The aggregate-analysis script can use the included outcome and hardware tables.
Reconstructing snapshot_storage.csv from raw compilation-file byte sizes requires
the large compilation histories; use the saved snapshot accounting table for
that measurement.

The historical REPRODUCE.md documents the full research workflow. The root README
provides commands for the self-contained small reproduction and statistical
safeguards. Use fresh output directories for every new experiment.

