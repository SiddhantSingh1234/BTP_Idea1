Both full pinned archive working trees are recovered and runnable. Their 512 RFT
and 499 DasAtom blobs are verified in `../runs/phase_00/verified_source_trees.json`.
Upstream files/licenses remain unchanged. See `../handoffs/phase_00.md` for tested
commands, dependency lock and unresolved manuscript evidence.

The following paragraph records the earlier blocked state, not current status:

The retained files in `../source_review/upstream_excerpt/NAQC_Compiler` remain an
incomplete, unmodified reference excerpt. They are not an installed baseline.

`../tools/recover_phase00_sources.py` downloads complete revision archives and
checks all Git blob hashes against the saved repository trees before extracting
under this directory. It neither installs packages nor executes upstream code.
The download was attempted in Phase 00 and blocked by local network permissions;
see `../runs/phase_00/source_recovery_attempt_01.json`. A successful archive still
needs an environment, a historical Git checkout for the paper audit, and smoke tests.
