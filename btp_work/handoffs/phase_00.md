# Phase 00 handoff — current checkpoint, 28 October 2026

Owner: Codex /root. **Status: complete under the user-adopted latest-source scope
D001.** The runnable snapshot audit and environment setup are delivered; exact
manuscript-version evidence remains unresolved as a historical limitation.
See [D001](../reports/decisions/D001_CURRENT_SOURCE_BASELINE.md) and the
[passing scope-aware check](../runs/phase_00/final_gate_check_03_latest_scope.json).
This is an explicit changed completion scope, not recovered paper evidence.
All earlier availability claims and gate verdicts
in the historical checkpoint below are superseded by this current section.

Both complete pinned archive working trees are recovered: RFT
`3d1f09233c2acd357fd9fbfad1b5300a921d301a` (512 files) and standalone DasAtom
`73a6bdf0fd200b2733745211eaf2e0c1e17f496a` (499 files). Every Git blob was
reverified in [verified_source_trees.json](../runs/phase_00/verified_source_trees.json).
Licenses and upstream bytes are unchanged; no applicable AGENTS.md was found.
These are archive working trees, not local Git clones. Public history was
retrieved separately. Papers/Proposal remain unchanged; Intern_Report is excluded.

The research venv is `btp_work/.venv/Scripts/python.exe`, CPython 3.13.2, matching
the manuscript version number. Qiskit 1.3.1, numpy 2.2.2, scipy 1.15.1,
networkx 3.4.2, rustworkx 0.15.1 and all 29 distributions are frozen in the
[environment record](../configs/environment/environment.json),
[version list](../configs/environment/requirements-py313-win64.txt) and
[hash lock](../configs/environment/requirements-py313-win64.lock).
Imports, package consistency and both full compiler smokes pass. A second clean
lock-only reinstall was not tested. No proposed heuristic or corrected compiler
baseline was implemented; all adapters are outside vendor trees.

## Current results and exact tested commands

Working directory: `C:\Users\hp\Documents\BTP`. Approved network execution of
source recovery and setup succeeded after the sandboxed retry failed:

```powershell
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/recover_phase00_sources.py --fetch --output runs/phase_00/source_recovery_attempt_05.json
powershell -NoProfile -ExecutionPolicy Bypass -File btp_work/tools/setup_phase00_environment.ps1
$env:PYTHONHASHSEED='0'
$env:PYTHONDONTWRITEBYTECODE='1'
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm rft --case qft5 --out runs/phase_00/smoke_rft_qft5_01
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm dasatom --case qft5 --out runs/phase_00/smoke_dasatom_qft5_01
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm rft --case tableII --out runs/phase_00/smoke_rft_tableII_01
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/trace_phase00_fixture.py --out runs/phase_00/compiled_fixture_01
```

All above commands succeeded. The setup refuses an existing environment. Use
new output suffixes for another smoke attempt. No restart is needed to use the
installed runtime. Numeric thread limits are 1; runs use isolated directories.
RFT's warmup/native timed region is preserved. Standalone DasAtom uses an
explicitly labelled API adapter with 11x11 geometry, rather than the main
script's compact-grid default; its timer is separately labelled.

| Case | Declared/native N | CZ | Gate cycles | Move batches | Legacy F |
| --- | --- | --- | --- | --- | --- |
| RFT QFT5 | 5/5 | 26 | 17 | 10 | 0.8748227441484157 |
| DasAtom QFT5 | 5/5 | 26 | 26 | 0 | 0.877796969531686 |
| RFT 4mod5-v1_22 | 16/16 | 11 | 10 | 1 | 0.9453302538303964 |
| DasAtom 4mod5-v1_22, native scope | 16/5 | 11 | 11 | 0 | 0.9463490278828605 |

The last row is not a full-register matched result. DasAtom omits trailing
inactive qubits; its native five-qubit trace replays successfully. Rescoring
that partial trace at N=16 yields 0.9463337602417032 but does not supply the
other 11 atoms. This actual command returns Python exit 2 with explicit status
`unsupported_declared_register`:

```powershell
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm dasatom --case tableII --out runs/phase_00/smoke_dasatom_tableII_03
```

The three successful cases' `02` repeats and this case's `04` repeat were run
in fresh processes. All four pairs have identical normalized hashes, complete
instruction bytes, counts and shared scores. Earlier DasAtom Table II 01/02
attempts exposed the register mismatch as an adapter assertion; those failures
are retained. See [runtime_summary.json](../runs/phase_00/runtime_summary.json).
Replay covers CZ multiset/dependency order, initial/batch-end occupancy and gate
geometry; it is not the full Phase 02 physical validator.

