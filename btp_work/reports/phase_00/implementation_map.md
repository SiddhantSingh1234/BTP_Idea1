# RFT implementation map and worked example

Scope: pinned RFT `3d1f09233c2acd357fd9fbfad1b5300a921d301a`. The complete
working tree is now recovered and executed, with original upstream bytes preserved.
[inventory.json](../../runs/phase_00/inventory.json) verifies all six
retained files against their saved Git blob hashes and records function anchors.
No applicable `AGENTS.md` was found in the workspace ancestors or `btp_work`;
neither saved upstream tree lists one. Recheck after any recovery.

## Algorithm 1 in plain language

The manuscript first synthesizes a CZ-only routing problem and computes future
interaction information. For each dependency layer it repeatedly schedules a
subset until no gates remain. It tries pairs already within interaction range,
then pairs requiring one endpoint move. A greedy check rejects destination
collisions and interference with accepted gates. Remaining pairs compete for
safe static slots through a distance-sum assignment. Idle atoms occupying active
destinations are evicted toward future partners. Finally, the router realizes
the target map in legal AOD batches and executes that gate subset. The inner
loop serializes gates when there are too few compatible slots.

The interaction radius determines whether a pair may execute. Four cross-pair
distances determine whether two gates may execute together. Individually
addressed CZ gates are assumed; idle neighbors are not treated as involuntary
global-pulse participants. Future transport is predicted, not globally optimized.

## Source-to-code map

Line numbers below refer to the pinned files, not a future checkout. The
[machine-readable anchors](../../runs/phase_00/inventory.json) contain end lines.

