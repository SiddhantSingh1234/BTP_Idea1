# Source review and implications for execution

Reviewed 26 October 2026. This is a planning review of relevant methods, assumptions, and evaluation sections, not a claim that the code was executed or every figure independently reconstructed. PDF page numbers below are the extraction's `=== PDF PAGE n ===` markers. The original PDFs remain authoritative when extraction is ambiguous.

## Source inventory

| ID | Local source | Relevant material | Consequence for this project |
| --- | --- | --- | --- |
| P | [Proposal source](../../Proposal/BTP_Research_Proposal.tex) and [PDF](../../Proposal/BTP_Research_Proposal.pdf) | Idea 1, Idea 2, reduced Idea 5, and My Choice | Defines four required contributions and the intended order; full Ideas 3–5 are not added to scope |
| R | [RFT manuscript](../../Papers/Priyanshu_Aditya_ISVLSI2026_AK_O.pdf), 6 pages | pp. 2–5, Algorithm 1, Eqs. 1–7; p. 6 Table II and Fig. 4 | Baseline tiered planner, one-partner RFT description, offline layout, sum-distance matching, ideal transport evaluation |
| D | [DasAtom](../../Papers/3_DasAtom_A_Divide-and-Shuttle_Atom_Approach_to_Quantum_Circuit_Transformation.pdf), 13 pages | pp. 5–7 algorithms and fidelity Eqs. 3–5; p. 12 limitations | Primary comparison; exact historical idle convention; future Idea 2 uses alternative subcircuit embeddings |
| A | [Atomique](../../Papers/4_ISCA59077.2024.00030.pdf), 17 pages | pp. 6–7 Section IV, Eqs. 1–2, loss/cooling expressions and Table I; p. 11 sensitivity | Heating affects gate fidelity as well as loss; loss is evaluated across movements; cooling uses a prepared spare array |
| Z | [ZAP](../../Papers/2_ZAP_Zoned_Architecture_and_Performant_Compiler_for_Field-Programmable_Atom_Array.pdf), 19 pages | p. 5 Eqs. 4–5; pp. 7–9 placement/routing; pp. 15–16 cost/ablation | Acceleration-limited timing; negative-log accounting and committed-move conflict heuristic; zoned/global hardware must stay distinct |
| E | [Enola](../../Papers/5_3658617.3697778.pdf), 9 pages | Scheduling/placement/routing sections; Section 8 future directions | Explicitly distinguishes Euclidean placement quality from move compatibility; stage guarantee does not imply optimal physical makespan |
| S | [Schmid review](../../Papers/6_Schmid_2024_Quantum_Sci._Technol._9_033001.pdf), 37 PDF pages | Hardware constraints, figures of merit, case studies, Section 7 | Hardware-dependent tradeoffs; analytical success probability is a proxy, not full state fidelity |
| M | [Device-model paper](../../Papers/1_2607.20616v2.pdf), 7 pages | pp. 4–6 Sections IV–V | Explicit coordinates, units, geometry, capabilities, and movement properties; use a lightweight profile, not a full QDMI implementation |
| G | [Existing study guide](../../Papers/NEUTRAL_ATOM_PAPERS_STUDY_GUIDE_AND_RESEARCH_GAPS.md) | Sections 5–14 | Secondary navigation/context; its summaries are not substitutes for checking primary equations or implementations |

The proposal and all seven PDFs were extracted locally; checksums and link annotations are in [manifest.json](manifest.json). A blank review cover page and rotated content may not extract. Equations, plots, and table entries used numerically must be checked visually against the PDFs during implementation/reproduction. `Intern_Report` is excluded.

## Public code checked

The paper's wrapped URL resolves to **[ipash185/NAQC_Compiler](https://github.com/ipash185/NAQC_Compiler)**, using an underscore. GitHub API metadata and selected raw files were retrieved successfully even when browser retrieval failed.