The [actual compiled fixture](../runs/phase_00/compiled_fixture_01/trace.json)
uses existing ladder6, three layers and the declared 3x3/two-slot geometry.
It captures candidates, both orientation costs, RFT entries, target maps,
parking decisions and router calls without patching any compiler function.
There are two forced evictions (including no-future-partner parking), four CZs,
three execution cycles and six movement batches; legacy F=0.9787689724998074.
Its [instruction stream](../runs/phase_00/compiled_fixture_01/instructions.txt)
passes the scoped replay. The earlier conditional analytic trace remains
labelled as such and is not substituted for this observed output.

## Current mandatory acceptance assessment

Final validation commands were executed from the workspace root:

```powershell
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/check_plan.py
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/check_phase00.py --output runs/phase_00/final_gate_check_02.json
```

The documentation/integrity check passes with no issues: eight original PDFs
and six original excerpt blobs unchanged. The
[final phase check](../runs/phase_00/final_gate_check_02.json) verifies all 1,011
recovered source files, repeat evidence and the actual fixture; artifact checks
and all six scoped snapshot criteria pass. It intentionally retains Python
exit 2 because exact-paper evidence is unresolved; full phase_complete=false.

| Phase 00 criterion | Current disposition |
| --- | --- |
| Fresh-shell RFT and DasAtom smoke | Pass: both QFT5 runs execute full pinned sources in fresh processes |
| Algorithm 1 explanation/source map | Pass: implementation_map.md and actual compiled fixture |
| Paper/snapshot/corrected distinction | Pass: separate configs; paper null; no corrected implementation |
| C1-C8 owner and resolution plan | Pass: baseline_spec.md; deferred work is not called implemented |
| Input normalization/output accounting specification | Pass as specification: exact versions/recipe, raw hashes and explicit unsupported native-register policy frozen |
| Deterministic repetition | Pass for tested controls: four trace/count/score repeat pairs; general RNG/order limitations documented |
| Exact-paper configuration evidence | Unresolved historical limitation; outside the user's D001 current-source completion gate |

The input manifest now has raw SHA-256 for all 15 Table II and 56 candidate QFT
files, plus normalized hashes/counts for the two actual smoke inputs. Other
normalizations belong to Phase 01. Hardware/trace/profile contracts and C1-C8
remain as documented; no new event schema or physics model is introduced.

The [history audit](../runs/phase_00/history_01/summary.json) recovered 27 main
commits, current main=pin and no tags. Plot code filters 5..60 step5; table code
selects ladder8 CSV names. No original CSVs or author-supported paper mapping
were found. A 2025 commit message already mentions multi-layer lookahead,
limiting broad novelty claims. Seven helper-history versions did not match the
embedded blob exactly; the [code diff](../reports/phase_00/embedded_dasatom.diff)
shows progress-logging differences, with no observed planner-rule change.

Machine facts remain in environment.md: Core Ultra 5 225H, 14 logical CPUs,
about 16.54 GB physical RAM. No peak-RSS study, full-suite resource pilot,
continuous clearance proof, full-unitary simulation or published result is
claimed. Timers have distinct scopes; no speedup conclusion follows from smokes.

Next owner: run a fresh-suffix QFT smoke with the installed venv, then recover
manuscript evidence or preserve a qualified snapshot study. Phase 01 remains
not_started here. Its ledger must retain unmatched/unavailable outcomes and
separate native active-prefix DasAtom from a future corrected full-register
control. Do not contact authors or introduce proposed heuristics without the
appropriate authorized phase. The complete initial checkpoint follows only
as historical context; its blocked-setup verdicts are no longer current.

# Historical checkpoint — before successful recovery

## Identity and status

- Owner: Codex `/root`; 27 October 2026.
- Status: **blocked_dependency**, not complete. Exact-paper gate remains
  `paper_revision_unresolved` independently of the download problem.
- Starting/final source identity: retained RFT excerpt at
  `3d1f09233c2acd357fd9fbfad1b5300a921d301a`; no upstream bytes modified.
  Standalone DasAtom pin: `73a6bdf0fd200b2733745211eaf2e0c1e17f496a`, tree metadata only.
  No compiler checkout, executable environment, corrected revision, or proposed
  research heuristic was created.
- Prerequisites read: README, master plan, protocol, technical contracts, tracker,
  Phase 00 brief, source review, proposal Idea 1/My Choice and relevant primary
  paper sections. No earlier phase handoff exists. No applicable AGENTS.md found.
