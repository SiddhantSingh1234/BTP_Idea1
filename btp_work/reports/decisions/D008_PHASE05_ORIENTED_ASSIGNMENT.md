# D008: oriented fixed-cost bottleneck/composite assignment

The user authorized Phase05 after reviewing the supplied papers, adding further research as needed, and asked that extra papers be retained as references. [Source research](../phase_05/source_research.md), [additional-paper archive and BibTeX](../../source_review/phase05_primary/README.md).

Implement proposal Step3 as a frozen oriented rectangular assignment. Exact sum-distance is corrected to materialize the scored orientation in every new control. The original snapshot and Phase04 passthrough remain separate unchanged references. Candidate policy and objective are independently switchable. Composite terms normalize distance, fixed-reference/internal conflicts, transfers, model-predicted marginal heating/loss and Phase04 future potential. No future chosen placements or unexecuted route outcomes are read.

Prefix heating is updated from already emitted original-router batches through the unchanged common physics functions. Its final states agree with independent full evaluation. Optional displacement estimates use known vacancies and the same parking potential, are costed explicitly and receive an ablation. A linear matrix does not encode mutual conflicts between different newly assigned rows, so actual routing/validation remains decisive.

The solver minimizes exactly (maximum frozen entry, summed frozen entries), not the full sorted lexicographic vector, physical makespan or full E. Forbidden edges stay forbidden. A maximum feasible row prefix can serialize; no-progress/zero-capacity cases fail explicitly. Candidate expansion is fixed at2 in its own control; all-compatible is a diagnostic alternative, not a promoted winner.

[Protocol](../../configs/studies/phase05_pilot_v1.json): four separate development seeds; 11 evaluation cases x two routing seeds x14 variants. No evaluated-outcome weight/horizon selection. All 364 development/evaluation schedules validate and replay identically. [Results](../phase_05/pilot_results.md) show conditional benefit: expanded composite versus expanded distance-sum gives 10/8/4 wins/ties/losses and mean relative E -1.815%, while common-CoM and bottleneck-only findings are mixed/negative.

This accepts engineering and the small analytical pilot, conditional on the [final gate](../phase_05/gate_01.json). Full paper-matrix evaluation, device calibration, original one-qubit timing and a general performance claim remain later obligations. The original frozen Phase01/03/04 benchmark campaigns are preserved; Phase06 is not started.
