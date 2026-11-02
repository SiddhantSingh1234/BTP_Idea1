# Phase 00 baseline specification

Owner: Codex `/root`, updated 28 October 2026. **The snapshot is runnable in a
tested pinned environment; exact-paper identity remains unresolved.** No proposed
lookahead, movement-noise, assignment, or repair heuristic was implemented.

## Recovered executable controls — current specification

The authoritative current configs are in `configs/baselines`; pre-recovery
versions are preserved under `reports/phase_00/configs_before_recovery`.
Full source trees (512 RFT files, 499 standalone DasAtom files) are verified in
`runs/phase_00/verified_source_trees.json`. The environment is CPython 3.13.2 with
the hash lock at `configs/environment/requirements-py313-win64.lock`.
The selected RFT control remains unmodified ladder7; its actual six-slot 11x11
layout is frozen in its JSON config. Standalone DasAtom is run with explicit
11x11/r_int=2/r_restr=4 geometry, global seed 42 and native MIS seed 0, without
cached embeddings. This is an API adapter control with a separately labelled
timer; the native main program defaults to ceil(sqrt(N)) geometry.

Both compilers pass QFT5 on identical normalized input (26 CZs, N=5). RFT also
passes Table II `4mod5-v1_22` (11 CZs, declared N=16). DasAtom's helper derives
N=max(two-qubit operand)+1=5 and omits trailing inactive qubits on that case.
Its native five-qubit trace and score pass their declared scope; a full-register
16-qubit matched schedule is explicitly unsupported. No idle atoms were silently
invented, and no preprocessing/heuristic fix was applied. Preserve native N and
declared N as separate fields during Phase 01; record this case as unmatched
under a full-register comparison. The earlier adapter equality assertion
failures are retained as attempts 01/02; attempts 03/04 handle the discrepancy
explicitly without changing compiler behavior.

The recovered `CreateCircuitFromQASM` uses a custom phase-gate QASM instruction,
transpiles at optimization 0 only when its gate-name set exceeds the allowed
basis, then `get_2q_gates_list` retains all two-qubit instructions. The shared
smoke adapter feeds it the same frozen CZ-only QASM as RFT. Neither path's
route-only skeleton preserves the original full-unitary semantics by itself.
The manifest now records raw SHA-256 for every inventoried source circuit and
normalized hashes/counts for both actual smoke inputs. Other normalized hashes
remain pending Phase 01; paper-version input identities are still unknown.

Each RFT case and DasAtom case has two fresh-process repeats with identical
normalized inputs, complete instruction bytes, counts and shared scores. The
known global/private RNG and ordering sources remain documented below; this
demonstrates repeatability for these controls/cases, not every possible circuit.

Public history retrieval returned all 27 commits reachable from pinned main;
current main is still the pinned revision and there are no tags. The May 15,
2026 sparse-schedule refactor explains the manuscript/current representation
difference; a December 18, 2025 commit added pure-partner eviction/future bias.
An October 27, 2025 commit message already describes multi-layer weighted
lookahead. This is additional overlap evidence, not proof of an implemented
next-h-event method or a manuscript revision. The recovered QFT plot explicitly
filters multiples of five from 5 to 60; the QFT table script selects ladder8
CSV names. Neither script plus absent raw CSVs proves which code/options
generated the manuscript. Historical GitHub responses are in
`runs/phase_00/history_01`; `paper_revision_unresolved` remains the disposition.

Embedded versus standalone helper/router diffs are now inspected: differences
are progress printing and the loop variables supporting it, with no observed
planner-rule change. Their blob identities remain distinct and timed printing
can matter. None of the seven upstream helper-changing versions inspected
matches the embedded helper blob exactly. See `embedded_dasatom.diff`; do not
invent an exact embedded source commit. Actual imported module paths are
recorded for every smoke run.

The remaining sections preserve the initial audit and scientific contracts;
their pre-recovery availability statements are superseded by this section and
the current executable JSON configs. No corrected baseline has been implemented.

## Controls and provenance