- Scope delivered: source/metric audit, isolated counterexamples, code map,
  conditional worked trace, baseline specifications, dataset identity inventory,
  recovery/bootstrap tooling, documented failures and gate assessment.

## Artifacts and use

| Artifact | Purpose / next use |
| --- | --- |
| [environment.md](../reports/phase_00/environment.md) | Machine/package facts, commands actually tested, setup limitations |
| [implementation_map.md](../reports/phase_00/implementation_map.md) | Algorithm 1 explanation and pinned function/line map; analytic eviction example |
| [baseline_spec.md](../reports/phase_00/baseline_spec.md) | Controls, manuscript item ledger, normalization/accounting, C1-C8 owners/plans, primary-source/overlap review |
| [discrepancy_ledger.md](../reports/phase_00/discrepancy_ledger.md) | D01-D17, confirmed/unresolved distinctions; no corrections applied |
| [baseline configs](../configs/baselines/) | Source-backed snapshot options; paper/corrected/dependency fields explicitly unresolved |
| [input manifest](../configs/benchmarks/reproduction_manifest.json) | All 15 Table II names and 56 candidate QFT files, source Git blob identities, missing normalized hashes |
| [raw inventory](../runs/phase_00/inventory.json) | Six excerpt SHA-256/Git hashes, original PDF integrity, embedded-source comparisons, exact function anchors |
| [final isolated run 1](../runs/phase_00/isolated_final_01.json) / [run 2](../runs/phase_00/isolated_final_02.json) | 27 checks each; byte-identical; explicitly no full compiler execution |
| [latest download retry](../runs/phase_00/source_recovery_attempt_03.json) | Retry after user set network_access=true; both downloads still denied by active session |
| [compiler startup retries](../runs/phase_00/compiler_retry_02/attempts.json) | Missing pinned entry points and retained-runner missing-pandas diagnostic; no circuit compiled |
| [setup script](../tools/setup_phase00_environment.ps1) | Portable uv 0.9.5, managed Python 3.13.2, local .venv/caches, full-source recovery, declared requirements and candidate lock; successful install path untested |
| [setup failure record](../runs/phase_00/setup_20261027_180107_712/setup_status.json) | Network failure before uv/environment install; PowerShell syntax check passed |

All new files are under `btp_work`. Papers/Proposal were not edited;
Intern_Report was excluded. Retained-source and PDF integrity are checked.

## Actual commands and outcomes

