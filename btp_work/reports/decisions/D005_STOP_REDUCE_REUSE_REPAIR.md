# D005: stop the broad campaign, retain every paper target, reuse and repair

Owner: Codex /root. User-directed scope change, 28 October 2026. This supersedes
the 726-job execution schedule and D004_REPAIR_FAILED_BASELINES's deferral of
repairs until that schedule finishes. It does not change source pins or erase
historical results. The separate Phase 02/03 acceptance decision in
D004_PHASE03_MODEL_AND_DEPENDENCY remains in effect; other phase work is preserved.

## Paper coverage retained

The original RFT paper was checked directly, including a local rendering of
[PDF page 6](../phase_01/paper_scope_evidence/page6.png). Figure 4 visibly plots
QFT sizes 5,10,...,60 on 11x11, 20x20 and 35x35 for both methods: 72 targets.
All four metrics remain: compile time, circuit runtime, movement operations,
and fidelity. Table II lists 15 circuits on 11x11/35x35 for both methods:
60 targets, retaining all three printed metrics. Total: **132 configurations**.
Table I is a four-qubit worked example, not an eight-variant ablation study;
its exact next-partner table remains a cheap independent test. Figures 1 and 3
are method/eviction illustrations, not additional benchmark matrices.

No paper point, circuit, method, grid, or reported metric is dropped. Historical
revision/options remain unresolved: this is the accepted pinned-source rerun,
not proof of the manuscript commit. The original layout-sampling/configuration
choices are retained, not reduced to save computation.

## Stop and reuse

The benchmark and auditor process families were stopped and verified absent;
[the receipt](../../runs/current_baseline/stop_20261028_user_scope_change.json)
identifies only the project-owned processes. Runtime progress says stopped.
The old controller now refuses to resume a study with this explicit stop and
replacement-plan marker. Its pre-guard source is archived. The compiler worker,
vendor snapshots, all 411 terminal attempt records and their results remain
unchanged. No long background process has been restarted.

The 411 records contain 376 paper-target attempts and 35 extra completed runs.
All are retained. Existing native timing repetitions are reused; no slow sample
is removed just because it is inconvenient. The new plan removes blanket future
repetitions and retires the broad 198-job RFT8 and 132-job active-prefix sweeps.
Of those 330 extra jobs, 35 already ran and remain archival data. The 20 not-run
native timing-repeat slots are not automatically requeued. These changes retire
315 unexecuted slots from the old schedule while preserving all paper coverage.

The [new plan](../../configs/studies/paper_focus_v2.json) has one row per paper
configuration and links every existing attempt/hash. Its canonical selection is
the earliest complete repetition, not the best score or fastest runtime.
Saved repeated traces agree exactly for every completed configuration. Timing
medians, sample counts, ranges and CV remain available in the joined report.

## Correctness repairs without repeated expensive compilation

All 66 RFT paper targets reuse their native results and matching independent
audits. Fifty-seven DasAtom targets have complete saved layouts. Their active
embeddings and gate groups are reused; partitioning/VF2/embedding searches are
not run again for repair. Declared trailing idle qubits are restored at vacant
sites (20 targets needed this). Only invalid transitions are rerouted; already
legal native transitions are retained. Vacant destinations and ordered AOD
lines are enforced, and dependency cycles use explicit temporary vacancies.
No proposed lookahead or score-driven objective is enabled.

All 57 final cached repairs pass independent discrete replay with no known
violations. Original invalid rows remain invalid. Corrected files have their
own provenance, hashes, counters and scores, under `dasatom_corrected_v2`.
The final corrected cache is `cached_corrections_05`; earlier development
passes are preserved and are not the accepted repaired dataset.

This main baseline retains legacy geometry assumptions. Native logs do not
provide physical minimum separation or cross-trap plane geometry. Those remain
unsupported checks, not invented zero-distance limits or successful physical
proofs. The independent checker still checks supplied geometry and reports the
missing evidence. The older, stricter single-plane/3um control remains a
separate hypothetical-profile result; it is not silently substituted here.
Phase 03 consumers must validate any additional physical profile before making
extended-model claims.

Fresh compilation smoke tests exposed a tuple/list representation mismatch in
the new adapter's final-map comparison. Coordinate containers were normalized,
a regression added, and the original development failures retained. Fresh
QFT10 and 16-declared/5-active smokes now pass and exactly match their cached
corrected embeddings, gate groups and movement lists.

## Quality and honest timing

All existing timing samples are retained; fixed-seed repeats are not portrayed
as independent quality samples. Validation covers every reused/repaired paper
target. Sixteen paper-focus test groups plus fourteen existing foundation
groups pass, including 25 adversarial fixtures, full tiny-circuit semantics,
five actual routing seeds on the fixed worked example, capacity/no-CZ errors,
native-route preservation, source hashes and process-family timeout cleanup.
The tiny seed fixture is not a full benchmark seed-distribution study.

Cached repair duration is not full corrected compilation time. Original native
compile times remain reference measurements with their original validity and
scope. Corrected full-compilation fields stay null when not freshly measured.
The two fresh smokes are validation pilots, not new timing comparisons. Fresh
corrected timing is needed wherever a later comparison relies on that quantity;
it must not be fabricated by relabelling old invalid-run timings.

## Nine missing traces, no replacement sweep

Nine DasAtom 35x35 targets have only censored native attempts: QFT35/40/45/50/55/60,
misex1_241, qv_n16_d5 and square_root_7. They remain mandatory rows. One bounded
corrected compilation per missing target is queued. Caps are 1800 seconds,
except qv_n16_d5 (3600s) and square_root_7 (6000s), whose printed paper times
already exceed the shorter budgets. Observed process-family memory is capped
at 4 GiB. Censored values are not zero-time measurements.

`run_paper_focus.py` runs at most one queued target by default, with one active
worker, an OS lock, inline validation, success reuse, and no automatic same-cap
repeat after a failure. These nine runs have **not** been launched. The user
requested stopping the background processes; the new executable plan is ready
without restarting the campaign or auditor. Any remaining unsupported case must
stay reported, not be dropped to make the dataset look complete.
