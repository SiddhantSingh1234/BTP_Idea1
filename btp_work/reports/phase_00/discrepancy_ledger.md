# Phase 00 discrepancy ledger

## Runtime update — 28 October 2026

Sources and environment are now recovered; D17's download/dependency blocker is
resolved. Both complete trees pass all 1,011 saved Git blob checks and both
compilers execute QFT5 successfully. Four fresh-process repeat pairs have
identical traces/counts/scores, including the explicitly unsupported case below.
The old isolated results and failed setup/startup attempts remain evidence.

| ID | Current disposition and evidence | Consequence |
| --- | --- | --- |
| D18 | Confirmed at runtime: `4mod5-v1_22` declares N=16, native DasAtom infers N=5. Its native idle time is 8.8 us/F=0.9463490278828605; rescoring the same partial trace at declared N=16 gives idle=33 us/F=0.9463337602417032 | Native five-qubit run succeeds; full-register matched trace is unsupported. Explicit status in smoke_dasatom_tableII_03/04. No silent padding or count substitution |
| D14 update | Embedded/standalone helper and router code differs by progress logging and its counters; no algorithm-rule difference observed. Seven helper-history blobs do not exactly match embedded helper | Distinct provenance retained; standalone API control is identified. Logging/timing effects are not ignored |
| D01 update | 27 RFT main-history commits, current main=pin, no tags; plot filter 5..60 step5 and table CSV selector ladder8 recovered | Better candidates/context, still no manuscript revision/options/raw-data proof; paper gate remains unresolved |
| D06 update | Exact repeat traces and legacy scores agree for the tested seeded controls/cases | Scope is tiny snapshot cases only. Native DasAtom MIS uses explicit seed 0; completion uses global random choice; ordered basis-set/transpilation/VF2/version effects documented |
| D19 | Native DasAtom main's aggregate row labels `num_moves*4` as transfers, while its scalar scorer increments four per movement batch | Preserve both aliases and identify which result column is compared. Nonzero-transfer native main case not measured in these smokes |

The real full-planner fixture has two forced evictions and a no-future-partner
case, with decisions captured in `runs/phase_00/compiled_fixture_01`. No upstream
fix or new research heuristic was applied. The initial ledger below is retained
for its detailed source facts; availability/unperformed-test statements are
historical where superseded above.

Owner: Codex `/root`, 27 October 2026. Source: retained pinned RFT excerpt and
saved Git trees. **No fixes applied to upstream; no paper reproduction claimed.**
`confirmed` below means a source fact or the stated isolated result, not an
end-to-end compiler failure unless explicitly noted. Raw tested results:
[isolated_final_01](../../runs/phase_00/isolated_final_01.json) and
[isolated_final_02](../../runs/phase_00/isolated_final_02.json). Both pass 27
checks; neither compiles a QASM circuit.

