# Phase 04 fixed pre-evaluation pilot

[Manifest](../../runs/phase_04/pilot_03/pilot_manifest.json), [CSV](pilot_results.csv), [JSON and code hashes](pilot_results.json), [raw workers/requests](../../runs/phase_04/pilot_01/raw), [SVG](pilot_results.svg), [PNG](pilot_results.png). Copies under this report are identical to the canonical run exports.

Four cases x two routing seeds x five policies = 40 accepted schedules, all passing the common independent validator and Phase 03 cubic/no-cooling evaluator. The cases are frozen normalized QFT5, the full-register RFT Table-II smoke, the existing ladder6 eviction fixture and a synthetic ladder7 serialized-layer fixture. Offline layouts are fixed. Gamma .9 and uniform weights were declared before evaluation; no tuning occurred. Initial idle and eviction parking both use the selected policy.

Quality seeds 42/43 are distinct from timing repetitions. Seed42 has three fixed-seed timing samples; seed43 has one, for 80 timing samples total, not 80 independent quality trials. Workers are short, serial, below-normal priority with one numerical thread and a 45-second cap. No timeout/error occurred. Total foreground pilot wall time was 99.19 seconds, dominated by fresh worker imports and evidence writing. This does not invoke or restart the Phase 01 controller.

## Error results: no strict improvement over legacy in this pilot

Seed42 is shown below; seed43 has the same E outcomes here. Lower E is better.

| Case | Legacy E | h1 E | h2 E | h4 E | h8 E |
| --- | ---: | ---: | ---: | ---: | ---: |
| QFT5, ladder7 | .160503219162 | .160834473943 | .160834473943 | .160503219162 | .160503219162 |
| Table-II smoke, ladder7 | .060322141155 | .075798672693 | .060322141155 | .060322141155 | .060322141155 |
| Existing eviction, ladder6 | .035291000679 | .035291000679 | .035291000679 | .035291000679 | .035291000679 |
| Serialized fixture, ladder7 | .047760661474 | .047760661474 | .047760661474 | .047760661474 | .047760661474 |

Across all 40 rows, 34 equal the matched legacy E and six are worse; none is strictly better. Larger horizons recover the legacy result in the two affected benchmark cases. These recoveries are not labelled improvements over the original control.

QFT5 h1/h2 add about 99.38 us to retimed makespan with the same ten moved atom-events. Table-II h1 changes initial idle placement, increases moved atom-events from one to five and makespan from 296.75 to 993.41 us. It has no eviction calls, illustrating why initial-placement scope must be explicit. Other horizons restore the old movement result. Repeated-pair endpoint stability, evictions, batches, transfers, distances, full raw E terms and hashes remain available in the CSV/raw evaluator records.

## Geometry and model scope

Every policy uses the same declared testing geometry: separate SLM/AOD planes with one-spacing clearance, a single ordered AOD and ordinary transfer primitives. The profile makes assumptions explicit for analytical validation. It is not newly measured native geometry, a continuous optical-control proof or a device-performance claim. Physics and scoring are delegated to Phase 03; the parking objective is a distance surrogate, not a private fidelity formula. Only the normalized CZ skeleton is timed/scored. Original one-qubit semantic restoration is a separate check.

## Timing and memory

The event index occupies 3,438-13,468 reachable Python bytes on these cases; separate tracemalloc construction peaks are 6,160-19,064 bytes. Query allocation measurements and per-call time are saved. Reachable size counts shared referents once; tracemalloc captures new Python allocations, not process RSS or native-library memory. Memory diagnostics run separately from timing samples.

Event-index construction and queries are timed separately. Planner times are roughly sub-millisecond to a few milliseconds and noisy under a shared machine. The wrapper also records total compile setup time and direct unmodified-source control time. Its planner-only clock excludes event-index setup, while the source legacy RFT is constructed inside the planner; all fields must be interpreted with that distinction. Do not infer end-to-end speedup from the plot. The Phase 01 compiler timer includes additional QASM/DAG work and is not directly comparable to this narrow clock.

## Nonmonotonic horizon example

[Refined raw example](../../runs/phase_04/pilot_03/nonmonotonic_horizon.json): current site (0,0), two genuinely vacant targets (0,2)/(2,1), anchors (0,3)/(4,1), gamma 1. h1 chooses (0,2), while h2 chooses (2,1) because 2+sqrt8 is less than 1+sqrt17. Both targets leave the later gates in range. Both choices require the same transfer population and legal motion; h2 travels farther. E rises from .012331905897 to .012344475311 and time from 149.9445 to 156.2292 us. Both traces independently validate in the declared single-plane fixture. This demonstrates that a better future-distance score need not improve full E.

## Development/evaluation boundary

Development uses exact oracle/analytic fixtures. The fixed pre-evaluation set is named in the manifest; gamma was not selected from its outcomes. It is not a final held-out performance study. Compare modified schedules against the accepted reduced Phase 01 baseline using matched input/layout/seed/correction/geometry/evaluator and comparable timing before making broad claims. Existing data versions remain distinct.


## Final evidence provenance

The canonical final evidence is [pilot03](../../runs/phase_04/pilot_03/pilot_results.json): it reuses the first complete 40 compiled attempts from pilot01 and [replays every schedule](../../runs/phase_04/pilot_03/cached_replay.json) with the current model, obtaining identical budgets. All current compiled-case dictionaries (circuits, schedules, layouts, geometry and options) match the original manifest. Production lookahead, worker and model code hashes remain unchanged; only the standalone counterexample fixture was refined. Its fresh two-vacancy schedules are saved separately. Final replay took about 2.73 seconds and performed zero fresh compilations. Original compile/timing records retain their original source hashes and paths.

Pilot01 optional-stay counterexample and pilot02 stale-coordinate development outputs remain archived. Tests05 caught the stale gate coordinate; tests06 pass after the gate fields were derived from the corrected anchors. The repeated pilot02 compiler/timing records are retained, not erased or selected by fastest score. Its wall clock includes a long interruption and is not reported as algorithm runtime. The first complete frozen run was selected by chronology, not by quality or speed. This pilot makes no timing-performance claim.
