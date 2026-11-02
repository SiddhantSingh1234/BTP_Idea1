# D001 — Use latest public sources and measure a new baseline

- Date/owner: 28 October 2026, user instruction recorded by Codex /root.
- Affected phases: 00, 01, later comparisons.
- Status: adopted.
- Type: explicit user scope/baseline decision.
- User instruction: "use latest available commit ... run these measurements again and save those results"; subsequently "run all result that have been specified in paper again ... save those result as new benchmark ... compare after making changes".

## Decision

Use the latest public default-branch commits verified on this date, then freeze
them for this study. RFT is `3d1f09233c2acd357fd9fbfad1b5300a921d301a` and DasAtom
is `73a6bdf0fd200b2733745211eaf2e0c1e17f496a`. These are already installed.
See [head verification](../../runs/phase_00/latest_heads_20261028_02/latest_sources.json).
Use explicit snapshot-control labels; do not call them the exact manuscript
implementation. The unknown original paper revision remains unresolved as a
historical limitation, but no longer blocks the user-selected current-source
Phase 00 baseline. This is a changed completion scope, not recovered evidence.

## New measurement scope

Run all current-source equivalents of Fig. 4: QFT 5,10,...,60 on 11x11,20x20,35x35;
and the 15 Table II circuits on 11x11 and 35x35. Measure RFT and standalone
DasAtom with recorded variants, inputs, hardware, seeds and timer scopes. Save
every attempt, trace, validator coverage, metric, failure and timeout. Repeat
successful timing cases and check stochastic effects with separate labelled runs.
Additional existing RFT variants, normalization controls and diagnostic cases may
be run when they improve interpretation. No proposed research heuristic is added.

Native register handling differs: preserve source-native measurements, and
keep any common active-prefix normalization as a separately labelled control.
Never silently compare a 16-qubit RFT trace with a five-qubit DasAtom trace as
matched hardware/register semantics. Untouched-source results remain archived.

## Verification and future use

Phase 00 closes against the adopted current-source scope once its six runnable
criteria and head/config/source checks pass. Phase 01 performs the full fresh
measurement campaign. Its outputs are a new measured baseline, not an assertion
that paper numbers were reproduced. Later changes must use the same immutable
inputs/configuration/evaluator and compare only compatible tracks. Revisit only
through a new versioned decision; never update a frozen study to a moving head.