| Control | Selected identity | Evidence / disposition |
| --- | --- | --- |
| `rft_paper` | Revision and exact options unknown | `paper_revision_unresolved`; [config](../../configs/baselines/rft_paper.json) deliberately leaves them null |
| `rft_snapshot` | RFT `3d1f09233c2acd357fd9fbfad1b5300a921d301a`, ladder7 `7_dynamic_slot_01q_move` | [Resolved source options](../../configs/baselines/rft_snapshot.json); current dataclass defaults equal ladder7 apart from name. Full sources/environment unavailable |
| Paper-like candidate | Existing ladder8 `8_optimized_eviction` | Pure partner-distance eviction resembles Eq.6 more closely, but its cutoff, anchors and RFT representation still differ. Not identified as the paper control |
| `rft_corrected` | Not implemented; parent would be pinned snapshot | [Specification](../../configs/baselines/rft_corrected.json); no corrected revision or applied patch exists |
| `dasatom_standalone_snapshot` | `73a6bdf0fd200b2733745211eaf2e0c1e17f496a` | [Specification](../../configs/baselines/dasatom_snapshot.json); saved tree only, no executable source |
| RFT embedded DasAtom | Files embedded in the RFT revision | Distinct source identity. Main script matches standalone; helpers/router and some QFT inputs differ |

The RFT license is MIT and the retained license is unchanged. The embedded
DasAtom has its own license entry; standalone's public repository identifies
BSD-3-Clause. Full license files must be recovered with the source archives.
No Git checkout/history, author-supported tag, or paper artifact bundle has
been recovered. The supplied six-file excerpt is not reclassified as a checkout.

## Published configuration ledger

All revision/variant assignments below remain unresolved. Values explicitly
printed in the manuscript are distinguished from defaults found in the snapshot.

| Published item | Established by manuscript | Missing evidence / next action |
| --- | --- | --- |
| Fig.1 preprocessing | QASM/DAG, interaction representation, RFT, planner | Historical dense versus current sparse code identity; inspect Git history |
| Algorithm 1 | Tiered stay/lazy, global assignment, eviction, serialization | Exact options, initial-map behavior, ties, and historical router implementation |
| Fig.2 / Table I | Four-qubit example, three declared time layers, per-qubit next-partner explanation | Original example circuit and original table-builder revision; retained code has per-pair entries |
| Fig.3 | Future-partner-oriented eviction illustration | Whether pure partner or sum-distance scoring, cutoff and fallback generated results |
| Eq.7 / results, p.5 | Python 3.13.2; i5 eighth-generation/8 GB; T2=1.5 s, fCZ=0.995, ideal transfers; individual CZ addressing | Dependency lock, exact idle convention implementation, transfer duration, speed and spacing used for each original run |
| Fig.4(a-d), p.6 | QFT range 5-60, grids 11x11 / 20x20 / 35x35; compilation/runtime/moves/fidelity | Exact sampled sizes, original QFT bytes, final swaps/precision, selected ladder variant, layouts, seeds, raw data, timed scope. README mentions step-5 circuits, which is only a hint |
| Table II, p.6 | 15 named QTetris circuits; grids 11x11 / 35x35; both methods' compilation times, fidelities and movement counts | Original normalized inputs, variant, same hardware/grid handling in DasAtom, seeds, timings and raw rows |

The snapshot tree lists plotting/table scripts but retains no CSV/XLSX result
files. Those scripts were not downloaded; their settings and Git history remain
unread. README examples name variants 9-11 although the actual pinned runner
defines only variants 1-8. That inconsistency cannot establish a historical
version. No author was contacted. Smallest remedy for paper identity is a
matching source commit plus configuration, input and raw-result provenance;
successful snapshot runs alone will not resolve it.

## Selected snapshot options and timing

The selected existing ladder7 has keep-adjacent and one-endpoint relocation on,
CoM-subset candidates, Hungarian sum-distance assignment, RFT-greedy idle
parking, pure-partner eviction off, future-biased assignment off, bias weight
0.3 and maximum time distance 3 (inactive while bias is off), seed 42, and square
padding off. No parameter has been tuned against a published result.

For the first runnable smoke use the source-default 11x11 grid, interaction
radius 2 grid units and restriction radius 4. Those are snapshot defaults, not
proof that every paper run used them. At spacing 3 um they correspond to 6 um
and 12 um. The runner uses 20 layout trials and resets the global Python RNG to
42 inside the sampler. Layout generation occurs outside the timed region.

