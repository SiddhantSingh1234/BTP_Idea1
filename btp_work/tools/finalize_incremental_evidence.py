"""Freeze the incremental tranche without closing unresolved original phase gates."""
import csv
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase07_extension import read,write,sha


def text(path,value):
    path=ROOT/path;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    path.write_text(value,encoding='utf-8',newline='\n')


def csvsave(path,rows):
    path=ROOT/path;path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    delivery='final/research_delivery_20261031_v2'
    analysis='reports/phase_08/integrated_analysis_02'
    summary=read(ROOT/analysis/'summary.json')
    reused=read(ROOT/'reports/phase_07/reused_studies.json')
    gaps=[
        {'requirement':'QFT through100 with matched primary baselines','status':'unrun','reason':'existing full matched corpus ends at60; incremental factorial uses5/10; no new large-scale campaign claimed'},
        {'requirement':'Larger/deeper QAOA and quantum-volume scaling','status':'partial','reason':'new genuine circuits cover6/8 qubits, QAOA p2 and QV depth4; two instances per family'},
        {'requirement':'Critical-path versus equal future weighting','status':'unrun','reason':'accepted implementation and all fixed experiments use uniform event weights; no unimplemented comparison invented'},
        {'requirement':'Extended full-method profile-driven replanning and resource sweeps','status':'partial','reason':'fixed-trace9-setting transfer/T2 analysis and prior Phase03 heating/trajectory/cooling stress evidence are available; complete large-scale planner sweeps remain'},
        {'requirement':'Generalized runtime/memory scaling conclusions','status':'partial','reason':'existing QFT5–60 stage measurements and memory stress evidence exist; no universal asymptotic empirical claim'},
        {'requirement':'Native calibrated hardware validity and complete one-qubit physical timing','status':'unsupported','reason':'declared geometry and normalized CZ analytical scope; original-unitary proofs do not establish these physical quantities'},
        {'requirement':'Exact historical paper revision/options','status':'unresolved_provenance','reason':'accepted pinned-source scope preserves this limitation rather than claiming exact historical reproduction'},
        {'requirement':'Final accepted Idea1 report/release','status':'draft','reason':'editable report and presentation plus clean reproduction delivered; original Phase07/09 requirements remain open'}]
    coverage=[]
    for path,record in reused.items():coverage.append({'category':'reused_study','cell':path,'status':'reused_complete','rows':record['rows'],'evidence':path})
    for row in csv.DictReader((ROOT/'runs/idea1_extension_v1/campaign/results.csv').open(encoding='utf-8-sig')):
        coverage.append({'category':'new_factorial','cell':row['case']+'__s'+row['seed']+'__r'+row['repeat']+'__'+row['variant'],
                         'status':row['status'],'quality_sample':row['quality_sample'],'evidence':row.get('raw_result','')})
    for row in csv.DictReader((ROOT/'runs/idea1_extension_v1/primary_baselines/results.csv').open(encoding='utf-8-sig')):
        coverage.append({'category':'new_primary','cell':row['case']+'__s'+row['seed'],'status':row['status'],'quality_sample':True,'evidence':row.get('output','')})
    for gap in gaps:coverage.append({'category':'original_scope_gap','cell':gap['requirement'],'status':gap['status'],'evidence':gap['reason']})
    csvsave('reports/phase_07/coverage.csv',coverage);csvsave('final/scope_coverage.csv',gaps)
    claims=[
        {'id':'C01','claim':'Final pipeline reduces summed total E1.504%, equivalent to3.016% of transport-sensitive E','status':'supported_conditional','evidence':analysis+'/transport_budget.csv','limitation':'analytical fixed corpus;13/66 regressions remain'},
        {'id':'C02','claim':'h4 circuit-balanced mean improves while summed E worsens','status':'supported','evidence':analysis+'/clustered_comparisons.csv','limitation':'different weighting objectives; cluster interval crosses zero; no tuned best horizon'},
        {'id':'C03','claim':'Recorded standard composite repair is dominated by cheaper choices on45/66 targets','status':'supported_observational','evidence':analysis+'/pareto_choices.csv','limitation':'same-scope single noisy timing samples; no universal dominance theorem'},
        {'id':'C04','claim':'Quantum-volume lookahead null is explained by zero parking/eviction decisions in these examples','status':'supported_mechanism','evidence':'reports/phase_08/new_primary_analysis_01/summary.json','limitation':'two QV instances at6/8 qubits, depth4; not all quantum-volume circuits'},
        {'id':'C05','claim':'Component effects are not generally additive','status':'supported_conditional','evidence':analysis+'/factorial_effects.csv','limitation':'eight circuits/five seeds; saturated-system independent check; no population p-value'},
        {'id':'C06','claim':'Corrected DasAtom has lower E on all20 new QAOA/QV comparisons','status':'supported_conditional','evidence':'reports/phase_08/new_primary_analysis_01/new_primary_pairs.csv','limitation':'same model/input/geometry; different classical timer scopes; small workloads'},
        {'id':'C07','claim':'Hardware scorer assumptions change aggregate gain magnitude','status':'supported_conditional','evidence':analysis+'/sensitivity_summary.csv','limitation':'fixed schedules; does not optimize decisions under changed profiles'},
        {'id':'C08','claim':'Fresh environment reproduces tiny original semantics, full comparison and analysis tables','status':'supported','evidence':'final/reproduction_clean_01/verification.json','limitation':'quick workflow and representative aggregate rebuild, not a fresh full-suite campaign'},
        {'id':'C09','claim':'Universal superiority or calibrated native-device fidelity','status':'not_supported','evidence':'final/scope_coverage.csv','limitation':'must not appear as a report conclusion'},
        {'id':'C10','claim':'All original Phase07–09 requirements are complete','status':'not_supported','evidence':'final/completion_review.md','limitation':'scaling, weighting and remaining evaluation gates are explicitly open'}]
    csvsave('reports/phase_08/claims_evidence.csv',claims)
    text('reports/phase_08/results_and_discussion.md',f'''# Incremental results and discussion

The full report narrative and figures are in [the research draft](../../{delivery}/report/Research_Report_Draft.md), with [editable Word](../../{delivery}/report/Research_Report_Draft.docx), [PDF](../../{delivery}/report/Research_Report_Draft.pdf) and [presentation](../../{delivery}/presentation/Research_Presentation.pptx).

The new analysis adds circuit-cluster uncertainty and aggregation checks, transport-sensitive budgets, same-scope Pareto/cost effectiveness, nine fixed-trace hardware settings, paired grids and a complete four-family L/A/R factorial. It preserves1,980 old result rows and adds448 factorial outputs (320 quality,128 timing-only) plus20 new corrected DasAtom primary outputs. All new final schedules pass independent replay at their declared level; the new audit does not claim that every rejected proposal was independently recompiled.

RQ1: the existing132-row model study shows that movement accounting changes timing/error values without changing the original choices. Timing/exposure conventions also change, so this is not heating alone. RQ2: gains vary by horizon/aggregation; h4 has a favorable circuit-balanced mean but worse summed E, and QV examples have zero parking opportunities. RQ3: corrected assignment/candidate effects are conditional; fixed-candidate composite uncertainty crosses zero on the selected corpus. RQ4: repair protects its own parent and can improve full E while imposing high extra cost;45/66 standard-composite points are observationally dominated. RQ5: fixed-trace transfer/coherence sensitivity changes gain size, and prior resource-enabled cooling evidence adds hardware/time; complete large-scale robustness remains open.

Final-over-original summed E improves1.504%; transport-sensitive E improves3.016%. Corrected DasAtom has lower E on64/66 existing targets and all20 new QAOA/QV pairs. New QV lookahead effects are exactly zero, with all10 case/seed baselines reporting no parking or eviction. Saturated linear-system checks independently reproduce all40 factorial contrasts. Report positive, null and negative findings together.

[Claims ledger](claims_evidence.csv), [limitations](limitations.md), [related-work update](related_work_update.md), [analysis outputs](integrated_analysis_02/summary.json), [primary comparisons](new_primary_analysis_01/summary.json), and [analysis tests](tests_01/result.json) preserve exact evidence. Two circuits per new family and five routing seeds do not justify broad statistical generalization; circuit-cluster intervals condition on the selected corpus and exclude hardware calibration uncertainty.
''')
    text('reports/phase_08/limitations.md','''# Remaining limitations

The [coverage ledger](../../final/scope_coverage.csv) preserves unfinished original requirements. The incremental study does not close QFT-through100, large/deep new-family coverage or the unimplemented critical-path-weighting ablation. Existing heating/trajectory/cooling stress sweeps are reused as analytical examples, not presented as large-scale calibrated evaluation.

All scores concern normalized CZ skeletons under declared two-plane geometry and uncertain model parameters. Original-unitary restoration verifies semantics, not native one-qubit timing. Extra cooling banks/resources are hypothetical and distinct from algorithm gains. Corrected DasAtom is explicitly separate from native output. Exact manuscript revision/options remain unresolved under the accepted pinned-source scope.

There are27 distinct circuits across66 old circuit/grid targets; repeated grids/timing samples are dependent. Bootstrap intervals describe selected-corpus stability. The new four-family matrix has only two circuit instances per family and five routing seeds. All settings were frozen before final execution; no post-hoc best policy was deployed. Extra comparisons require their own predeclared protocol.

Classical timing scopes differ across algorithms/tracks. The same-scope Pareto and repair ratios are observational and subject to fixed order, host variability and limited repeats. Model sensitivities vary the scorer on fixed physical schedules and do not imply reoptimized decisions. All failure/OOM histories remain preserved, including the earlier Phase06 v1 memory failures.

The delivered report is an editable research draft. All Phases7–10 are being advanced, but incomplete original Phase7/9 gates and the Idea2 transition dependency remain visible. No Idea2 compiler or campaign was implemented.
''')
    text('final/README.md',f'''# Idea1 incremental research package

Latest report: [PDF]({delivery.removeprefix('final/')}/report/Research_Report_Draft.pdf), [editable Word]({delivery.removeprefix('final/')}/report/Research_Report_Draft.docx), [Markdown]({delivery.removeprefix('final/')}/report/Research_Report_Draft.md).
Latest presentation: [PowerPoint]({delivery.removeprefix('final/')}/presentation/Research_Presentation.pptx), [PDF]({delivery.removeprefix('final/')}/presentation/Research_Presentation.pdf), [speaker notes/source]({delivery.removeprefix('final/')}/presentation/Research_Presentation.md).

The existing full benchmark report is preserved. This increment adds only missing experiments, analysis and integration. [Completion review](completion_review.md), [scope ledger](scope_coverage.csv), [artifact index](artifact_index.json), [demo](demo.md), and [provenance](PROVENANCE.md). The original full-study gates remain open; these artifacts are a research draft and evidence package.

## Quick CPU-only reproduction

From btp_work, recreate an isolated environment with the pinned Python3.13.2 interpreter and original hash lock. The tested local uv path is used below; installing the exact lock with another installer is an alternative requiring its own verification.

```powershell
.\\.compiler-tools\\uv-0.9.5\\uv.exe --cache-dir .compiler-tools/uv-cache venv --python .venv/Scripts/python.exe final/repro_env_new
.\\.compiler-tools\\uv-0.9.5\\uv.exe --cache-dir .compiler-tools/uv-cache pip install --require-hashes --python final/repro_env_new/Scripts/python.exe -r configs/environment/requirements-py313-win64.lock
.\\final\\repro_env_new\\Scripts\\python.exe -B -X utf8 tools/reproduce_incremental_release.py --out final/reproduction_new
```

The actual [fresh-environment receipt](reproduction_clean_01/verification.json) verifies29 exact packages, separate sys.prefix/user-site exclusion, baseline/full-method compilation, independent validation/scoring, original QFT5 semantics and figure generation. Observed quick-workflow time was8.55seconds on this host; installation is separate. This is a small reproducibility workflow, not a full benchmark rerun or exact historical-paper reproduction.

## Rebuild aggregates without recompiling old benchmarks

```powershell
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/phase08_incremental.py --out reports/phase_08/rebuild_new --extension runs/idea1_extension_v1
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/phase08_primary.py --study runs/idea1_extension_v1 --out reports/phase_08/primary_rebuild_new
```

A clean-environment rebuild from a separate working directory is retained in reports/phase_09/clean_analysis_01 and checked byte-for-byte for every numerical CSV. Current scientific sources and all old result CSVs are unchanged. Use fresh output suffixes; immutable reports/runs are never overwritten. CSVs and manifests give relative artifact paths; source scripts resolve the project root from their own location.

## Rebuild the report/presentation

The separate .delivery-tools directory contains pinned python-pptx1.0.2, python-docx1.2.0 and their recorded dependencies. The builder reads checked analysis outputs, writes DOCX/PPTX plus offline HTML/Markdown, and uses no image-generation service. Headless Edge is required only for PDF rendering. In this environment, downloaded document-library files and the hidden browser required sandbox escalation; that is an access constraint, not a scientific dependency.

```powershell
.\\.venv\\Scripts\\python.exe -B -X utf8 tools/build_incremental_delivery.py --out final/delivery_new
.\\.venv\\Scripts\\python.exe -B -X utf8 tools/render_incremental_delivery.py --delivery final/delivery_new
```

The current builder uses integrated_analysis_02 and new_primary_analysis_01 explicitly. Study generation/execution is documented in reports/phase_07/study_protocol.md; full benchmark launch commands remain in ../BENCHMARK_COMMANDS.md. Do not launch a completed old matrix merely to regenerate a figure.
''')
    text('final/demo.md',f'''# Supervisor demo, approximately6minutes

1. Open [the deck]({delivery.removeprefix('final/')}/presentation/Research_Presentation.pptx) or its PDF. Introduce the question: when is better routing worth more compilation?
2. Show the reuse/new-work counts. Explain66 targets versus27 circuits and the distinction between320 quality and128 timing-only outputs.
3. Show the h4 aggregation reversal, then the transport-budget denominator and same-scope repair cost. Avoid selecting only a favorable metric.
4. Show the full factorial and zero-parking QV mechanism. Explain why a heuristic can be correct but have no opportunity to help.
5. Show the negative corrected-DasAtom result, the model-sensitivity range and the explicit remaining-study slide.
6. Run the small reproduction command from README if desired; explain that the clean receipt verifies all29 exact packages and original QFT5 semantics. Finish with the prepared Idea2 brief, not an unstarted implementation claim.

Key distinction: E reduction is not fidelity percentage points; full parent-safe repair is not universal superiority. The report is a draft until the open original gates in completion_review.md are resolved.
''')
    text('final/PROVENANCE.md','''# Provenance, environment and licenses

Original Papers and Proposal are read-only research inputs; Intern_Report was not used. All new work remains inside btp_work. Pinned RFT revision3d1f09233c2acd357fd9fbfad1b5300a921d301a and DasAtom revision73a6bdf0fd200b2733745211eaf2e0c1e17f496a retain their original source/licenses under vendor/. The source_review manifests retain PDF/repository identities. No upstream scientific file or old raw result is overwritten.

configs/environment/requirements-py313-win64.lock is the original29-package hash lock. The fresh final/repro_env environment was installed from that lock; it does not share the old site-packages directory. final/reproduction_clean_01 records exact versions and system identity. The Python interpreter itself remains the project-pinned CPython3.13.2 distribution; Windows/CPU-only requirements and the owned process-family launcher are documented.

Document generation is isolated in .delivery-tools: python-pptx1.0.2, python-docx1.2.0, lxml6.1.3, Pillow13.0.0, XlsxWriter3.3.1, typing-extensions4.16.0. These do not alter the research lock. Their package metadata/license files remain installed. Editable scientific figures are standard Matplotlib PNG/SVG/PDF, not generated illustrations. PDF rendering uses an isolated local hidden Edge profile; profile caches are excluded from the scientific artifact index.

The artifact index binds new code, protocols, small receipts, report/slide sources and release files. Large experiment and old-source trees remain in place with their own manifests, rather than being recopied. Manuscript/benchmark redistribution terms are not changed by this package. Citation/source versions and primary links are in the report and related-work update.
''')
    review='''# Completion review: incremental Phases7–10 work

Date:31 October2026. This tranche is delivered and independently checked. It does **not** mark the original complete Idea1 study finished.

| Phase | Delivered in this tranche | Original phase status / remaining work |
| --- | --- | --- |
| 07 | audited reuse of five old matrices; complete448-row four-family factorial,20 new corrected-DasAtom baselines, frozen inputs/caps and coverage | in_progress: QFT-through100, broader scaling/weighting and remaining protocol axes |
| 08 | circuit-cluster uncertainty, aggregation reversal, transport budgets, repair Pareto/cost, factorial mechanisms, primary comparisons and model sensitivity; five analysis tests | in_progress: conclusions remain qualified by missing original Phase07 evidence |
| 09 | editable9-page report draft,13-slide deck with notes, PDFs, artifact index/provenance, fresh29-package environment and clean numerical rebuild | in_progress: full final report/release cannot close before required study gates |
| 10 | four actual Idea2 brief documents and installed VF2 API feasibility probe | in_progress/prepared: final accepted Idea1 release dependency remains; no Idea2 implementation/campaign |

All448 new factorial outputs validate. Independent auditing replayed211 distinct schedule hashes and checked every448 rows,56 attempts,840 recorded candidate trials and141 accepted repairs. The accepted-repair/trap counts include timing repetitions and are not independent quality sample counts. The new audit checks trial evidence but does not claim independent recompilation of every rejected candidate. The20 new primary outputs are independently replayed, with full tiny semantic proofs.

Five extension acceptance groups and five independent analysis groups pass. The saturated linear-system oracle reproduces40 factorial contrasts. All old result CSV hashes and frozen scientific module hashes are unchanged. The original full benchmark campaigns were not rerun.

The fresh reproduction uses a separate CPython3.13.2 environment and all29 exact hash-locked research packages. It compiles/checks/scores original/full-method QFT5, verifies32 basis columns and generates a figure. A separate clean-directory analysis rebuild reproduces all numerical CSVs exactly. PDF/layout verification checks all13slides and the report, without hidden network assets. These reproduce a representative workflow and analysis, not an unperformed full-suite experiment.

All unresolved scope items are machine-readable in [scope_coverage.csv](scope_coverage.csv). They have not been removed, made optional or checked off as complete. The report names these gaps and keeps positive/null/negative results. The [artifact index](artifact_index.json) and [incremental verification](../reports/phase_09/incremental_verification.json) bind delivered evidence. Original Phase7–9 completion remains a separate gate.
'''
    text('final/completion_review.md',review)
    handoffs={
        '07':'''# Phase07 incremental handoff

Owner:Codex /root,31 October2026. Original phase status:in_progress. This completed tranche reuses five old matrices without reruns and adds the frozen four-family factorial (448 accepted rows,320 quality/128 timing-only) and20 new QAOA/QV DasAtom baselines. [Protocol](../reports/phase_07/study_protocol.md), [capabilities](../reports/phase_07/baseline_capabilities.md), [coverage](../reports/phase_07/coverage.csv), [acceptance](../reports/phase_07/extension_tests_01/result.json), [independent audit](../reports/phase_07/extension_audit_01/verification.json).

Five paired routing seeds and fixed expanded candidates isolate L/A/R. A private legacy-entry guard permits the existing exact picker; all224 executed baseline preparations match untouched compiler instructions/RNG. Two identical pilot jobs are imported by hash to avoid duplicate work. Source revisions/configs remain frozen. Fresh primary comparisons use the same normalized input, physical geometry and scorer, with timer-scope differences retained.

All new final schedules pass their claimed declared-model checks. Existing bad/timeout/OOM histories are preserved. Rejected candidate plans are audited, not all independently recompiled here. QFT-through100, broad scale/depth and unperformed weighting axes remain open in final/scope_coverage.csv. The study is a completed incremental experiment, not closure of the complete original Phase07.
''',
        '08':'''# Phase08 incremental analysis handoff

Owner:Codex /root,31 October2026. Status:in_progress pending remaining original-study evidence. [Results](../reports/phase_08/results_and_discussion.md), [claims ledger](../reports/phase_08/claims_evidence.csv), [limitations](../reports/phase_08/limitations.md), [related work](../reports/phase_08/related_work_update.md), [tests](../reports/phase_08/tests_01/result.json).

New evidence: circuit-cluster bootstrap over27 circuit identities, explicit weighting-dependent conclusions, native/transport budget decomposition, same-scope repair cost/Pareto, matched grids,9-setting fixed-trace transfer/coherence sensitivity, complete four-family factorial interactions and20 new primary pairs. Main supported findings: total/transport-sensitive E reductions1.504%/3.016%; h4 aggregation reversal; observationally dominated standard repair on45/66 targets; QV null from zero parking; corrected DasAtom wins all20new pairs. These are conditional, not universal or calibrated-device results.

analysis/phase08_incremental.py and analysis/phase08_primary.py regenerate aggregates from immutable records. The final integrated_analysis_02 differs from01 only by legible heatmap label color; numeric tables are byte-identical and the older script is archived. Independent saturated linear-system tests reproduce all40factorial contrasts. A clean environment/directory rebuild reproduces numerical CSVs. Final report/deck sources and all sample/uncertainty definitions are linked in final/README.md. Do not silently pool grids/seeds/repeats as independent circuits.
''',
        '09':'''# Phase09 integration handoff

Owner:Codex /root,31 October2026. Status:in_progress; deliverable is an explicitly labelled research draft. [Package README](../final/README.md), [completion review](../final/completion_review.md), [artifact index](../final/artifact_index.json), [demo](../final/demo.md), [provenance](../final/PROVENANCE.md).

Delivered editable Word/Markdown/offline HTML report and native PowerPoint with13slides/speaker notes, plus checked PDF exports and scientific figure formats. Existing full benchmark report remains unchanged. final/research_delivery_20261031_v2 is the current draft; earlier version is retained. The report preserves observed losses and original remaining gates. No external publication or message was sent.

The fresh final/repro_env installs29exact packages from the original hash lock. final/reproduction_clean_01 independently compiles, validates, scores, restores original QFT5 semantics and regenerates a figure; reports/phase_09/clean_analysis_01 rebuilds numerical results from raw inputs in that separate environment/workdir. Browser checks verify layout/offline assets; PDF checks verify9report pages/13slides. Separate document libraries do not modify scientific dependencies.

Required large-scale comparisons/weighting remain incomplete, so full Idea1/Phase09 completion is not claimed. Read final/scope_coverage.csv before drafting submission claims. Code and dataset versions are in the artifact index, original studies keep their own frozen manifests, and quick/full reproduction scopes stay distinct.
''',
        '10':'''# Phase10 prepared transition handoff

Owner:Codex /root,31 October2026. Status:in_progress/prepared. The user's request authorized preparing Phases7–10; Idea1's unfinished original gates and draft release remain preserved, with no research-direction switch or Idea2 implementation.

[START_HERE](../idea2/START_HERE.md), [reuse map](../idea2/REUSE_MAP.md), [initial plan](../idea2/INITIAL_PLAN.md), [first QFT5 experiment](../idea2/FIRST_EXPERIMENT.md), [installed API probe](../idea2/api_probe.json).

The brief matches proposal Idea2: bounded DasAtom embedding candidates and transition-cost sequence DP. Pinned source, unchanged partition/router controls, D4/translation legality, full-register candidates, K=1 recovery, deterministic VF2 call/candidate/wall bounds and exhaustive tiny DP tests are specified. Installed rustworkx0.15.1 has call_limit but no previous-layout ordering callback; that unresolved implementation choice is explicit. Layout-only DP cannot exactly optimize history-dependent full error/RNG state.

The exact QFT5input/hash, paper example and semantic/physical checks are provided. One logical exchange is not called one physical shuttle. Final accepted Idea1release remains a dependency; no arbitrary final tag is invented. Full Idea2implementation should begin only on user instruction.
'''}
    for phase,value in handoffs.items():text('handoffs/phase_'+phase+'.md',value)
    # Current status updates supplement, rather than erase, historical checkpoints.
    p=ROOT/'plan/STATUS.md';s=p.read_text(encoding='utf-8')
    replacements={
        '07':'| 07 | in_progress | Codex /root | Accepted06; reused full matrices |448new factorial outputs/20new primary baselines accepted; source reuse/coverage frozen; original QFT100/weighting/scale gates remain open |',
        '08':'| 08 | in_progress | Codex /root | Frozen incremental07 | Cluster uncertainty, factorial/primary analysis, Pareto/error budgets/sensitivity and5test groups delivered; remaining original-study evidence limits closure |',
        '09':'| 09 | in_progress | Codex /root | Qualified08 evidence | Editable9-page report draft and13-slide deck/PDF; fresh29-package reproduction and clean analysis pass; full release awaits remaining gates |',
        '10':'| 10 | in_progress | Codex /root | User-authorized brief preparation | Four Idea2documents and pinned VF2API probe delivered; original Idea1final release still pending; no Idea2implementation |'}
    for phase,line in replacements.items():s=re.sub(r'^\| '+phase+r' \|.*$',line,s,flags=re.M)
    s+='''\n## Incremental Phases7–10,31 October2026\n\nThe [completion review](../final/completion_review.md), [package](../final/README.md), [Phase07handoff](../handoffs/phase_07.md) and [claims ledger](../reports/phase_08/claims_evidence.csv) record the new work. All five old datasets are reused unchanged;448factorial and20new DasAtom outputs are accepted. Current report/presentation are editable drafts. The original full-study requirements remain open and visible in [scope coverage](../final/scope_coverage.csv). No original phase gate is closed by relabelling incomplete scope.\n'''
    p.write_text(s,encoding='utf-8',newline='\n')
    p=ROOT/'README.md';s=p.read_text(encoding='utf-8');i=s.index('\n')+1
    block='''\n<!-- BEGIN PHASE07_10 INCREMENTAL -->\n31 October2026: incremental Phases7–10 work adds448validated four-family factorial outputs,20new corrected-DasAtom comparisons, cluster-aware analysis and an editable report/presentation package. Existing completed matrices are reused unchanged. [Open package](final/README.md), [completion review](final/completion_review.md), [claims](reports/phase_08/claims_evidence.csv), [Idea2brief](idea2/START_HERE.md). The original Phase7/9full-study gates remain in progress; the report is a draft and no Idea2compiler has been started.\n<!-- END PHASE07_10 INCREMENTAL -->\n'''
    p.write_text(s[:i]+block+s[i:],encoding='utf-8',newline='\n')
    for phase,name in [('07','07_EXPERIMENTS.md'),('08','08_ANALYSIS.md'),('09','09_FINAL_DELIVERY.md'),('10','10_IDEA2_TRANSITION.md')]:
        p=ROOT/'plan/phases'/name;s=p.read_text(encoding='utf-8').replace('**Status:** not started.','**Status:** in progress; incremental work is documented in [handoff](../../handoffs/phase_'+phase+'.md). Original unmet gates remain open.')
        p.write_text(s,encoding='utf-8',newline='\n')
    # Complete the artifact inventory only after all build outputs and docs exist.
    inventory=[]
    for folder in [ROOT/delivery/'report',ROOT/delivery/'presentation',ROOT/delivery/'figures']:
        inventory.extend(p for p in folder.rglob('*') if p.is_file())
    for folder in ['reports/phase_07','reports/phase_08','idea2']:
        inventory.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ['.md','.csv','.json','.py','.pdf','.png','.svg','.txt'])
    inventory += [ROOT/'analysis/phase08_incremental.py',ROOT/'analysis/phase08_primary.py']
    inventory += [ROOT/'tools'/name for name in ['phase07_extension.py','run_phase07_incremental.py','phase07_new_primary.py','audit_phase07_extension.py',
        'reproduce_incremental_release.py','build_incremental_delivery.py','render_incremental_delivery.py','finalize_incremental_evidence.py']]
    inventory += [ROOT/'tests/phase07_extension_acceptance.py',ROOT/'tests/phase08_incremental_acceptance.py',
        ROOT/'runs/idea1_extension_v1/protocol.json',ROOT/'runs/idea1_extension_v1/campaign/results.csv',
        ROOT/'runs/idea1_extension_v1/primary_baselines/results.csv',ROOT/'final/reproduction_clean_01/verification.json',
        ROOT/'configs/environment/requirements-py313-win64.lock']
    inventory += [ROOT/'handoffs'/('phase_'+phase+'.md') for phase in ['07','08','09','10']]
    inventory += [ROOT/'final'/name for name in ['README.md','completion_review.md','PROVENANCE.md','demo.md','scope_coverage.csv']]
    write(ROOT/'final/artifact_index.json',{'schema':'incremental_release.v1','release_directory':delivery,
        'original_study_complete':False,'artifact_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(inventory))},
        'old_study_source_sha256':{name:record['sha256'] for name,record in reused.items()},
        'excluded':'virtualenv/site-packages and isolated browser caches; old large raw artifacts retain their own manifests',
        'environment_lock':'configs/environment/requirements-py313-win64.lock'})
    # Gate this tranche separately from the original full-study acceptance.
    checks={}
    checks['five_old_datasets_unchanged']=all(sha(ROOT/name)==record['sha256'] for name,record in reused.items())
    protocol=read(ROOT/'runs/idea1_extension_v1/protocol.json')
    checks['frozen_scientific_sources_unchanged']=all(sha(ROOT/name)==digest for name,digest in protocol['artifact_sha256'].items())
    checks['five_extension_tests_pass']=read(ROOT/'reports/phase_07/extension_tests_01/result.json')['successful']
    checks['five_analysis_tests_pass']=read(ROOT/'reports/phase_08/tests_01/result.json')['successful']
    audit=read(ROOT/'reports/phase_07/extension_audit_01/verification.json')
    checks['all448_new_final_rows_audited']=audit['status']=='ok' and audit['accepted_rows']==448
    checks['twenty_new_primary_outputs_pass']=read(ROOT/'runs/idea1_extension_v1/primary_baselines/summary.json')['accepted']==20
    checks['primary_semantic_and_physical_replays_pass']=read(ROOT/'reports/phase_08/new_primary_analysis_01/summary.json')['all_new_primary_outputs_independently_replayed']
    checks['fresh29_package_workflow_pass']=read(ROOT/'final/reproduction_clean_01/verification.json')['all_29_exact_packages_match']
    numerical=[p.name for p in (ROOT/analysis).glob('*.csv')]
    checks['clean_environment_numerical_rebuild_identical']=all((ROOT/analysis/name).read_bytes()==(ROOT/'reports/phase_09/clean_analysis_01'/name).read_bytes() for name in numerical)
    checks['report_and_slide_layout_pass']=read(ROOT/delivery/'render_checks/verification.json')['passed']
    checks['editable_deck_and_report_present']=(ROOT/delivery/'presentation/Research_Presentation.pptx').is_file() and (ROOT/delivery/'report/Research_Report_Draft.docx').is_file()
    checks['all_four_idea2_briefs_present']=all((ROOT/'idea2'/name).is_file() for name in ['START_HERE.md','REUSE_MAP.md','INITIAL_PLAN.md','FIRST_EXPERIMENT.md'])
    checks['claims_and_remaining_scope_explicit']=len(claims)==10 and len(gaps)==8
    checks['artifact_index_hashes_match']=all(sha(ROOT/name)==digest for name,digest in read(ROOT/'final/artifact_index.json')['artifact_sha256'].items())
    issues=[];docs=[ROOT/'final'/name for name in ['README.md','completion_review.md','demo.md']]
    docs += [ROOT/'handoffs'/('phase_'+phase+'.md') for phase in ['07','08','09','10']]
    docs += list((ROOT/'idea2').glob('*.md'))+list((ROOT/'reports/phase_07').glob('*.md'))+list((ROOT/'reports/phase_08').glob('*.md'))
    for doc in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
            path=(doc.parent/target.partition('#')[0]).resolve()
            if not path.exists() and path!=ROOT/'reports/phase_09/incremental_verification.json':issues.append({'document':doc.relative_to(ROOT).as_posix(),'target':target})
    checks['current_document_links_resolve']=not issues
    verification={'status':'incremental_work_complete' if all(checks.values()) else 'needs_revision',
        'original_phase07_09_status':'in_progress','checks':checks,'passed':sum(checks.values()),'total':len(checks),
        'link_issues':issues,'numeric_csvs_reproduced':len(numerical),'current_delivery':delivery,
        'script_sha256':sha(Path(__file__))}
    write(ROOT/'reports/phase_09/incremental_verification.json',verification)
    print(json.dumps(verification));return 0 if all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
