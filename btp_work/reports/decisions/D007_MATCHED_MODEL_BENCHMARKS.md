# D007: matched original, Phase 3 and Phase 4 benchmark commands

The user requested two additional commands: original code under the Phase 3 cost model, and the modifications through Phase 4, comparable to the original Phase 1 campaign.

The [run guide](../phase_04/benchmark_run_guide.md) defines two separate frozen/resumable studies. Phase 3 reuses all saved RFT schedules and completed corrected DasAtom schedules, retiming/scoring them under extended_no_cooling.v1. No new compiler timings are invented for rescoring. Phase 4 reuses the same 66 RFT inputs/grids/layouts/options, reconstructs the original warmup/RNG sequence, verifies exact original instructions and final RNG state, then measures h1/2/4/8 with the same common evaluator/geometry. Its event index and parking calls are charged inside the original RFT timer.

The user's running Phase 1 campaign is not modified or stopped. Both new controllers wait for its OS lock and serialize with each other. New controls and all unsupported/invalid/timeout outcomes are retained. Corrected DasAtom remains the unchanged anchor, not a Phase 4 heuristic variant. No cooling resources or later assignment/repair algorithms are silently enabled.

The new benchmark worker bounds diagnostic snapshots while reusing the production event index and potential. Eight [acceptance groups](../phase_04/benchmark_tests_03/result.json) pass, including equivalence of complete instructions/RNG states on all 16 pilot case/horizon combinations, actual detached RFT control/all-horizon smokes, resume and DasAtom scoring. This prepares the experiment infrastructure; it does not claim that the full evaluation or report analysis is complete. The analytical geometry and CZ-only scoring limitations remain explicit.