The RFT runner timer starts after initial QASM parsing, transpilation, 1Q
removal and temporary-file writing. It includes the second QASM load, DAG/layer
construction, busiest-layer/canonical-map work, RFT, planning and routing. It
stops before temporary-file deletion, metric calculation and log/CSV writing.
The first sorted circuit is warmed up once using the first selected variant.
Record offline, preprocessing, upstream timed region and end-to-end costs
separately. The converter's DasAtom timer includes repeated preprocessing,
conversion and scoring, and can reuse cached instruction files. These timer
scopes cannot be compared as equivalent without an explicitly labelled adapter.

## Input normalization and identities

RFT: OpenQASM 2 input -> Qiskit transpile to `cz,h,s,t,rx,ry,rz`, optimization 0
-> retain every operation whose `num_qubits == 2`, replacing it with CZ -> dump
temporary QASM -> reload -> DAG layers -> lexicographically sorted operand pairs.
No transpiler seed is supplied. The full register size is retained. One-qubit
gates are intentionally absent from the route-only benchmark, so the output is
not a unitary-equivalent replacement for the complete original circuit.

Two-qubit barriers/non-CZ instructions need explicit accounting; do not silently
change historical preprocessing to match expectations. Record raw QASM SHA-256,
normalized QASM SHA-256, Qiskit version, synthesis recipe, qubit count, CZ count
and layer count for every successful run. If a corrected normalizer is needed,
preserve historical normalization as a separate control.

DasAtom: the retained converter exposes the call chain, but the definitions of
`CreateCircuitFromQASM` and `get_2q_gates_list` are missing. Equivalent synthesis,
inactive-qubit treatment and exact CZ ordering are therefore unverified. Both
methods must consume one declared normalized CZ input for matched comparisons;
historical native preprocessing remains separately reproducible.

[reproduction_manifest.json](../../configs/benchmarks/reproduction_manifest.json)
lists all 15 Table II filenames and 56 available QFT *candidate* filenames
between 5 and 60, with embedded and standalone Git blob SHA-1 identities from
the saved trees. It does not assert that every candidate was plotted. Actual
file content, SHA-256, normalized hashes, counts, QFT final-swap conventions and
exact sampled sizes remain null. The root/small QFT files for sizes 6-16 differ
between embedded and standalone snapshots; never substitute one silently.
`Data/Q_Tetris/qft_16.qasm` is a separate identity from the qiskit-bench QFT file.
The small intended smokes are `qft_5` and `4mod5-v1_22`; neither is locally present.

## Historical output accounting

The legacy parser counts nonempty `[SHUTTLING]` blocks as movement operations B,
`SHUTTLE` records as atom-move events, and `[EXECUTE` blocks as gate cycles H.
Its distance D is the sum of maximum physical distances per movement block,
not total atom distance. Loading/initial placement is free. It calculates:

```text
t_move = 4*B*20 us + D/(0.55 um/us)
T = H*0.2 us + t_move
T_idle = N*T - G_CZ*0.2 us
s_alias = 4*B
F_legacy = exp(-T_idle/1.5e6 us) * 0.995^G_CZ
F_diagnostic_realistic = F_legacy * 0.999^s_alias
```

`Num Transferred Qubits` is the historical alias `s_alias`; it is not a unique
population or explicit per-atom event count. The `Realistic` label changes
transfer fidelity only; it has no heating, motion loss, cooling or acceleration.
Do not reinterpret these CSV fields as the Phase 02 event schema. Preserve the
historical `N*T-G*tCZ` subtraction separately from any later per-qubit exposure
integral. These are approximate independent-error scores, not state fidelity.

## Repeatability and exceptional inputs

Choose fresh processes, isolated working directories, numeric thread counts 1
and `PYTHONHASHSEED=0` for new controlled snapshot experiments. Record ordered
inputs, exact frozen layout, package versions, Python private/global random
states, and the warmup policy. This is a new repetition policy, not a claim
about unknown historical settings. Do not change historical router calls while
calling the run an untouched reproduction.