| Stage / manuscript connection | Exact source and entry point | Behavior and limitation |
| --- | --- | --- |
| QASM loading and synthesis, p.2 | [runner](../../source_review/upstream_excerpt/NAQC_Compiler/src/benchmark_runner.py#L59), `run_benchmark`, line 59 | `QuantumCircuit.from_qasm_file`; transpile to `cz,h,s,t,rx,ry,rz`, optimization 0; no explicit transpiler seed |
| Remove one-qubit gates | runner `preprocess_circuit`, line 23 | Replace every operation reporting two qubits by a CZ; preserve register size. This discards 1Q semantics and can mishandle two-qubit barriers; see ledger |
| DAG/layers and sparse interaction schedule | [core](../../source_review/upstream_excerpt/NAQC_Compiler/src/compiler_core.py#L111), `analyze_qasm_file`, line 111 | Reload temporary QASM; Qiskit DAG layers; sorted operand pairs; multi-operand nodes become all pair combinations if used directly |
| Offline static layout, III-B | core `sample_max_parallel`, line 150 | Global `random.seed(42)`, randomized trials; best slot count; NumPy distance screening; runner uses 20 trials rather than function default 1000 |
| Busiest layer/canonical map | core `find_busiest_pairs`, line 208; `create_initial_mapping`, line 218 | Runner computes these, but planner never reads either argument; they do not control actual initial placement |
| RFT, III-C/Table I | core `build_right_filled_table`, line 254 | Schedule-derived next occurrence per distinct pair at every timestamp; several partners may appear per qubit; current interactions have distance 0 |
| Planner initialization and temporal loop | core `generate_hardware_instructions`, line 373 | Empty position map, private RNG; future table; each nonempty timestamp repeats over pending pairs |
| Stay/lazy wishlist, Algorithm 1 lines 8-16 | core lines 434-473 | Stay when enabled and within radius; otherwise try q1 toward an empty neighbor of q2 before trying q2 toward q1 |
| Greedy validation, Algorithm 1 lines 17-23 | core lines 475-505 | Stable priority order, destination claims and cross-gate blockade tests; no continuous path check here |
| Static candidates and serialization | core lines 510-556 | Filter static slots against dynamic gates; defer excess logical pairs to next placement batch |
| Hungarian fallback, Eq.5 | core lines 558-644 | CoM subset or all-compatible slots; rectangular SciPy linear sum assignment; both orientations costed; optional future bias already exists; materialization disagrees with matrix orientation |
| Initial placement | core lines 656-698 | First active assignment plus parking all remaining qubits; emit `PLACE`; no shuttle loading cost. Does not use the canonical map |
| Idle retention/eviction, Eq.6 | core lines 700-740; `_pick_idle_position`, line 67 | Keep nonobstructing idle atoms; evict residents of active targets; initial partner cutoff 3 and eviction cutoff 2; absent partner falls back to supplied CoM |
| Router and cycles, p.5 | core `generate_safe_shuttle_instructions`, line 284 | Empty-target moves first; conflict graph enforces row/column equality and order; unseeded maximal independent set; cycles temporarily park one atom at nearest empty grid site |
| Gates, pending-pair update | core lines 750-763 | Emit CZ locations, remove completed pairs; stalled batch writes an error string instead of failing the result |
| Output accounting, Eq.7 | [converter](../../source_review/upstream_excerpt/NAQC_Compiler/src/dasatom_instruction_converter.py#L89), `analyze_converted_instructions`, line 89; `_compute_fidelity_from_counts`, line 46 | Count execute blocks, nonempty shuttle blocks, atom moves and sum of batch maxima; apply historical fidelity formula |
| DasAtom adapter | converter `convert_dasatom_to_instructions`, line 154 | Calls `CreateCircuitFromQASM`, `get_2q_gates_list`, `gates_list_to_QC`, grid generation, DAG partitioning, embeddings, `QuantumRouter.run`, parallel gate grouping. Definitions are missing locally; invocation audit only |

The planner docstring promises a full-revert fallback, but the retained body
only defers excess pairs. `GridCapacityError` exists without a corresponding
raise in this planner. Errors in strings are not an independent success check.

## Captured full-compiler four-qubit trace (28 October update)

The same four-qubit QASM was run through the **unmodified full planner**, using
the existing ladder6 configuration, grid 3x3, r_int=1, r_blk=2 and declared static
slots A=[(0,0),(0,1)], B=[(2,0),(2,1)]. No decision was injected or function
patched. Python tracing captured cost matrices, candidates, targets, RFT entries,
parking decisions and router calls/returns in
[trace.json](../../runs/phase_00/compiled_fixture_01/trace.json).
The [actual instructions](../../runs/phase_00/compiled_fixture_01/instructions.txt)
supersede the conditional hand example below as evidence of observed behavior.

| Layer | Observed placements / movements / gates |
| --- | --- |
| T1 | Free initial map q0=(2,1), q1=(2,0), q2=(0,1), q3=(0,0); execute (0,1) and (2,3) |
| T2 | Assign active q0->(0,1), q2->(0,0). Evict q3, which has no future partner, to CoM-nearest (1,1). Route singleton batches q3: (0,0)->(1,1), q2: (0,1)->(0,0), q0: (2,1)->(0,1). Execute (0,2) |
| T3 | Assign q1->(0,0), q2->(0,1). Evict q0, also with no future partner, to (1,0). Route q0: (0,1)->(1,0), q2: (0,0)->(0,1), q1: (2,0)->(0,0). Execute (1,2) |

The actual RFT table is retained in the trace and agrees with the table below.
The run has four CZ gates, three execution cycles, two forced evictions and six
movement batches/atom moves. D=26.48528137423857 um, transfer alias=24,
T=528.7550570440701 us, idle=2114.22022817628 us and legacy F=0.9787689724998074.
The boundary replay passes gate multiset/dependency, occupancy and gate geometry
checks. It does not establish continuous path/transfer/timing validity. The
observed initial map differs from the hand example because real candidate and
orientation/tie choices are now captured rather than prescribed.

## Conditional analytic example retained from the pre-recovery audit

This is a **hand-worked conditional trace**, not a captured compiler run. Its
[QASM fixture](../../benchmarks/phase_00/four_qubit_hand_trace.qasm) has CZ layers
`T1=[(0,1),(2,3)]`, `T2=[(0,2)]`, `T3=[(1,2)]`. The third gate layer follows the
second because both use q2. It uses the already existing ladder6 option (stay
on, lazy endpoint moves off), a 3x3 grid, interaction radius 1, restriction
radius 2, and static slots A=`[(0,0),(0,1)]`, B=`[(2,0),(2,1)]`. Both gates at T1
are compatible: their minimum cross-distance is 2. This is a controlled
illustration, not the selected ladder7 production control.

The code's RFT for these specified layers is:

| Qubit | T1 partner/distance entries | T2 | T3 |
| --- | --- | --- | --- |
| q0 | (1,0), (2,1) | (2,0) | empty |
| q1 | (0,0), (2,2) | (2,1) | (2,0) |
| q2 | (3,0), (0,1), (1,2) | (0,0), (1,1) | (1,0) |
| q3 | (2,0) | empty | empty |

Entry order follows first appearance of distinct pairs; sorting by distance
chooses the earliest partner when parking. These rows are not a next-k-event
list, and the general repeated-partner counterexample is tested separately.

1. At T1, choose orientation q0->(0,0), q1->(0,1), q2->(2,0), q3->(2,1).
   Emit four `PLACE` records, then execute CZ(0,1) and CZ(2,3). Placement is free
   in the legacy in-circuit score; it is a prescribed prepared initial state.
2. At T2, the active positions q0=(0,0), q2=(2,0) give CoM=(1,0). Both static
   slots tie as CoM candidates and at minimum distance-sum `sqrt(5)`. Condition
   the example on selecting A and materializing q0->(0,0), q2->(0,1). q1 at
   (0,1) must be evicted. q3 stays at (2,1). The available sites are (0,2),
   (1,0), (1,1), (1,2), (2,0), (2,2). q1's next partner q2 has target (0,1)
   and distance 1. The legacy sum score is 2 for both (0,2) and (1,1); condition
   the example on parking at (1,1). Neither tie decision has been attributed
   to an uninstalled SciPy/networkx version.
3. The router must first move q1 (0,1)->(1,1), because q2's destination is
   occupied. Then move q2 (2,0)->(0,1). Each clear-move graph has one vertex,
   so the independent set is uniquely determined. The two movement lengths
   are 1 and sqrt(5) grid units. Execute CZ(0,2).
4. The T2 final map is `{0:(0,0), 1:(1,1), 2:(0,1), 3:(2,1)}`. At T3 q1 and
   q2 are already adjacent; stay and execute CZ(1,2). q3 has no future partner
   after T1 and stays idle. Separately, the tested no-partner parking rule
   chooses the vacancy nearest the supplied active-mover CoM, which can differ
   from the manuscript's geometric array center.

The [hand-specified instruction stream](../../benchmarks/phase_00/four_qubit_hand_trace.txt)
is parsed by the actual legacy parser and checked with a separate small
boundary replay in `audit_phase00.py`. It contains four CZ gates, three execute
cycles, two movement batches and two atom-move events. Each moved target is
empty at its boundary; gate distances and the two-gate cross-distance are
checked. Continuous trajectory clearance, trap transfers, and QASM simulation
are **not** validated by this fixture.

At 3 micrometres per grid unit, sum of batch maximum distances is
`3*(1+sqrt(5)) = 9.70820393249937 um`. Historical transfer alias is `4*2=8`.
Movement time is `160 + 9.70820393249937/0.55 us`; total time adds `3*0.2 us`
and equals `178.25127987727157 us`. Idle time is `4*T-4*0.2 = 712.2051195090863 us`.
Legacy fidelity is `0.995^4*exp(-idle/1.5e6) = 0.9796842327609727`.
The historical `Realistic` diagnostic multiplies by `0.999^8`, yielding
`0.9718741352636082`. These are scores of the declared fixture, not measured
RFT outputs or physical-state fidelities.

For initial placement, all atoms of the first successful batch are considered
prepared at their targets; `PLACE` records incur neither movement nor transfers.
Later placement batches in that same logical layer use the router and are
charged. A qubit with no interactions at all has no initial placement if the
entire circuit is skipped. An explicit loader/no-gate policy belongs in a
separate adapter, without rewriting historical counts.
