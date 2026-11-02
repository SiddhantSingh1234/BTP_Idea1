# D004: repair and rerun invalid baselines after the current campaign

Owner: Codex /root. User-directed follow-up, 28 October 2026:
"so once this finishes we should repair those invalid runs as well".

The current frozen native campaign continues unchanged. After it finishes,
repair the underlying causes in a separately versioned corrected baseline and
measure the corrected compiler again. This is required follow-up work, not an
optional demonstration or permission to relabel old invalid schedules as valid.

## Execution order and acceptance

1. Freeze the current attempt/omission inventory and retain every original
   measurement, trace, error, source pin and input hash. Group failures by root
   cause and unique configuration rather than counting repeated timing runs as
   distinct defects. Include related unsupported-register cases in the inventory.
2. Create minimal failing regressions. Known classes are occupied destinations
   between DasAtom movement batches and omitted trailing inactive qubits. Inspect
   any additional failures discovered by the completed all-repetition audit.
3. Fix the actual routing/register-handling implementation in a separate
   corrected code path under btp_work; keep the vendor snapshots immutable.
   Preserve supported circuit identity, declared register, geometry, source
   configuration and seeds. Distinguish necessary schedule corrections from
   proposed lookahead/assignment/score-driven heuristics, which remain disabled.
4. Use the existing conservative staging control as correctness evidence only.
   It is not an already repaired full benchmark and is not automatically the
   final efficient corrected router. Record changed decisions and any remaining
   unsupported capacity/path cases explicitly.
5. Run independent geometry, occupancy, logical, transfer/resource and tiny
   full-circuit checks. Retest previously valid cases as regressions. Missing
   physical evidence remains a coverage limitation, never an assumed pass.
6. Rerun affected configurations with fresh compilation measurements, including
   corrected preprocessing/layout/compile scopes and resource observations.
   Then rerun the affected algorithm's full target matrix with the same correction
   enabled uniformly, rather than creating a baseline that patches only failed
   test instances. Use the same requested hardware/input/register policy for
   comparisons; declare any mismatch as a separate track.
7. Save a new corrected benchmark with its own code hashes, configuration,
   attempt IDs, repetitions, counts, timing, scores, traces and validation reports.
   Link each corrected result to its native reference. Original invalid rows
   remain invalid and are excluded from comparisons of valid schedules.
8. Update Phase 01/02 handoffs and gates. Future heuristic variants must use
   the same applicable correctness fixes. Report unrepairable/unsupported cases
   honestly; no guarantee that every requested configuration admits a legal
   schedule is made.

The queued specification is [corrected_baseline_followup_v1.json](../../configs/studies/corrected_baseline_followup_v1.json).
It is declarative: implementation and corrected reruns have not started. The
running native controller and background auditor do not automatically execute
this not-yet-implemented repair campaign. A later owner must carry out this
required follow-up before accepting the corrected dataset.
