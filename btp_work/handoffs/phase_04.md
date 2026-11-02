# Final benchmark analysis checkpoint, 29 October 2026

Full matched benchmark:396 accepted rows. h1 better/tie/worse E counts41/2/23; h2 41/3/22; h4 37/4/25; h8 32/4/30. Median compilation overhead is positive. No best h or universal gain is claimed. Artifact/inline-validation/budget audit passed; no additional full physical replay was run.

[Audited results and plots](../reports/final_benchmark_analysis_01/report.md) | [Final gate](../reports/final_benchmark_analysis_01/final_gate.json).

Earlier checkpoints below remain historical evidence.

---

# Phase 04 handoff: occurrence-based lookahead parking

Owner: Codex /root, 28 October 2026. **Status: complete within the declared implementation/pilot scope.** [Final gate](../reports/phase_04/gate_01.json) passes. Accepted dependency: [Phase 03](phase_03.md). Phase 01 remains a separate reduced, user-controlled benchmark campaign; no controller was started or modified here. All new work stays in btp_work. Intern_Report was excluded. No applicable AGENTS.md was found in the workspace ancestors/new-work subtree. No subagents were used.

## Delivered scope and identity

NEW [lookahead package](../implementation/lookahead), five [lookahead configs](../configs/variants), [worker CLI](../tools/phase04_worker.py), [pilot runner](../tools/run_phase04_pilot.py), [cached-evidence replay](../tools/finalize_phase04_evidence.py), [tests](../tests/phase_04_acceptance.py). [Specification](../reports/phase_04/lookahead_spec.md), [citations](../reports/phase_04/source_research.md), [D006](../reports/decisions/D006_PHASE04_EVENT_LOOKAHEAD.md), [change ledger](../reports/phase_04/change_ledger.md).

No local Git commit identity is invented. [Tests06 hashes](../reports/phase_04/tests_06/result.json) identify current implementation/configs. [Pilot03](../runs/phase_04/pilot_03/pilot_results.json) separately records current replay hashes and original compilation hashes. The only compiled-source helper change concerns the standalone counterexample; every compiled-case dictionary is verified unchanged. Source compiler SHA256 is24651482cf223c1a84d0aeecb1493ee2024e25c2da9bebd37d035023e3ff71bb at pinned RFT revision3d1f09233c2acd357fd9fbfad1b5300a921d301a.

The new sparse index preserves repeated gate occurrences and handles pending, active and consumed current-layer gates. Generalized parking uses only a frozen current/committed-active snapshot. Legacy_exact delegates to the original picker. Both initial idle placement and eviction use the selected parking policy. The static layout, active local heuristics, assignment/orientation, candidate sets and router are preserved; assignment future bias stays disabled. No Phase 05 objective or repair is enabled.

## Actual tested commands

