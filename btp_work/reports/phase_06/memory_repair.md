# Phase 6 memory repair and full rerun

The original `runs/phase06_matched_benchmark_v1` finished 42 targets successfully
and hit the observed 4 GiB family working-set limit on 24 targets. It is preserved,
including raw attempts, accepted checkpoints, manifests and result CSV. The
replacement `runs/phase06_matched_benchmark_v2` reruns all 66 targets/528 rows;
its timings are not mixed with v1. Source launcher start/status/stop defaults
now select v2. Original frozen controllers still belong to their original studies.

The full rerun started after both stress cases passed. Their two fresh v2
measurements form the first 16 accepted campaign rows, avoiding about 33 minutes
of duplicate execution. They used the exact frozen production worker, inputs,
seed/RNG protocol, eight controls, 7200-second/4-GiB limits and serial execution
lock. All artifact hashes are verified on import; raw commands, outputs and
timing values remain unchanged. Both the original evidence directories and
canonical hardlink/copy are retained, with source-record hashes and provenance
under `measurement_imports/`. No v1 observations are imported. The controller
continues the remaining 64 targets.

[memory_repair_verification.json](memory_repair_verification.json) binds the
23 scientific/memory checks, 24 paired rows/74 candidate audits, stress results,
five matching partial rows from original OOM attempts, frozen execution hashes,
and original v1 dataset hashes. Stress peaks were 1.00 GiB for square_root_7 and
1.11 GiB for QFT60, with all eight rows accepted on each.

## Root cause and execution changes

Replay captured full pending/completed gate lists and both MT19937 states at
every boundary. JSON normalization duplicated strings and integers. Deep copies
then multiplied the compilation evidence across incumbent, candidate, accepted
history and checkpoint objects. Large formatted JSON strings and whole-bundle
fingerprints added transient allocations. Worker local variables also retained
the preceding budget's full result during the next repair call.

Allocation profiling additionally found that dynamically compiled function
globals retain the finished replay context even after its module is removed
from `sys.modules`. Each retained context kept its full parking candidate-score
tables and snapshots. Garbage collection alone did not detach these references.

`tools/phase06_memory.py` provides an execution scope over the unchanged accepted
scientific implementation:

- Freeze completed compilation evidence into read-only dict/list subclasses
  with identical JSON values/equality. Deep copies share that immutable evidence;
  mutable override plans and outer compilation mappings remain independent.
- Intern repeated gate-ID strings and share repeated MT19937 integer blocks
  without dropping any snapshot field or RNG value.
- Stream canonical full-bundle hashing and formatted artifact JSON in bounded
  chunks instead of allocating the complete encoded strings. Nonfinite-value
  encoding and atomic temporary-file replacement are preserved.
- Suppress only the evaluator's optional `event_audit`, which the original
  bundle writer removed before saving. Full trace, timed schedule, validation,
  error terms, final carriers/heating/exposure and every proposal remain saved.
- Explicitly detach a completed replay context's attributes after the returned
  compilation owns all required frozen evidence. This frees parking/candidate
  tables retained by dynamic function globals without mutating saved evidence.
  Release full completed budget results before the next budget/policy and
  collect unreachable hooked-module cycles.

The scoped hooks restore their original functions/classes after execution.
No accepted `implementation/` or `configs/` scientific file is edited. No
candidate is pruned and no evaluation budget, precision, physics formula,
acceptance threshold, routing RNG or memory cap changes. Timed replay includes
its new compaction/cleanup. Artifact export and post-budget cleanup remain
outside the repair API timer, as separately described by the original timing
contract; compare v2 timings within v2.

## Validation

[memory_scientific_tests_03/result.json](memory_scientific_tests_03/result.json)
records 23 passing checks: 20 original scientific behavior groups, an updated
source-preservation check that explicitly permits operational launcher changes,
lossless JSON/hash/immutability checks, and repeated finished-context release
while verifying that every returned evidence value remains unchanged. The original preservation test was
first run unchanged and correctly flagged the modified operational launcher;
that initial report is retained in `memory_scientific_tests_01`.

[memory_integration_tests_02/result.json](memory_integration_tests_02/result.json)
records 24 accepted full worker rows, detached launch/resume, Phase 5 exact
starting instructions/scores, rollback/budget checks and timing-contamination
rejection. This exercises the finished-context fix. The final frozen v2
execution revision is exercised by the stress tests below.

[memory_stress_tests_02/equivalence.json](memory_stress_tests_02/equivalence.json)
compares 24 result rows and all 74 candidate audits with v1: same E/F/makespan,
candidate plans/order, accept/reject decisions, prefix evidence, full error
budgets, schedule/instruction hashes and final routing RNG. Timings and paths
are intentionally different.

[memory_stress_tests_02/result.json](memory_stress_tests_02/result.json) records
final frozen-worker reruns of both previously failing extremes: `square_root_7`
and QFT60 on grid 11, all eight policy/budget rows each, under the unchanged
4 GiB cap. Raw owned-process measurements and peak working sets are retained
alongside that report. This report is complete only when its result says passed;
campaign progress remains separate from verification.

The initial storage-only repair still hit the cap during the largest stress
case. That failed test is preserved in `memory_stress_tests_01` and was not
launched as a production rerun. The completed context-lifetime fix is frozen
separately under the v2 study's `execution_optimization_v1` with a manifest/hash
bound to its unchanged parent study. Its controller verifies both sets of files
before each target. The source launcher prepares/verifies that execution revision
and runs its controller, using the same mechanism as the earlier Phase 3
execution revision.

## Start/resume and inspect

From `C:\Users\hp\Documents\BTP`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase6 -Study .\btp_work\runs\phase06_matched_benchmark_v2
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\model_comparison.py status --track phase6 --study .\btp_work\runs\phase06_matched_benchmark_v2
```

The first command resumes the replacement campaign and skips its successful
targets. The second reads status. A complete result still requires all 66
targets/528 rows to finish and be analyzed; stress-test success alone does not
claim full campaign completion.
