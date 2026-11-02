# Trace metric definitions

Metrics are accounting results, not a declaration that a schedule is valid.
Always join them with source status, independent validation and coverage.

| Field | Definition / limitation |
| --- | --- |
| required_CZ / observed_CZ | Normalized input operations versus emitted gate events; report both even for incomplete output |
| gate_stages | Distinct emitted gate groups; legacy header count is separately preserved and can include empty stages |
| routing_batches | Nonempty emitted move events, including source records with zero displacement |
| move_records / moved_atom_events | All atom records versus only nonzero-displacement records; an atom moved twice counts twice |
| sum_atom_distance_um | Sum of Euclidean distances of every atom move |
| max_atom_event_distance_um | Largest individual move distance |
| distance_by_atom_um | Accumulated distance for each physical carrier ID |
| sum_batch_max_distance_um | Sum, over batches, of that batch's longest atom displacement; legacy Total Move Distance uses this |
| observed_transfer_atom_events / stages | Explicit observed atom transfers versus concurrent transfer events; zero observed count with incomplete evidence is not proof of no transfers |
| inferred_transfer_atom_events / stages | Same counts under the declared reconstruction policy, separate from observations |
| makespan_us | Last end minus first in-circuit start, excluding initialization; null if any event lacks timing; derived timing is labelled |
| explicit_parking_atom_events | Nonzero moves with explicit cycle-breaking cause; unknown moves are not classified as nonparking |
| emitted_batch_line_conflict_graph | One vertex per atom move record; an edge violates AOD line equality/order within that emitted batch; density uses summed edges / summed possible edges, zero if no possible edges |
| planner_candidate_conflict_graph | Null: emitted logs do not expose the original graph of candidate moves |

For legacy accounting let N be the source-scored population, G the source-scored
CZ count, H the source gate-header count, B the nonempty movement-block count,
and D the sum of batch maximum distances in micrometres. The frozen scorer uses:

```text
transfer_alias = 4 B
T_proxy = H t_CZ + 4 B t_transfer + D / speed
idle_proxy = N T_proxy - G t_CZ
E_legacy = -G ln(f_CZ) - 4 B ln(f_transfer) + idle_proxy / T2
F_proxy = exp(-E_legacy)
```

The default legacy constants are t_CZ=0.2 us, t_transfer=20 us,
speed=0.55 um/us, T2=1.5e6 us, f_CZ=.995 and f_transfer=1. These reconstruct the
historical proxy; they do not establish heating, atom loss, true transfer
population or physical makespan. The input G may differ from observed gates in
a failed compiler result; the mismatch remains visible rather than silently
repairing the score. Negative-log fidelity is retained when finite F underflows.
A zero fidelity factor with a nonzero event count yields infinite E (represented
by a separate JSON flag), not clipped survival. Invalid factors are rejected.

In the valid parallel fixture, two atoms each move 1 um together: atom distance
sum=2 um, batch-maximum sum=1 um. Two assumed transfer stages contain four
atom-transfer events. Derived makespan=3.2 us; historical proxy=5.2 us. These
different definitions must not be plotted under an unqualified common name.

No extended heating/cooling/error scorer has been implemented. A new evaluator
identity and source-backed profile are Phase 03 requirements.
