# Phase 00 environment and execution evidence — updated 28 October 2026

**Current outcome: the research venv is installed and both pinned compilers run.**
The network/setup blocker described in the historical section below is resolved.
Exact manuscript-version evidence remains unresolved.

The tested interpreter is `btp_work/.venv/Scripts/python.exe`, uv-managed CPython
3.13.2 on Windows x64, matching the manuscript's version number. It is an Astral
standalone build; the manuscript's original binary build is unknown. The original
3.12.10 portable interpreter remains for document extraction only.

Both complete archive working trees are under `vendor`, with 512 RFT and 499
DasAtom files verified against every saved Git blob. Licenses are retained and
no upstream file was changed. [Source verification](../../runs/phase_00/verified_source_trees.json)
and [successful recovery](../../runs/phase_00/source_recovery_attempt_05.json)
record the evidence. No recovered AGENTS.md applies. No Git executable was
installed; public history was inspected through saved GitHub API responses.

| Dependency | Tested version |
| --- | --- |
| Qiskit | 1.3.1 |
| numpy | 2.2.2 |
| scipy | 1.15.1 |
| networkx | 3.4.2 |
| rustworkx | 0.15.1 |
| pandas | 3.1.0 |
| openpyxl | 3.1.5 |
| matplotlib / plotly | 3.11.2 / 7.1.0 |

All 29 installed distributions are frozen in the
[environment record](../../configs/environment/environment.json),
[exact version list](../../configs/environment/requirements-py313-win64.txt) and
[hash-locked requirements](../../configs/environment/requirements-py313-win64.lock).
The setup's import probe and `uv pip check` passed. Full RFT and DasAtom smoke
cases subsequently passed; this lock is now the tested snapshot environment.
A second clean lock-only reinstall was not performed. Python, venv, uv, caches,
sources, scripts and run artifacts are under `btp_work`.

The initial sandboxed retry still failed. The approved network execution of
source recovery and setup succeeded; changing config alone had not lifted this
session's network boundary. Tested setup commands from the workspace root:

```powershell
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/recover_phase00_sources.py --fetch --output runs/phase_00/source_recovery_attempt_05.json
powershell -NoProfile -ExecutionPolicy Bypass -File btp_work/tools/setup_phase00_environment.ps1
```

The second command created the venv with uv 0.9.5 / Python 3.13.2, installed the
union of declared upstream requirements, checked imports and package consistency,
and generated a candidate hash lock. The recorded setup attempt is
[setup_20261027_183111_096](../../runs/phase_00/setup_20261027_183111_096/setup_status.json).
The setup script refuses an existing environment. Do not rerun it to inspect
the installed venv or overwrite prior records.

Tested compiler commands (use new output names for another attempt):

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONDONTWRITEBYTECODE='1'
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm rft --case qft5 --out runs/phase_00/smoke_rft_qft5_01
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm dasatom --case qft5 --out runs/phase_00/smoke_dasatom_qft5_01
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm rft --case tableII --out runs/phase_00/smoke_rft_tableII_01
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/phase00_smoke.py --algorithm dasatom --case tableII --out runs/phase_00/smoke_dasatom_tableII_03
& '.\btp_work\.venv\Scripts\python.exe' -X utf8 btp_work/tools/trace_phase00_fixture.py --out runs/phase_00/compiled_fixture_01
```

The first three return success. The DasAtom Table II command returns Python
exit 2 (`unsupported_declared_register`): native compilation succeeds for five
qubits but the original input declares 16. Both scores and native/full-register
replay results are retained. Earlier attempts 01/02 surfaced that difference
as an adapter assertion failure; neither failure was discarded or relabelled.

The smoke wrapper uses numeric thread limits 1 and isolated working directories;
RFT retains its warmup and native timed region. Standalone DasAtom uses an
explicitly labelled API adapter with matched 11x11 geometry, rather than its
main script's default compact grid. Its timer is labelled separately. No whole
suite, corrected planner or new heuristic was run. Each case was repeated in a
fresh Python process; normalized input hashes, instruction bytes, counts and
scores match exactly in all four repeat pairs. Results are summarized in
[runtime_summary.json](../../runs/phase_00/runtime_summary.json).

## Historical pre-recovery observations (27 October; superseded above)

Owner: Codex `/root`. Date: 27 October 2026. Status: **blocked_dependency**.

There is no runnable compiler environment in this workspace. Full pinned-source
downloads were attempted and failed with `WinError 10013` (socket access denied).
Both repository attempts are preserved in
[source_recovery_attempt_01.json](../../runs/phase_00/source_recovery_attempt_01.json).
Local Python HTTPS and PowerShell `Invoke-WebRequest` also failed. Web retrieval
could read some primary-paper pages and the DasAtom repository README, but could
not recover the pinned RFT files, Git history, or pinned DasAtom implementation.
No sandbox escalation was requested; the managed permission profile disallows it.
This is an observed network restriction, not an author-artifact availability claim.

## Machine facts actually collected

See [environment.json](../../runs/phase_00/environment.json) for raw observations.

| Item | Observation |
| --- | --- |
| OS | Windows 11, build 26200, AMD64 |
| CPU | Intel Core Ultra 5 225H; 14 logical processors |
| Physical RAM | 16,535,990,272 bytes; 5,639,294,976 bytes available at probe time |
| Workspace disk | 256,599,126,016 bytes total; 161,200,619,520 free at probe time |
| Interpreter actually used | Portable CPython 3.12.10, 64 bit, under `btp_work/.research-tools/python` |
| Manuscript interpreter | Python 3.13.2 (RFT p.5); not installed/tested here |
| Available extraction packages | pypdf 6.21.2; fontTools 4.67.0 |
| Compiler packages | Qiskit, numpy, scipy, networkx, rustworkx, pandas, matplotlib, plotly, openpyxl all absent |
| Installation tools | No `pip` or `venv` module in the embedded interpreter; no Git on PATH |

The full retained core import fails at `import networkx` with
`ModuleNotFoundError`. DasAtom's implementation is absent. No successful QASM
normalization, RFT compilation, DasAtom compilation, memory pilot, or published
result is reported. The preparation Python remains an audit/extraction runtime.
The paper's i5 eighth-generation/8 GB machine differs from this machine; there
is no meaningful measured compile-time comparison yet.

## Tested commands

Working directory for all commands: `C:\Users\hp\Documents\BTP`. These commands
ran in PowerShell. Output paths for audit/recovery records must be new; the tools
refuse to overwrite earlier attempts. Change the suffix for a repeat.

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
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/recover_phase00_sources.py --output runs/phase_00/source_recovery_inventory.json
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/recover_phase00_sources.py --fetch --output runs/phase_00/source_recovery_attempt_01.json
& '.\btp_work\.research-tools\python\python.exe' -X utf8 btp_work/tools/prepare_phase00_metadata.py
```

