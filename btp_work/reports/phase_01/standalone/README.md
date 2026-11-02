# Run the frozen Phase01 benchmark

Ready and tested; the full run is left stopped for the user. From
`C:\Users\hp\Documents\BTP`, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\btp_work\tools\Start-Phase01Benchmark.ps1
```

This starts a hidden independent Windows controller. No active agent or open
launching terminal is required. Keep the computer powered on. Automatic idle
sleep is inhibited during work, but manual sleep, closing the lid, shutdown and
reboot can interrupt it. Rerun the same command to resume: successful committed
measurements are skipped. There is no automatic login/startup task.

Check status or request a stop:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\standalone_baseline.py status
& .\btp_work\.venv\Scripts\python.exe -B .\btp_work\tools\standalone_baseline.py stop
```

Stop targets this study only and preserves partial outputs. An OS lock prevents
a second controller on the same study. The Windows venv redirectors, controller
and its worker can appear as multiple Python processes; only one benchmark job
runs at a time, with no separate auditor. Kill-on-close Windows jobs stop the
owned worker family if its controller crashes.

## Scope and files

All **132 paper configurations** remain: 66 RFT targets reuse their 198 saved
native timing samples and independent audits; 66 corrected DasAtom targets
receive one fresh timing pass. The 57 cached corrected schedules remain saved.
Nine DasAtom configurations still need complete schedules. Cache repair time
does not measure whole compilation, so corrected compilation must be measured
afresh. No broad sweep or whole-matrix timing repetition is added.

One genuine detached QFT5 11x11 smoke is already saved in the canonical study;
**65 corrected measurements remain**. It will be reused. Test-only pilots are
separate. The old 726-job campaign remains stopped and guarded.

Study directory: `btp_work/runs/phase01_frozen_baseline_v1`.

- `frozen/`: hashed executable baseline, vendor providers/licenses, 27 raw and
  normalized inputs, dependency inventory and original paper-focused plan.
- `references/`: original attempts, native outputs, independent audit receipts
  and 57 cached corrected schedules.
- `manifest.json`, `manifest.sha256`, `comparison_contract.json`: frozen
  source/input hashes, protocol and later Phase04 comparison requirements.
- `measurements/<target>/attempt_NN/`: requests, logs, corrected native layouts,
  timings, trace, independent validation, metrics and artifact hashes.
- `progress.json`: target, stage, heartbeat, counts and observed memory.
  The status command also probes the OS lock to identify stale progress.
- `results.csv`, `summary.json`: refreshed after every completed attempt,
  including all pending and failed configurations.
- `events.jsonl`, `controller_*.stdout.txt`, `controller_*.stderr.txt`: history
  and separate controller logs per launch.

Workers use hash seed0, seed42, one numerical thread, full declared registers
and requested hardware grids. Wall caps are 1800s, 3600s for qv_n16_d5 and
6000s for square_root_7; the observed process-family working-set cap is 4GiB.
Polling working sets is not an allocation-proof OS memory limit. Timeout,
OOM, unsupported, error and invalid outcomes are retained and held; resume
does not repeat identical failures indefinitely. Stop/crash/long-gap interrupted
attempts can retry on explicit resume. Code/protocol/cap changes need a separate
reviewed study. Snapshot or dependency changes cause refusal rather than mixing.

The runner saves compile time, runtime proxy, movement batches and fidelity
proxy. RFT retains its original timer/warmup policy and reports sample range/CV.
DasAtom's fresh corrected pipeline timer has a different scope and no warmup;
a normalized-input timer is saved separately. Do not infer cross-algorithm
speedups from unlike scopes. One new DasAtom sample has no timing-variability
estimate. Cache repair durations are separate from compiler timing.

Validation covers gate identity/dependencies, register, bounds, occupancy and
known AOD constraints. Native physical path clearance/calibrated fidelity remain
unsupported. Original invalid outputs remain preserved and labelled. Missing
paper-version evidence remains unresolved.

After Phase04 is complete, freeze it separately and run the same **66 RFT**
input/grid configurations with this contract, original placements/options,
scorer, timer boundaries and warmup. Include new event-index and heuristic work
inside compilation time. Keep DasAtom as the unchanged anchor. Before claiming
speedups, use small paired unchanged-RFT controls to assess host drift. This
baseline launcher does not run mutable Phase04 code.

## Actual tested commands

```powershell
# Executed one-job detached smoke; retained, not required again.
powershell -NoProfile -ExecutionPolicy Bypass -File btp_work/tools/Start-Phase01Benchmark.ps1 -Limit 1

& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/standalone_baseline_acceptance.py --study btp_work/runs/phase01_frozen_baseline_v1 --out btp_work/reports/phase_01/standalone/tests_03
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/paper_focus_acceptance.py --out btp_work/reports/phase_01/paper_focus_v2/tests_06
& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tests/phase_02_acceptance.py --out btp_work/reports/phase_02/tests_07
```

**8 + 16 + 14 groups pass**. Automation tests check real detached validated
compilation, reuse, cross-process locking, freeze/environment rejection,
132-target/198-sample evidence preservation, timeout, stop, monitor-gap handling
and killing a real child controller to verify its worker exits. Earlier failed
tests_01/02 remain: locked-byte reading and querying inherited job membership
were fixed before tests_03. Foundation checks include the 25 adversarial fixtures.
Reruns of tests require new output paths to preserve evidence.

Phase01 remains in progress. A completed measurement matrix still needs final
discrepancy analysis, regenerated figure/table and independent dataset review.

Windows reference documentation:
[independent Start-Process](https://learn.microsoft.com/powershell/module/Microsoft.PowerShell.Management/Start-Process),
[idle-sleep requests](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
