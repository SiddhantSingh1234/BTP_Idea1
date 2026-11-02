# Shared technical contracts

These are proposed interfaces to be frozen by Phases 00–03. They are not implemented APIs. Agents may refine them with an explicit decision and schema version, while preserving the scientific distinctions below.

## Notation and units

Use `N` qubits, `L` logical layers, `h` future-event horizon (the proposal's k), `m` unresolved logical pairs, `s` candidate interaction slots, `A` physical atoms, and `B` physical movement batches. A logical pair is assigned to a two-site interaction slot; its two endpoints have an orientation. Keep physical-atom identity distinct from logical-qubit identity when cooling transfers quantum information.

Use integer grid indices for discrete sites and explicit conversions to physical distance. Recommended stored units: micrometres for distance, microseconds for time, radians per microsecond for angular trap frequency. For acceleration, `1 m/s^2 = 1e-6 micrometre/microsecond^2`. Record the original unit and conversion beside every published parameter. Never assume “80 kHz” denotes angular frequency without resolving the source convention.

## Architecture and hardware profile

Every profile includes:

- Schema/profile ID, source pages or calibration references, assumption labels, and content hash.
- Grid dimensions, spacing, legal sites, interaction/restriction radii, minimum atom separation.
- Individual/global addressing, number of AODs, row/column rules, and allowed transfer/gate overlap.
- Gate durations and fidelities; transfer duration and **per-atom per-event** fidelity.
- Movement trajectory type, acceleration/velocity/jerk bounds where used, and unit conversions.
- Dephasing/coherence convention, and whether stationary, moving, transferred, and gate-active intervals accrue exposure.
- Heating initial state and update rule, trap frequency convention, zero-point size, heating gate penalty, loss rule and evaluation cadence.
- Cooling support, trigger, reset rule, affected atom set, resource requirements, operation schedule, and state mapping.

Maintain separate profiles: `legacy_rft` (exact historic accounting), `extended_no_cooling`, and a resource-enabled cooling profile when physically specified. Other published parameter sets are explicitly labelled sensitivity profiles. Unknown constants remain unresolved, not copied from a different device as facts. Model parameters may be hypothetical for sweeps if labelled and justified.

## Compiler request and result

A request contains normalized circuit ID/hash, full preprocessing recipe, hardware geometry, algorithm revision, variant options, all seeds, and any bounded-work limits. The compiler returns a trace plus diagnostics; it does not get to declare its own output valid merely because planning succeeded.

Use independent options for lookahead policy/horizon, candidate set policy/size, assignment objective, conflict/heating terms, and repair budget. Profiles used only for scoring must not silently change placement. If physical constraints require cooling or retiming, record the resulting schedule transformation and evaluate all compared variants by the same rules.

## Event trace

Recommended storage: one metadata JSON file and an ordered JSONL event stream. Metadata includes schema version, circuit/profile/config hashes, compiler/adaptor revisions, seeds, initial atom/qubit/trap mapping, geometry, and logical gate IDs. Event records contain:

| Field | Meaning |
| --- | --- |
| `event_id`, `kind` | Stable identity; initialize, transfer, move, gate, cooling sub-operation, or wait |
| `logical_layer`, `placement_batch`, `routing_batch` | Distinct logical and physical groupings |
| `start_us`, `duration_us`, `resources` | Timed execution and resource ownership |
| `atom_ids`, `logical_qubit_ids` | Physical carriers and current logical states |
| `from_sites`, `to_sites`, `trap_from`, `trap_to` | Geometry and transfer identity, where relevant |
| `trajectory` | Interpolation law and bounds needed to validate paths |
| `gate_id`, `gate_type`, `parameters`, `dependencies` | Circuit operation, exactly once, and prerequisite IDs |
| `cause`, `parent_event_id` | Parking/eviction/repair/cooling origin for accounting |

Initial placement is not charged as in-circuit transport unless the profile explicitly includes loading. Trap transfers are explicit, not inferred from a fixed multiple of movement batches. Concurrent transfers may consume time once as a stage, while each affected atom contributes its own fidelity factor. A zero-displacement atom is not automatically transferred. Retained AOD occupancy must be represented if supported.

Text logs from upstream may omit details. Adapters must distinguish directly observed fields from derived assumptions, and reject traces when missing information prevents a required correctness or cost claim. One-qubit gates can be excluded in the historical route-only experiment, but final normalized-circuit semantics and the chosen scoring scope must still be explicit.

## Validator contract

Input: immutable trace, normalized circuit, hardware profile. Output: validity, list of violations with event IDs, and coverage/unsupported-check flags. Validate:

1. Every required operation occurs exactly once with correct logical operands and dependencies.
2. Atom/qubit mapping, occupancy, bounds, trap ownership, and resource exclusivity throughout replay.
3. Interaction radius and cross-gate restriction radius at gate time, with a frozen boundary tolerance.
4. AOD equality/order preservation and coupled-line motion during moves, not only final coordinates.
5. Collision/minimum separation for moving pairs and moving versus stationary atoms along the specified trajectory.
6. Timing, transfer prerequisites, cooling state handoff/reset, and legal gate/trap coexistence.
7. Global-pulse unintended interactions only for a profile that actually has global pulses; mark not applicable for individual addressing.
8. Final logical operation sequence equivalence, using gate IDs/DAG replay and independent tiny-circuit unitary/state checks with explicit final permutation.

Endpoint AOD tests alone are not a continuous collision proof. Use analytical minimum-distance checks for a shared progress function where possible; otherwise provide a conservative geometric/temporal bound. Sampled trajectories are diagnostic and must be labelled incomplete if no error bound establishes safety. Unsupported checks block a full physical-validity claim.

## Timing and error accounting

`makespan = max(event end) - min(in-circuit start)`. For synchronized movement batches the duration follows the slowest legal trajectory, but shared AOD lines can couple displacements. Count all routing substages, parking, transfers, gates, cooling, and waits. Sequential batches add time; independent concurrent events do not.

Let `E = -ln(F_proxy)`. A source-consistent extended decomposition is:

```text
E = E_native_gate + E_transfer + E_heating_gate
  + E_movement_loss + E_cooling_gate + E_decoherence
```

- `E_native_gate`: errors of original/synthesized computation gates (one-qubit inclusion follows declared scope).
- `E_transfer = sum over atom-transfer events [-ln(f_transfer)]`.
- `E_heating_gate`: Atomique-inspired extra gate penalty from affected atoms' vibrational states at gate time; specify the architecture adaptation.
- `E_movement_loss`: sum of negative-log conditional survival factors at the movement events where the model applies.
- `E_cooling_gate`: extra gates introduced by a supported cooling primitive. Two CZ per cooled atom is counted once, not again inside `E_native_gate`.
- `E_decoherence`: per-qubit time integral of the profile's exposure rate. It includes all applicable transport/cooling time without adding a second duplicate movement-decoherence term.

Track extra cooling transfers under `E_transfer` and all cooling time under the exposure integral; annotate them for a cooling-total diagnostic without adding that diagnostic to E again. Transfer loss and movement-induced loss are separate mechanisms only if the chosen parameterization supports that interpretation.

Historical score is reproduced exactly from the chosen upstream revision, even when its idle convention differs. Report legacy and extended scores separately. Evaluate products in log space (`log1p`/stable survival arithmetic); `p_loss=1` yields `E=+infinity`, not a silently clipped good score. Reject invalid inputs or nonphysical factors outside [0,1]. A raw F underflow is represented alongside finite E and an underflow flag.

E is an approximate independent-error accounting proxy. It is not an exact output-state fidelity, not a confidence interval on a real device, and not atom-loss correction. No stochastic loss injection is required for the core project.

## Experiment record

One immutable record per attempt, including failures:

```text
run_id, attempt_id, timestamp, owner
input circuit/generator/version/hash, circuit seed, family, N, CZ count, L
normalized circuit hash and preprocessing revision
compiler/adaptor/validator/evaluator revisions
hardware profile hash, resolved options, layout seed, routing seed
CPU/OS/RAM, threads, Python/packages, resource limits
compile time, offline-layout time, preprocessing time, validation/scoring time
peak memory definition and sampling method
trace path/hash, validation result/coverage
makespan, gate stages, movement batches, moved atom-events
sum/max atom distance, sum of batch maximum distances
per-atom transfer count, timed transfer stages, parking, cooling atom-events/episodes
conflict edges, possible edges, density (0 when fewer than two vertices)
all E terms, total E, F_proxy/underflow, runtime status and diagnostics
```

Use statuses `ok`, `invalid`, `timeout`, `out_of_memory`, `unsupported`, `error`. A timeout is a censored outcome, not an observed completion time. Do not average it as zero or discard it silently.

## Baseline and variant naming

Keep algorithm and evaluator axes separate. Suggested algorithm variants: historical/corrected RFT, exact legacy lookahead, generalized h=1, h=2/4/8, bottleneck-only, fixed conflict/composite, expanded candidates, repair, and full. Suggested scorer axes: legacy, extended-no-cooling, extended-resource-enabled-cooling. Merely rescoring one frozen trace changes a model, not the algorithm. Labels and manifests must make that distinction visible.
