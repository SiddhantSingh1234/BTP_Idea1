# Phase 04 completion review

Status: complete within the original implementation and small analytical pilot scope. All seven work packages and six mandatory acceptance criteria have supporting artifacts. Fresh execution found no missing implementation work. The phase brief's stale status and unchecked boxes are now corrected; its original snapshot and all earlier results remain preserved.

| Requirement | Verified evidence |
| --- | --- |
| Event semantics, sparse table and independent oracle | [17 fresh acceptance groups](tests_recheck_01/result.json), [test transcript](tests_recheck_01/unittest.txt), [event API](../../implementation/lookahead/events.py); exhaustive 121,600 oracle queries including repeated, pending, active and consumed gates |
| Exact legacy and separate generalized h1 | [Compatibility report](legacy_compatibility_report.md), eight exact instruction/RNG controls checked by the fresh gate, and freshly executed frozen-eviction controls |
| Parking score, legal snapshot anchors and unchanged integration | [Potential API](../../implementation/lookahead/potential.py), [parking hooks](../../implementation/lookahead/integration.py), [specification](lookahead_spec.md); uniform weights, optional critical-path weighting disabled, no future chosen placement access |
| Fixed small comparison and negative examples | [Pilot results](pilot_results.md), five configs for legacy and h1/2/4/8, gamma .9, separate quality seeds and timing repeats, hand-calculated compromise and fresh nonmonotonic-horizon checks |
| Independent validation and common model | [16 fresh model groups](model_recheck_01/result.json), [40 fresh schedule replays](../../runs/phase_04/replay_recheck_01/cached_replay.json); all accepted and every error budget identical to canonical evidence |
| Complexity, build/query timing and memory | [Specification](lookahead_spec.md) and [measurements](pilot_results.md), including separate sparse-index and verbose audit costs |
| Deliverables, handoff, provenance and document links | [29/29 fresh gate checks](gate_recheck_01.json), [handoff](../../handoffs/phase_04.md), [machine-readable review](completion_review.json) |

Fresh test hashes match the current implementation and configs. Fresh replay records match the canonical 40 records exactly. Previously saved h1/h4 full-original-QFT5 semantic checks and both CLI smokes remain intact and pass integrity checks; this review did not relabel them as freshly executed. No benchmark controller was started and no historical raw output was overwritten.

The pilot still has 34 ties and six worse error results relative to legacy, with no strict improvement. No best k is selected. Full matched benchmark evaluation, calibrated-device claims and Phase 01 completion remain outside Phase 04 acceptance. Phase 05 has not been started.

Commands were executed from the BTP workspace using the existing Python environment. Use fresh output paths when repeating them:

```powershell
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tests\phase_04_acceptance.py --out .\btp_work\reports\phase_04\tests_recheck_01
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tests\phase_03_acceptance.py --out .\btp_work\reports\phase_04\model_recheck_01
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\check_phase04.py --out .\btp_work\reports\phase_04\gate_recheck_01.json
& .\btp_work\.venv\Scripts\python.exe -B -X utf8 .\btp_work\tools\finalize_phase04_evidence.py --source-pilot .\btp_work\runs\phase_04\pilot_01 --out .\btp_work\runs\phase_04\replay_recheck_01
```
