# Complexity, measured costs and scalability interpretation

Use distinct symbols: N logical qubits, Q normalized CZ gates, S grid sites, P placement transitions, D parking calls, h event horizon, F available parking sites, m unresolved pairs, c candidate columns, A assignment solves, B permitted complete repair trials, and J emitted physical events. S and Q must not both be called G in the final presentation.

| Component | Time bound / dominant work | Storage boundary | Measured evidence |
| --- | --- | --- | --- |
| Next-event index | O(N+Q) construction; valid-prefix query O(log degree+h); general API additionally scans skipped records | O(N+Q) index | `event_index_build_seconds`, `event_index_reachable_bytes`; original event-oracle tests |
| Critical remaining-depth weights | O(Q+dependency edges) reverse-DAG preparation; O(h) event weighting, then original candidate scoring | O(Q) depths | Hand-labelled branched DAG and equal-depth recovery tests; scoped only to parking |
| Parking choice | O(Fh) potential evaluation plus O(log degree+h) query, F≤S | Candidate audit may retain O(F+h+Q) per decision | `parking_opportunities.csv`; low-depth QV null versus deeper inputs |
| Oriented cost matrix | O(mc(N+h+number of fixed moves)) without displacement prediction; both orientations are evaluated | O(mc+mh+N) working cost/potential state, before verbose sidecars | `assignment_cost_seconds`; heating observer and selected predictor components |
| Bottleneck then sum matching | O(mc log(mc)+m²c log(mc)); feasible-prefix fallback adds O(m²c log m), at most one rebuild | Cost matrix plus O(m+c) matching work arrays | `assignment_matching_seconds`, candidate count and matching oracle |
| Router | Per-transition conservative O(N³+NS), given unique legal destinations and spare cycle-breaking space; explicit finite failure when not feasible | O(N²+S) working graph/grid, plus emitted routes | Actual routed batches, temporary moves and declared grid; not inferred from assignment objective |
| Full replay repair | Baseline copy/revalidation + ranking/generation + up to B complete compiles/validations + exact local-prefix checks | Incumbent, candidate and round winner plus accepted/audit evidence; fixed trial count does not bound circuit-dependent size | `runtime_stages.csv`, `repair_cost_effectiveness.csv`; baseline/repair caps retained separately |
| Current verbose replay snapshots | Each prefix stores completed and pending CZ IDs together, plus positions, RNG, heating and exposure; serialization/hashing visits these values | Exactly P×Q repeated gate-ID occurrences in this representation, plus O(PN) state and other logs | `snapshot_accounting_01/snapshot_accounting.csv`; measured QFT65/80/100 |

The lookup index has a useful sparse bound. The complete diagnostic compiler has a different storage requirement. QFT100's baseline snapshot contains 24,632,550 completed/pending ID occurrences across 2451 boundaries and is 993,066,271 bytes on disk. The process retains additional Python objects, schedules and candidate state. A sub-gigabyte file is not itself a measurement of RAM, and measured process-family peaks include imports/native libraries; both are reported separately.

The Phase06 lossless memory adapter shares immutable evidence during deep copies and streams JSON writes. Its independent checks preserve canonical values, prefix hashes and scores. It reduces allocation pressure but does not remove the serialized P×Q representation or full-circuit recomputation. Claiming that the sparse index makes the whole pipeline linear in Q would therefore be incorrect.

## What timing can establish

The original studies retain three RFT timing samples per target and selected factorial settings have three timing repeats. Their variability, including high coefficients of variation, is reported. The bounded completion portfolio prioritizes coverage under a six-hour experiment budget and generally records one measurement per paired routing seed. These seeds are quality repetitions; they do not remove fixed order or host variability.

`compile_validate_repair_seconds` includes required compilation/checking/scoring and, for repair, baseline/prefix/candidate work. The repair worker writes its durable baseline inside this region; non-repair final export is outside it. The corrected DasAtom inner worker includes different native export work. These inner times must not be divided to claim cross-method speedups.

`process_wall_seconds` is the common operational outer scope, including imports, final artifact work and parent-side artifact hashing. Its cost is meaningful for executing this implementation, including diagnostics. A process timeout is enforced while the owned worker runs; subsequent termination/hash bookkeeping can make recorded wall time slightly exceed the configured cap. A timeout's recorded elapsed duration is not a completed algorithm runtime. The scaling plots mark censored points separately, and completed-only medians are labelled as conditional.

Observed memory is the maximum sampled sum of process-family peak working sets, with a four-GiB safeguard. It is neither an allocation-proof memory maximum nor a synchronized resident-set sum. It is sufficiently defined to report resource pressure and guarded failures without advertising an asymptotic empirical fit from eight sizes and two seeds.

## Consequence for the research conclusion

Full replay provides a conservative acceptance rule and catches locally favorable changes with a bad suffix. It is also the central practical cost. The bounded study can close with negative scaling outcomes: completed experiments include valid timeouts. The justified finding is a quality/cost tradeoff in a specific implementation, not that four trials are cheap or that the method always finishes QFT100 at an arbitrary deadline. Redesigning persistence or implementing true suffix resumption would be a separate future engineering contribution and would require a new frozen comparison; it is not silently substituted into these results.

Sources: [lookahead specification](../../reports/phase_04/lookahead_spec.md), [assignment specification](../../reports/phase_05/assignment_spec.md), [repair specification](../../reports/phase_06/repair_spec.md), [lossless memory adapter](../../tools/phase06_memory.py), [snapshot accounting](../../reports/phase_08/snapshot_accounting_01/verification.json), and the final completion-study runtime/scaling CSVs.
