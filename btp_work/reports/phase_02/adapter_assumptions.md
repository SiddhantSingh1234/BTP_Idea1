# Adapter assumptions and evidence

Owner: Codex /root, 28 October 2026. Contract: [D002](../decisions/D002_TRACE_V1.md).

Both adapters use only standard-library code and the shared trace helpers;
neither imports a compiler or calls its feasibility predicates. RFT text is
parsed strictly: placement, shuttles, cycle-parking annotations and CZ operations
retain their ordering and coordinates. Unknown lines and upstream `ERROR`
messages become failing diagnostics. DasAtom's native embedding, gate-group and
movement arrays are consumed directly. Inconsistent array lengths are rejected.
The native final embedding is an explicit final-map replay target.

One stable atom carries each source logical qubit. Atom IDs (`a0`, etc.) and
logical qubit IDs are distinct fields, but native logs do not independently
identify physical carriers. This is a declared no-SWAP/no-cooling assumption,
not evidence for state handoff. Gate IDs identify FIFO occurrences of each CZ
pair in the normalized input. Dependencies are recomputed independently from
the input circuit by the checker; emitted IDs do not authorize reordering.

The original normalized input, result, and native log/arrays are hashed in
metadata. Source revisions, options, seeds and module-provider paths are
preserved where the worker supplies them. Old Phase 00 smokes omit geometry;
only those use their documented 11x11, interaction 2, restriction 4 defaults.
Current campaign results provide explicit geometry. Coordinates are integer
grid indices; the native legacy profile converts them with 3 micrometres/site.

DasAtom can drop trailing inactive qubits. Its effective population comes from
the embedding, not a larger input declaration. The metadata retains both and
the validator flags an incomplete original register. Its native-N historical
score is reconstructed without silently padding atoms. Active-prefix controls
remain separately labelled, not full-register equivalents.

Physical times, transfer events, minimum separation and cross-trap geometry
are absent from native evidence. `evidence` leaves them unknown. The optional
two-stage reconstruction is a documented sensitivity/model test and cannot
make a native result physically established. In particular, it fails on the
QFT10 example in [the discrepancy ledger](discrepancy_ledger.md).

Primary local evidence reviewed for these choices:

- [RFT extracted text](../../source_review/extracted/Priyanshu_Aditya_ISVLSI2026_AK_O.txt), method and shuttling constraints; pinned compiler/converter predicates and counters.
- [DasAtom extracted text](../../source_review/extracted/3_DasAtom_A_Divide-and-Shuttle_Atom_Approach_to_Quantum_Circuit_Transformation.txt), hardware Section II, compatible moves in Section III, fidelity accounting in Section IV.
- [Schmid extracted text](../../source_review/extracted/6_Schmid_2024_Quantum_Sci._Technol._9_033001.txt), Section 3.2.4: shared AOD lines move all retained carriers.
- [Device-model extracted text](../../source_review/extracted/1_2607.20616v2.txt), Sections IV-B/D: coordinates, interaction/blocking radii, loading/storing, shuttling speed and minimum atom distance are separate properties.

The geometric path check minimizes relative squared distance analytically over
shared progress u in [0,1]. A common continuous monotone nonlinear progress law
that traverses this interval has the same spatial minimum. Independent progress
laws, multiple AODs, acceleration/heating and unknown cross-plane geometry are
not proven safe by this result. Timing uses linear progress only in the explicit
reconstruction policy. No sampled-path safety claim is made.
