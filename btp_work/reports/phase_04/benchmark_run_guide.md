# Matched Phase 1, Phase 3 and Phase 4 benchmarks

The original Phase 1 campaign remains separate. These two new commands prepare frozen studies and start independent hidden controllers. Run from C:\Users\hp\Documents\BTP:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase3
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-ModelComparison.ps1 -Track phase4
```

Both controllers wait while the original Phase 1 controller lock is held, and serialize with each other. They survive closing the launching terminal and do not need an active agent. Rerun the same command to resume; successful committed targets are skipped. Automatic idle sleep is inhibited during execution; manual sleep/shutdown can interrupt a worker, whose timing is then rejected. No automatic startup task is installed.

| Track | Work | Output |
| --- | --- | --- |
| phase3 | Rescore all 66 saved RFT schedules and the 66 corrected DasAtom schedules as they become available, under the Phase 3 cubic/no-cooling model | runs/phase03_matched_benchmark_v1 |
| phase4 | On the same 66 RFT targets, verify a fresh unmodified control and run all four lookahead horizons: h1/2/4/8, gamma .9, uniform weights | runs/phase04_matched_benchmark_v1 |

Phase 3 changes accounting and retimes existing movement; it does not change parking or routing. It reuses original compilation times explicitly and records scoring time separately. Missing/failed Phase 1 DasAtom schedules remain visible as pending; the same phase3 command can consume later completed schedules. The phase4 track adds 264 modified configurations and 66 fresh original controls. Each target also exports its saved original schedule scored under the common model. DasAtom is the unchanged anchor from the phase3 results; Phase 4 only modifies RFT.

The accepted [Phase 1 comparison contract](../../runs/phase01_frozen_baseline_v1/comparison_contract.json) governs inputs, full registers, grids, layout, seeds and timing. Every phase4 target must reproduce the saved native instruction text and final global RNG state before modified comparisons proceed. A mismatch is retained as an error, not interpreted as a lookahead improvement. New event-index construction and parking work are inside the original run_benchmark timer. Imports, frozen module setup, offline layout sampling, warmup and scoring are outside it. Small paired original controls expose host/timer drift; one fresh timing per variant is diagnostic and does not by itself establish a statistical speedup.

Diagnostic samples are bounded to eight decisions/batches for large runs. The worker uses the same production FutureEventIndex and FuturePotential implementations, including candidates, score, anchors, horizon and ties. [Acceptance tests](benchmark_tests_03/result.json) prove instruction/RNG equivalence with full production diagnostics on 16 pilot case/horizon combinations. They also test real detached launch/resume, frozen inputs, QFT5 exact native compatibility, common profile/geometry across all horizons and corrected DasAtom rescoring. Earlier failed smoke outputs remain archived; the missing converter dependency and test-isolation issue were fixed before acceptance.

Each study contains frozen code/inputs/config hashes, manifest.json, progress.json, summary.json, results.csv, controller logs and immutable per-attempt worker artifacts. Workers are serial with one numerical thread, a monitored process-family 4 GiB working-set cap and finite wall caps (600 seconds for rescoring; 1800 seconds per phase4 target including its control and four horizons). Terminal failures remain explicit and are not automatically retried indefinitely.

Check progress or request a stop for either study:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\model_comparison.py status --track phase3
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\model_comparison.py status --track phase4
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\model_comparison.py stop --track phase3
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\model_comparison.py stop --track phase4
```

If the user restarts Phase 1 during a phase4 worker, the comparison controller flags the overlap and withholds that timing. The original Phase 1 process is never stopped by this controller.

For analysis, join rows on target_id, normalized_sha256, profile_sha256 and geometry_sha256, and compare accepted schedules only, retaining failed/pending counts. results.csv includes legacy_E/fidelity/runtime, extended_E/fidelity/makespan, every error-budget component, compile/scoring times, movement counts, h/gamma and source paths. The phase4 rows include delta_extended_E_vs_original. Compare horizons against generalized h1 as well as the exact original control.

Use Phase 1 versus phase3 to show the effect of the cost model on the same schedules. Use original_phase3 versus lookahead rows under the same model to assess the algorithm. Do not interpret different scoring models' fidelity proxies as an algorithmic gain. The shared two-plane geometry is a declared analytical assumption, not new native-device evidence. Timing/scoring covers the normalized CZ skeleton, with cooling disabled; omitted one-qubit timing and calibrated device fidelity are outside scope. No best k is selected, and the small Phase 4 pilot found no improvement over legacy. Full runs and validated analysis are still required for conclusions in the report.