Known RFT randomness includes global sampler seeding/shuffle/choice, the options'
private Random(42), and networkx MIS with omitted explicit seed. Warmup and
prior routing calls consume global state. Candidate sites and some qubit sets
become unsorted lists; ties depend on enumeration/package behavior. Qiskit's
unseeded transpilation and the absent DasAtom/rustworkx/router implementation
require a complete audit after recovery. Byte-identical isolated tests do not
establish compiler determinism.

Inactive-only inputs: the upstream runner returns no result; an empty schedule
does not initialize qubits. Future adapters must emit an explicit skipped/
unsupported outcome with original N, rather than inserting a fabricated route.
Capacity: serialization handles excess concurrent pairs only when at least one
slot exists. More qubits than sites, zero slots, and full-occupancy cycles do
not have a reliable error-result contract. Reject incomplete schedules before
scoring in a future adapter; keep raw upstream failures. Do not enlarge a grid
without recording it. The converter may extend its grid based on embeddings;
actual geometry must be reported, not assumed from requested dimensions.

## Correctness patch ledger

No upstream file was modified and no corrected baseline was created. Proposed
repairs requiring later implementation/validation are: store and materialize
the orientation minimizing the same matrix entry (including optional bias),
and reject missing-gate/capacity/router-error outputs. Deterministic wrappers
and temporary-file isolation are reproducibility changes and need their own
revision. None of these is evidence for the four proposed research gains.

## Scientific clarifications C1-C8: ownership and resolution plan

| ID | Owner | Resolution contract / next acceptance evidence |
| --- | --- | --- |
| C1 legacy equivalence | Phase 00 baseline owner, then Phase 04 lookahead owner | Freeze current cutoff/anchor/tie behavior and preserve an exact legacy branch; compare decisions/movements against generalized h=1, including repeated partners. Paper identity still unknown |
| C2 heating gate errors/loss cadence | Phase 03 model owner | Include separate heating-induced gate penalties and moved-atom survival per event; verify Atomique IV equations visually and use limiting cases; no final-only cumulative-loss shortcut |
| C3 cooling population/resources | Phase 03 model owner | Default single-AOD control has no supported spare-array cooling primitive. Separate no-cooling/resource-enabled profiles; account two CZ per cooled atom-event, transfers, duration and state handoff |
| C4 trajectory consistency | Phase 03 model owner | Resolve compatible trajectory for acceleration timing and smooth-jerk heating or label a surrogate and sensitivity range; specify interpolation and units |
| C5 decoherence convention | Phase 00/01 historical owner, Phase 03 extended owner | Preserve DasAtom Eq.4 exactly for legacy; independently justify new per-qubit exposure including transport without double-counting |
| C6 fixed versus mutual conflict | Phase 05 assignment owner | Freeze committed-move costs during assignment, orient pair endpoints consistently, and route/replay the result; composite bottleneck is not automatically physical makespan minimization |
| C7 dimensions and complexity | Phase 00 audit owner, then Phases 04-06 implementers | Use N,L,h,m logical pairs,s slots,A atoms,B routing batches. Derive rectangular cost construction and routing/repair work; measure memory after runtime recovery |
| C8 hardware matching | Phase 02 profile owner and Phase 07 experiments owner | Capability matrix for addressing, arrays, spacing/radii, overlaps and cooling before ranking; incompatible architectures get separate studies |

For C7, the retained schedule stores O(G) gate-pair entries plus layer overhead.
With P distinct interacting pairs and K maximum occurrences of a pair, the RFT
builder creates N*L empty lists and can retain O(P*L) partner tuples; its
pair/timestamp bisect work is O(G + P*L*log(K+1)), with O(G + N*L + P*L) space
in the worst case. Python-object overhead is not the manuscript's dense numeric
tensor size. Assignment stores an m-by-s matrix with several distance/bias
temporaries; conflict graphs can have quadratic edges in moving atoms. Static
layout work depends on grid area, radius and trial count. No measured peak-RSS,
67 MB claim, or complete end-to-end polynomial bound has been validated here.

## Primary-source reading and bounded overlap review