Inventory, environment, metadata generation, and both isolated runs exit 0.
The isolated runs each pass 27 checks and are byte-identical, SHA-256
`6da28fc873e6dc2b4225e32febe80e1b739462b527e9fc7cba506fafcc8b58a8`.
The recovery inventory exits 0 without downloading. The fetch attempt exits 2:
both archives fail with the same socket-permission error. No compiler sources
were created under `vendor`.

Subsequent retries, including after the user added `network_access=true`, also
failed: see source_recovery_attempt_02/03 and compiler_retry_02 under runs/phase_00.
The local venv bootstrap script was prepared and PowerShell syntax-checked. Its
tested launch via `powershell -NoProfile -ExecutionPolicy Bypass -File
btp_work/tools/setup_phase00_environment.ps1` stopped at the uv download; see
[setup_status.json](../../runs/phase_00/setup_20261027_180107_712/setup_status.json).
The successful install path remains untested. A full Codex restart is the next
step to reload the user-edited configuration; managed session restrictions may
still take precedence.

The isolated tool executes selected **original AST definitions**, preserving
their source line numbers. It omits top-level optional imports and never supplies
fake numpy, scipy, networkx, Qiskit, or DasAtom modules. Tested code includes the
RFT builder, parking rule, exact orientation-materialization statements, legacy
parser/scorer, and dependency-free error branches. This is not a full-compiler
installation, routing test, or end-to-end repeatability result.

`isolated_01.json` is an earlier 24-check development result for a different
hand-worked final gate. The final fixtures and repeatability evidence are only
`isolated_final_01.json` and `isolated_final_02.json`. An initial AST read rejected
the runner's UTF-8 BOM; the audit reader now uses `utf-8-sig`. Upstream bytes
were not changed; Python itself accepts that BOM.

## Environment recovery and lock status

[dependency_status.json](../../configs/baselines/dependency_status.json) records
observed availability. It is explicitly **not a dependency lock**. No compatible
Qiskit/numpy/scipy/networkx/rustworkx version set has been installed or tested.
The unpinned upstream requirements are not sufficient to close the gate.

In a network-enabled session, rerun the tested recovery command with a new report
name. The helper validates every archive file against the saved Git blob tree
before extraction, retains licenses, refuses existing targets, and never runs
upstream benchmark scripts. Its successful-download path has not been exercised
here. Complete Git history/tags and table/plot scripts must then be inspected.

Install the research interpreter/environment under `btp_work`, preferably
3.13.2 if compatible. Resolve all used direct/transitive packages, record wheel
hashes, and test both compilers before freezing a lock. Any fallback interpreter
is a documented deviation. No successful setup command for that future
environment is claimed in this report.

Use a new working directory under `btp_work/runs` for every upstream run because
the RFT runner uses a fixed temporary filename. The next smoke targets are the
actual `qft_5.qasm` and `4mod5-v1_22.qasm` identified in the manifest. Their content
is not present yet, so successful commands and first compiler outputs remain
unavailable. Start with a proposed 60-second per-smoke timeout and a 4 GiB memory
cap; verify enforcement before running. Full-suite resource limits belong to
Phase 01 after a pilot. No long benchmark was launched.