Working directory C:\Users\hp\Documents\BTP; existing Python3.13.2 venv. Existing outputs are immutable; use new suffixes. Algorithms use stdlib plus existing upstream compiler dependencies; plotting uses existing Matplotlib. No dependencies were added for Phase 04.

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_04_acceptance.py --out btp_work/reports/phase_04/tests_06
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_03_acceptance.py --out btp_work/reports/phase_04/phase03_regression_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/run_phase04_pilot.py --out btp_work/runs/phase_04/pilot_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/finalize_phase04_evidence.py --source-pilot btp_work/runs/phase_04/pilot_01 --out btp_work/runs/phase_04/pilot_03
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/phase04_worker.py --request btp_work/runs/phase_04/pilot_01/raw/qft5_ladder7__legacy_exact__s42/request.json --out btp_work/runs/phase_04/cli_legacy_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/phase04_worker.py --request btp_work/runs/phase_04/pilot_01/raw/qft5_ladder7__next_events_h4__s42/request.json --out btp_work/runs/phase_04/cli_h4_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/verify_phase02_original.py --trace btp_work/runs/phase_04/pilot_01/raw/qft5_ladder7__next_events_h1__s42/worker/trace --original btp_work/benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm --out btp_work/reports/phase_04/full_original_h1_01
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/verify_phase02_original.py --trace btp_work/runs/phase_04/pilot_01/raw/qft5_ladder7__next_events_h4__s42/worker/trace --original btp_work/benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm --out btp_work/reports/phase_04/full_original_h4_01
```

Seventeen lookahead groups and sixteen unchanged model groups pass. The oracle checks121,600 queries across1,000 tiny schedules. Both CLI smokes pass. Both full original-QFT5 checks pass32 basis states with error8.33e-16 under explicit one-qubit restoration. Original one-qubit timing is not inferred from that sidecar.

## Acceptance, compatibility and results

Every mandatory criterion is mapped in the [validation report](../reports/phase_04/validation_report.md). All40 pilot schedules and both refined counterexample schedules pass the independent validator/common evaluator within their declared geometry. All eight legacy controls match complete instructions and final RNG hashes. The existing frozen Phase00 eviction trace is reproduced exactly. [Compatibility report](../reports/phase_04/legacy_compatibility_report.md).

[Result report](../reports/phase_04/pilot_results.md), [CSV](../reports/phase_04/pilot_results.csv), [canonical replay](../runs/phase_04/pilot_03/cached_replay.json), [original compiler records](../runs/phase_04/pilot_01/raw). No strict E improvement over legacy occurred:34 rows tie and6 are worse. Generalized h1 changes four case/seed schedules. QFT5 h1/h2 are slightly worse and h4/h8 recover legacy; Table-II h1 is worse and h2/h4/h8 recover legacy. The two other cases are unchanged. No final k is selected. Configs use h1/2/4/8, gamma.9 and uniform weights, without tuning.

The standalone vacant-target example proves nonmonotonicity: h1 chooses(0,2), h2 chooses(2,1); h2 lowers its future-distance score but raises E from.012331905897 to.012344475311 because the move is longer. [Raw evidence](../runs/phase_04/pilot_03/nonmonotonic_horizon.json).

The source compilation run has80 timing samples across40 quality attempts; fixed-seed repeats are not independent quality trials. Final evidence reused those schedules and replayed them identically, performing zero further compilations. Earlier repeated development runs and all timing samples remain archived, including the stale-coordinate fixture failure. First-complete chronology, not best score/time, selected the cached compilation run.

## API and complexity for Phase 05

FutureEventIndex(schedule,N,circuit) stores stable per-qubit event lists. Query with index.query(q,layer,h,completed=...,active=...). Layer is the zero-based schedule-list index; the trace circuit field is one-based. Current pending events have delta0; completed/active IDs are excluded. A normalized CZ circuit supplies stable FIFO gate identities. Empty layers preserve explicit gaps; h0 is rejected.

FuturePotential.from_events(events,known_positions,gamma=...,spacing_um=...) freezes anchors and exposes score(site)/choose(candidates,center). Missing anchors count within h and do not refill the horizon. No future placement map is accepted. Equal weights and zero current-distance term are explicit. Raw/scaled scores and the common log scale are returned; restore a common scale before combining different qubits' potentials. Phase05 must reuse this implementation, not copy a private formula.

Index construction/storage O(N+G). Valid scheduler query O(log degree+h), with a general skipped-record S term outside its prefix invariant. Candidate choice O(F*h). The original assignment/router complexity remains. Verbose sidecars can consume O(D*(F+G+h)) across D decisions; sparse-index complexity is not whole-wrapper memory. Measured table bytes3438-13468 and build allocation peaks6160-19064 exclude native libraries/RSS. Detailed definitions are in raw records/specification.

Planner-only, wrapper/setup, index/query and direct-source clocks are separate. These tiny, noisy diagnostics are not comparable directly with Phase01's full native timer. Before claiming improvement, run matched accepted baseline/modified inputs with the same timing region, validity/correction, geometry/profile, evaluator, layout and seeds. The adapter controls process-global routing RNG; use isolated workers as in the pilot.

## Boundaries and next smoke

The testing geometry assumes separate SLM/AOD planes and one-spacing clearance, identical across policies. This is not measured native geometry or a continuous optical-control proof. The common error model is analytical and scores the normalized CZ skeleton. No calibrated-device gain or final benchmark conclusion is claimed.

The concurrent Phase01 controller stop guard is documented in [this receipt](../reports/phase_04/concurrent_controller_change.json); it matches its archived pre-guard source and D005. It was not reverted. The user subsequently reported reduced reruns. Phase04 does not control them, overwrite raw data or mark Phase01 complete.

Next eligible phase is05, by user direction. A cheap smoke is the successful h4 worker command above with a NEW destination: expect status ok and QFT5 E=.16050321916152577. No need to rerun the full pilot to inspect it. Preserve legacy_exact and generalized h1 separately; no k is promoted to a best default from this small pilot.

Final tested gate command:

```powershell
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/check_phase04.py --out btp_work/reports/phase_04/gate_01.json --finalize
```

All gate checks pass. This closes Phase04 implementation/pilot acceptance, not a performance-improvement claim or Phase01 completion.

## Fresh completion verification

[Completion review](../reports/phase_04/completion_review.md) confirms 17 fresh lookahead groups, 16 fresh model groups, 29 gate checks and 40 fresh schedule replays with identical budgets. The phase brief status/checklist is reconciled with this evidence; no implementation changes were needed. Existing accepted raw runs and gates are preserved. To recheck an already completed phase, run check_phase04.py with a new --out path and omit --finalize, which is the one-time original finalization action.

## Full matched benchmark launch support

The user subsequently requested original-code Phase 3-model and all-through-Phase 4 benchmark commands. [D007](../reports/decisions/D007_MATCHED_MODEL_BENCHMARKS.md), [run guide](../reports/phase_04/benchmark_run_guide.md), [setup evidence](../reports/phase_04/benchmark_setup.json). Two frozen studies are ready and left stopped for user launch, with eight passing runner groups. Phase 4 uses the same 66 RFT targets, exact native controls and h1/2/4/8; Phase 3 reuses existing schedules/timings and applies the common model. The new worker limits diagnostic snapshots while preserving production event/potential behavior, verified by complete instruction/RNG equivalence on 16 pilot combinations. The active original Phase 1 runner is preserved. Full benchmark outcomes and analysis remain pending.