Read the proposal Idea 1 and My Choice, RFT pp.2-6/Algorithm 1/Table II, and the
listed primary method/evaluation sections through the preserved extracts.
[Source manifest](../../source_review/manifest.json) identifies the authoritative
PDFs and checksums; [source review](../../source_review/SOURCE_REVIEW.md) links
them. All eight PDF hashes remain unchanged. No internship report was read.
No new quantitative heating model is inferred from distorted extracted equations;
visual equation/unit verification remains required in Phase 03.

| Primary material read | Consequence recorded here |
| --- | --- |
| RFT pp.2-6 | Tiered planner, next-partner narrative, distance-sum Eq.5, pure-partner Eq.6, ideal Eq.7, grid/circuit targets and historical Python |
| DasAtom pp.5-7 and 12 | CZ-only normalization convention, VF2 division/embeddings, order-compatible moves/MIS, Eq.3-5 score, independently addressed architecture and embedding-transition limitation |
| Atomique pp.6-7 / IV, Table I | Heating changes gate errors as well as survival; smooth jerk differs from triangular acceleration; array-wide spare-array cooling costs depend on population |
| ZAP pp.5 and 7-9, evaluation/ablation context | Acceleration timing, next reuse/negative-log placement costs, committed-vector routing conflicts and parking already exist; zoned/global hardware differs |
| Enola pp.3-4 and 8 | Decaying weights consider future gates; Euclidean placement omits compatibility; near-optimal stage counts do not prove minimum physical makespan; simultaneous transfer duration differs from atom-event count |
| Schmid review hardware/figures-of-merit sections, Eq.13-15, shuttling cases and outlook | Success probability is a proxy and hardware-specific transport/coherence tradeoffs alter preferred routing |
| Device-model paper pp.4-6 / IV-V | Coordinates, scale units, operation capabilities, minimum separation and zones need explicit profiles; no full QDMI integration is required |

Bounded update on 27 October 2026 used primary papers and inspected snapshot
features. The new papers below do not establish hardware equivalence or prove
that a proposed RFT extension has already been implemented elsewhere.

| Proposed step | Existing overlap | Distinct work still to establish |
| --- | --- | --- |
| Realistic movement/error model | Atomique already models heating/loss/cooling; ZAP uses acceleration timing; snapshot diagnostic adds transfer infidelity | Compatible event-level adaptation to this individual-addressing baseline, explicit limitations and controlled rescoring; not invention of those physical laws |
| Next-k interaction events | Snapshot retains multiple partners and optional future-biased assignment; Enola weights many future gates | Ordered repeated interaction events, exact legacy control, supported scaling and controlled benefit; cannot claim nobody uses several future interactions |
| Bottleneck/conflict assignment | ZAP already uses committed-vector compatibility; future assignment information is already optional in RFT | Oriented bottleneck/composite matching with independent oracle and actual routed objective; no general first-use claim |
| Bounded repair | Existing router handles cycles; ZAP parking resolves conflicts | Scored, budgeted reassignment with replay and rollback; current cycle parking is not that contribution |

The recent [ARGON primary paper](https://arxiv.org/html/2607.21216v1), Sections
3.1-3.3, uses offline layouts, future interaction edges, and discounted rollout
costs for a learned placement policy. This directly limits broad claims that
multi-step future routing information is absent from prior work. A lightweight
explicit event table and validated bottleneck/repair approach would need a
specific comparison; their novelty is not established by this audit.

[Practical Insights into Fair Comparison](https://arxiv.org/html/2604.25478v1),
Sections III and III-F, presents a common routed/scheduled representation and
compiler adapters, and discusses normalization/accounting defects. Thus the
reduced validator/shared evaluator is evaluation infrastructure, not presumed
novel by itself. Its conclusions do not replace this project's native-hardware
checks or license different architectures as matched.

[PAC](https://arxiv.org/html/2505.13049v1), Sections 3.2-3.3, partitions hardware
and circuits for parallel compilation. It is adjacent scalability work; it does
not establish the proposed repeated-event, bottleneck assignment or replay-based
repair method. This bounded check found no basis for an automatic scope switch.
Revisit precise contribution claims before Phases 04-06 and during Phase 08.
Current upstream RFT beyond the saved snapshot could not be retrieved, so the
current-head overlap check remains unresolved.