| Repository | Pinned observed revision | What was checked |
| --- | --- | --- |
| [RFT code](https://github.com/ipash185/NAQC_Compiler/tree/3d1f09233c2acd357fd9fbfad1b5300a921d301a) | `3d1f09233c2acd357fd9fbfad1b5300a921d301a` | Tree, README, requirements, license, compiler core, runner, DasAtom converter |
| [DasAtom](https://github.com/Huangyunqi/DasAtom/tree/73a6bdf0fd200b2733745211eaf2e0c1e17f496a) | `73a6bdf0fd200b2733745211eaf2e0c1e17f496a` | Repository metadata/tree and public usage instructions; its complete algorithm implementation was not audited here |

The incomplete RFT excerpt is in `upstream_excerpt/NAQC_Compiler/`, with its upstream license. No compiler dependencies were installed and no quantum benchmarks were run. These revisions are reference anchors, not proof of the manuscript revision.

## Implementation observations the first agent must resolve

Line references refer to the frozen excerpt, not a future branch.

1. `src/compiler_core.py:36` defines `CompilerOptions`; `src/benchmark_runner.py:114` defines eight ladder variants. The repository already exposes CoM/all-compatible slots, RFT parking, keep-adjacent and one-endpoint moves, and alternative eviction. Existing switches should be reused where possible.
2. `compiler_core.py:254` builds a sparse schedule-derived table containing next occurrences **per interacting pair**, and can append several partner entries per qubit. The manuscript describes one next partner per qubit. This is not yet a next-k-events table: repeated future events with the same partner are not all retained.
3. `_pick_idle_position` at line 67 uses a current-distance-plus-partner-distance score by default, with a bounded future-distance filter and fallback. An option uses pure partner distance for evicted qubits. The manuscript's Eq. 6 describes pure future-partner distance. Determine which configuration generated the paper.
4. An optional future-biased Hungarian score already exists. Therefore “adding future information to Hungarian” alone is not a new contribution against this snapshot. The proposed next-k events, model-aware costs, bottleneck objective, and validated repair must be distinguished from existing work.
5. At lines 577–645, matrix construction minimizes a cost over both pair orientations, but assignment materialization compares only the first endpoint's distances. This suggests a possible cost/materialization mismatch. Reproduce it with an adversarial pair before calling it a bug. If confirmed, fix it only in an explicitly corrected baseline and downstream variants.
6. `generate_safe_shuttle_instructions` calls `networkx.maximal_independent_set` without an explicit seed argument. Combined with global random seeding elsewhere, ordering and random-state consumption need an end-to-end determinism audit. A seed field in options does not establish independent reproducible runs.
7. The benchmark runner uses `temp_preprocessed.qasm` in its working directory. Concurrent runs need isolated working directories or an adapter; otherwise run processes can overwrite the same temporary file.
8. The existing converter's “Realistic” metric changes transfer fidelity but does not implement Atomique heating/loss/cooling or acceleration timing. Preserve its historical label in reproduced CSVs, but do not confuse it with the new complete movement model.
9. The converter uses a four-transfer factor based on movement-operation counts. The meaning of a movement operation and whether this is an error-event count, a timed transfer stage, or both must be traced. The new evaluator requires explicit per-atom transfer events and resource-aware timing.
10. The paper's preprocessing memory claim and its stated dense interaction tensor differ from the sparse structure in this snapshot. Measure the chosen revision; do not inherit either a memory number or asymptotic claim without checking representation.

## Required scientific clarifications

### C1: Legacy equivalence must be an actual mode

For k=1, multiplying a single pure distance by a positive discount does not change the minimizer. That fact alone does not reproduce a code path with a different distance term, candidate filter, future cutoff, partner-position estimate, or tie-breaking. Preserve a `legacy_exact` branch and compare schedules exactly under controlled seeds. Test the generalized formula's k=1 mode as a separate variant if it differs.

### C2: Heating is not represented only by a final loss probability

The proposal's displayed error sum has no explicit heating-induced gate-error term. Atomique Section IV includes one. It also accumulates survival factors for moved atoms over movement events, rather than charging only each qubit's final vibrational state. Phase 03 must specify event ordering and avoid counting a cumulative loss twice.

### C3: Cooling is architecture-dependent and counted per affected atom

Atomique cools an entire AOD array by moving its quantum information to a prepared cold array, at two CZ gates per atom. If `N_cool` counts array-wide episodes, the proposal's `2*N_cool*epsilon_CZ` undercounts the operation cost; use the number of cooled atom-events or explicitly sum episode populations. Include duration, transfers, occupancy, and state handoff. RFT's single-AOD device does not automatically support this primitive.

### C4: Acceleration and trajectory smoothness must agree

ZAP's `2*sqrt(d/a)` is for a symmetric acceleration/deceleration profile. Atomique's heating expression uses a specific smooth constant-negative-jerk profile. Combining their formulae without checking the same trajectory is a modelling assumption, not a derived physical model. Specify an executable compatible trajectory or label the combined model as an approximate surrogate and sweep its uncertainty. Under a triangular acceleration profile, intermediate positions use normalized progress, not generally linear time interpolation.

### C5: Preserve historical decoherence separately

DasAtom Eq. 4 uses `n*T - m*t_CZ`. A sum of each qubit's non-gate exposure would usually subtract both CZ participants' active intervals. The appropriate new convention also depends on whether moving atoms decohere. Keep the historical expression for reproduction; define and justify the extended per-qubit exposure separately. ZAP's wording about idle intervals is not interchangeable with Atomique's movement decoherence.

### C6: Fixed assignment costs cannot encode all mutual conflicts

The proposal's conflict term counts conflicts against committed moves. Costs must be frozen while running a linear assignment. Conflicts among as-yet unassigned moves are pairwise dependent and are not exactly represented by those entries. Validate actual routing afterward. A threshold on composite cost optimizes the maximum composite score, not necessarily the maximum physical movement time or the sum of actual routed batch durations.

### C7: Complexity needs unambiguous dimensions

Use `h` for lookahead length, `m` for unresolved **logical pairs**, and `s` for candidate interaction slots. The proposal reuses k for lookahead and movers. Square `O(m^3 log m)` matching estimates do not by themselves cover rectangular candidate expansion, cost construction, event prediction, conflict rebuilding, or repair rerouting. Retain polynomial/bounded design but derive actual costs.

### C8: A shared scorer does not equal matched hardware

RFT/DasAtom use individual addressing, Enola global DPQA, Atomique multiple arrays, and ZAP zones/global illumination. Identical scoring constants do not make unsupported schedules legal on the same device. Compare capabilities before ranking algorithms, and preserve separate hardware tracks when they cannot be matched.

## Mapping proposal requirements to phases

| Proposal requirement | Phase(s) | Required evidence |
| --- | --- | --- |
| Reproduce RFT and understand implementation | 00–01 | Provenance, worked trace, published-result ledger |
| Realistic model and error budgets | 02–03 | Explicit event semantics, source-backed profiles, limiting-case checks |
| k = 1, 2, 4, 8 future interaction events | 04 | Event oracle, exact legacy branch, k/runtime/error results |
| Composite and bottleneck assignment | 05 | Frozen oriented costs, exact tiny matching oracle, routing comparison |
| Bounded repair | 06 | Actual accepted improvements, rollback, bounded work |
| QFT/QTetris/QAOA/QV; RFT/DasAtom/additional baseline | 07 | Frozen manifests, matched-capability matrix, full outcomes |
| Ablations, parameter sweeps, Pareto fronts | 07–08 | Isolated controls and uncertainty/coverage tables |
| Reduced validator/unified model from Idea 5 | 02–03 and 07 | Two primary adapters, independent checker and shared scorer |
| Report, reusable artifacts, then Idea 2 | 09–10 | Research release and separate transition brief |