Working directory: `C:\Users\hp\Documents\BTP`. Use the available portable
audit Python, not a claimed research environment. Exact successful audit commands:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONHASHSEED='0'
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/audit_phase00.py inventory --output btp_work/runs/phase_00/inventory.json
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/audit_phase00.py environment --output btp_work/runs/phase_00/environment.json
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/audit_phase00.py isolated --output btp_work/runs/phase_00/isolated_final_01.json
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/audit_phase00.py isolated --output btp_work/runs/phase_00/isolated_final_02.json
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/prepare_phase00_metadata.py
```

These exit 0. Each isolated run passes 27 checks. Both result files have SHA-256
`6da28fc873e6dc2b4225e32febe80e1b739462b527e9fc7cba506fafcc8b58a8`.
Records are immutable: use a new output filename on repetition. The metadata
exporter refuses existing outputs; do not rerun it just to repeat the checks.

Tested recovery/setup commands (they **failed**, not successful setup examples):

```powershell
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/recover_phase00_sources.py --fetch --output runs/phase_00/source_recovery_attempt_03.json
powershell -NoProfile -ExecutionPolicy Bypass -File btp_work/tools/setup_phase00_environment.ps1
```

Recovery exits 2 with socket `WinError 10013` for both repositories. Setup stops
at the uv archive download with `Unable to connect to the remote server`, records
status error, and creates no environment. Direct PowerShell script invocation
also encountered local execution policy; the tested `-ExecutionPolicy Bypass`
applies only to that child process and does not lift the Codex sandbox restriction.
No successful short-QFT, Table II, or DasAtom smoke command/output exists yet.

Final verification commands also ran:

```powershell
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/check_plan.py
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/check_phase00.py --output runs/phase_00/final_gate_check_01.json
```

Planning/integrity check: exit 0, no issues, all eight PDF hashes and six retained
source blobs verified. [Phase gate check](../runs/phase_00/final_gate_check_01.json):
artifacts consistent, all six mandatory criteria accounted for, exit 2
intentionally because the phase is incomplete. This exit is not a passing gate.

## Mandatory acceptance evidence

| Criterion copied from Phase 00 | Verdict | Evidence / remaining limitation |
| --- | --- | --- |
| A fresh shell can run one RFT and one DasAtom smoke case using documented commands. | **Blocked** | Recovery attempts and startup logs; missing sources and compiler packages |
| The agent explains Algorithm 1 and shows a traceable source-to-code map. | **Pass, source-audit scope** | implementation_map.md, pinned hashes/function anchors; worked trace explicitly hand-specified |
| The manuscript/snapshot/corrected control distinction is explicit; no uncertain variant is called exact paper reproduction. | **Pass** | baseline_spec.md and distinct configs; no paper/corrected revision invented |
| Every scientific clarification C1-C8 has an owner and a recorded resolution plan. | **Pass** | baseline_spec.md C1-C8 ownership table; deferred physics/heuristic checks are not reported as implemented |
| Input normalization and output accounting are specified sufficiently for Phase 01. | **Partial / unresolved** | RFT specified; original bytes, Qiskit version and DasAtom helper behavior not recovered; Phase 01 cannot run yet |
| Deterministic repeatability is tested twice, or all stochastic sources are identified for controlled repetition. | **Unresolved for compilers** | Isolated routines repeat twice; RFT seed/order audit recorded; absent DasAtom/Qiskit/networkx behavior and full schedules untested |
| If historical configuration remains unavailable, leave the exact-paper gate unresolved. | **Unresolved gate preserved** | `paper_revision_unresolved`; no successful snapshot audit can establish paper identity by itself |

The full runnable-snapshot audit required as fallback is also incomplete.
Consequently this handoff is not acceptance of Phase 00 or authorization to
start research extensions. Phase 01 remains not_started; independent inventory
work may continue.

## Findings, interfaces and resources

The matrix/materialized orientation mismatch is confirmed on a minimal valid
slot: selected cost 3.2360679775 versus materialized 3.4142135624. RFT retains
several partners but not repeated future events. Legacy transfer alias is four
per movement batch, independent of moved population. Embedded DasAtom helper,
router and QFT input blobs differ from standalone. Full end-to-end impact is
unmeasured. See the discrepancy ledger for cutoff, failure, timer and unused-API
issues. No source bug has been repaired in a hidden baseline.

The example fixture has three actual dependency layers, four CZs, two movement
batches and two atom moves; score 0.9796842327609727 under the retained legacy
scorer. This is a conditional analytic trace with declared assignment/parking
ties, not an observed compiler result. Only boundary replay and gate geometry
are checked; continuous physical validity is outside this phase's isolated check.

Introduced metadata schemas: `phase00.baseline-spec.v1` and
`phase00.reproduction-inputs.v1`, which are specifications/inventories rather
than implemented compiler/trace APIs. No Phase 02 event schema was frozen.
Environment lock remains null. C1-C8 plans preserve technical-contract semantics.

CPU: Core Ultra 5 225H, 14 logical processors; 16.54 GB RAM, about 161.2 GB disk
free at probe time. No compiled-circuit runtime or peak-memory result exists.
RFT memory depends on distinct pairs and layers (worst-case O(P*L + N*L + G)),
not merely a presumed O(N*L) next-partner table. Full experiments need a pilot.

## Resume after restarting Codex

The user added `[sandbox_workspace_write] network_access = true` in their own
`C:\Users\hp\.codex\config.toml`; it was read back as true. The current session
still denies sockets. Fully close/reopen Codex to reload permissions, then read
this handoff and STATUS.md. If a managed profile still denies networking, local
configuration alone is insufficient; do not alter firewall/security policy.

First retry with a **new** result filename:

```powershell
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/recover_phase00_sources.py --fetch --output runs/phase_00/source_recovery_attempt_04.json
powershell -NoProfile -ExecutionPolicy Bypass -File btp_work/tools/setup_phase00_environment.ps1
```

The helper checks all expected Git blobs before extraction and retains licenses.
Review recovered AGENTS.md, requirements, full DasAtom code and history before
compiler execution. Inspect/resolve package compatibility, then run `qft_5` and
`4mod5-v1_22` through RFT and DasAtom in isolated directories. Preserve exact
commands, resolved configuration, input/output hashes, counts, stderr, timing
scope and both repeats. Only then promote a candidate dependency lock and
replace missing-input metadata with observed content identities. Do not treat
the wrapper's import check or package consistency check as compiler smoke success.

Recover the manuscript revision/options/raw data separately. If unavailable,
finish the runnable snapshot audit while retaining the exact-paper gate as open.