| ID | Issue and disposition | Evidence / minimal case | Consequence and owner |
| --- | --- | --- | --- |
| D01 | `paper_revision_unresolved` | No matching revision/options/raw bundle; history/table scripts unavailable. README names variants 9-11, runner only 1-8 | No exact-paper control. Phase 00/01: recover history/artifacts; author contact requires separate authorization |
| D02 | **Confirmed:** RFT entries are per distinct pair, not one partner/event list | Core `build_right_filled_table`: layers 01,02,01 produce q0 entries `(1,0),(2,1)` at T1; the later 01 is hidden behind current 01 | Several partners already retained, repeated events not generally retained. Phase 04: explicit event oracle/legacy control |
| D03 | **Confirmed:** parking differs from manuscript Eq.6 | `_pick_idle_position`: current (0,0), partner (4,0), sites (1,0)/(4,1): sum rule picks (1,0), pure partner picks (4,1). Delta 3 exceeds eviction cutoff 2; missing target anchor also falls back | Do not assume k=1 equivalence. Alternative eviction already exists. Phase 00/04 |
| D04 | **Confirmed isolated cost/materialization mismatch** | Exact core lines 634-644 executed: p1=(0,0), p2=(0,1), slot [(0,2),(1,2)], valid length 1. Matrix chooses `1+sqrt(5)=3.2360679775`; nearest-first-endpoint materialization produces `2+sqrt(2)=3.4142135624` | Violates selected cost orientation even with bias off; bias is also omitted when materializing. No gate-invalidity or end-to-end impact measured. Separate corrected control must save full-cost orientation |
| D05 | **Confirmed:** transfer alias is four per movement batch | Converter scoring: one moved atom and three moved atoms in one batch both produce transfer alias 4 and same transfer-fidelity factor | Historical proxy is neither unique qubits nor explicit per-atom transfers. Physical transfer stages/events remain unobserved. Phase 02/03 must recover explicit events |
| D06 | **Confirmed:** MIS omits explicit seed; determinism unresolved | AST shows `nx.maximal_independent_set(conflict_graph)` with no seed. Global RNG seeded/consumed by layout sampler; warmup and previous routes consume it | No full-compilation two-run test available. Record global state/order/packages; audit absent DasAtom and Qiskit after recovery |
| D07 | **Confirmed:** fixed temporary filename | Runner line 72 writes `temp_preprocessed.qasm` in current working directory; shared across variants/processes and removed later | Concurrent runs can collide; no racing processes launched. Use isolated run directories; version any later adapter |
| D08 | **Confirmed sparse representation; 67 MB claim unresolved** | `analyze_qasm_file` returns a sparse schedule; RFT builds N*L lists plus per-pair/per-time tuples | Dense manuscript tensor and snapshot differ. Derived bounds in baseline spec; runtime RSS/memory pilot unavailable |
| D09 | **Confirmed unused options/arguments** | Planner never loads `canonical_mapping` or `busiest_pairs`; no square-padding option use in planner; duplicate terminal return; converter R/C signature arguments do not determine its selected grid | Busiest-layer mapping is not actual initial placement; misleading API/docstrings. Preserve source, document behavior; do not claim fixes |
| D10 | **Confirmed:** snapshot `Realistic` is transfer-only diagnostic | Converter lines 46-86 changes f_trans from 1 to .999, retains constant-speed timing and historical idle formula | No heating/loss/cooling/acceleration model implemented. Phase 03 must use a new scorer identity |
| D11 | **Confirmed source predicate; Qiskit barrier run unresolved** | Runner line 23 retains any operation reporting exactly two qubits and rewrites it to CZ; direct analyzer expands multi-qubit nodes into pair combinations | Two-qubit barriers can be treated as gates; no Qiskit runtime to demonstrate actual input behavior. Freeze skeleton identity; test correction separately |
| D12 | **Confirmed isolated exceptional-input defects** | Empty schedule returns []; idle layer only prints skip. With an active pair, empty layout and 2x2 grid, exact planner reaches unbound `center_of_mass`. Full 1x2 swap router returns an error log with no exception | Typed failure/validity contract missing. N>sites end-to-end behavior unresolved. Reject failures in future adapter; no scoring of incomplete schedules |
| D13 | **Confirmed source discrepancy:** promised capacity exception/fallback absent | `GridCapacityError` defined and caught by runner, but planner contains no raise; stall emits text. Router errors are returned as instructions while planner assumes final targets | Error logs can be scored as if complete; independent missing-gate replay required. Phase 01/02; no historical outputs validated here |
| D14 | **Confirmed metadata differences:** embedded versus standalone DasAtom | Main script blob identical; helper embedded `e0b021...` versus standalone `9a681c...`; router embedded `d7f98d...` versus standalone `e19c64...` | Embedded commit ancestry and behavior unresolved. Do not substitute standalone helpers under the historical converter without a labelled adapter |
| D15 | **Confirmed metadata differences:** benchmark identities | Embedded versus standalone qiskit-bench QFT root/small sizes 6-16 differ; other QV inputs also differ. Full hashes in inventory/manifest; content absent | Matched inputs must be explicitly chosen and hashed after retrieval; filenames alone do not identify original paper inputs |
| D16 | **Confirmed source timing mismatch / caching** | RFT timer excludes synthesis/scoring/offline layout. DasAtom converter times preprocessing/conversion/scoring and can reuse cached logs | Do not infer algorithm speedup from unequal timer scopes; report native and standardized regions separately |
| D17 | **Blocked:** complete sources and dependency lock | Three source recovery attempts fail with WinError 10013; no compiler packages in audit Python | Full smoke, package compatibility and runtime determinism gates remain open. User added network_access=true; active session still restricted, restart needed |

## Scope of counterexamples and negative findings

D04 disproves the expectation that materialization always realizes the
orientation represented in the cost matrix. It does not prove that the paper's
unknown revision had that defect, that any reported gain is false, or that the
result violates gate geometry. D05 disproves interpreting the historical alias
as a measured atom population, but does not establish the physical transfer
sequence absent from logs. D06 does not prove nondeterminism: an implicit
global seed may suffice under tightly controlled order and packages. D08 does
not disprove every historical memory claim; it establishes that this snapshot
uses a different representation and needs its own measurements.

No suspected issue was silently repaired. The patch ledger for `rft_corrected`
is empty. Proposed research heuristics remain deferred. Paper-version evidence,
recent current-head source changes, actual compiled forced-eviction trace,
dependency compatibility, source history, and all benchmark smoke results are
explicitly unresolved.
