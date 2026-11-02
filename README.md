# Idea 1: noise and routability aware compilation

Implementation and evaluation of lookahead, assignment, bounded repair,
and analytical movement/error accounting in neutral atom compilation.

## Read the results

- [Final research findings](btp_work/final/idea1_research_release_v1/RESEARCH_ANALYSIS.md)
- [Representative QFT5 reproduction](btp_work/final/reproduction_clean_01/verification.json)
- [Reproduction instructions](REPRODUCIBILITY.md)

The directory layout supports source-relative imports.

## Set up and verify

Run from this repository root. The research used CPython 3.13.2 on Windows.

~~~powershell
python verify_package.py
python prepare_data.py
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r btp_work/configs/environment/requirements-py313-win64.lock
~~~

prepare_data.py restores archived upstream QASM inputs inside this repository.
Extracted inputs are ignored by Git because their contents are stored in data_archives/.

## Small reproduction and safeguards

Use fresh output names when repeating these commands.

~~~powershell
.\.venv\Scripts\python.exe -B btp_work/tools/reproduce_incremental_release.py --out btp_work/final/reproduction_github
.\.venv\Scripts\python.exe -B btp_work/tests/idea1_completion_analysis_acceptance.py --out btp_work/reports/github_checks/statistics
~~~

The reproduction compiles control/full variants, independently replays them and
checks all 32 QFT5 basis columns. It does not rerun large benchmark campaigns.


## Contents and attribution

btp_work/implementation/ contains the methods; configs/, benchmarks/, tools/,
tests/ and analysis/ contain experiments and evaluation. Analysis outputs and selected
runs contain saved evidence and all outcome rows, including unsuccessful results.
See THIRD_PARTY.md and upstream licences. No environments, downloaded papers,
browser profiles or portable binaries are included.

Read REPRODUCIBILITY.md before attempting full raw replay. Cite the repository
URL, submission tag and commit hash when citing this work.
