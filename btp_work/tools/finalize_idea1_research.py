"""Close the bounded Idea1 research scope after every evidence gate passes.

Writes Markdown and indexes only. Preserves the user's existing formal report
and presentation, whose future required format has not yet been supplied.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'analysis')]
sys.dont_write_bytecode=True
from phase08_incremental import rows,csvsave
from audit_idea1_completion import read,write,sha

MAIN=ROOT/'runs/remaining_experiments_6h_v2'
FOLLOW=ROOT/'runs/idea1_completion_followup_v1'
ANALYSIS=ROOT/'reports/phase_08/completion_final_01'
RELEASE=ROOT/'final/idea1_research_release_v1'
ARCHIVE=ROOT/'reports/phase_09/before_completion_01'


def md(path,text):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(text.rstrip()+'\n',encoding='utf-8')


def rel(path,origin=RELEASE):return os.path.relpath(path,origin).replace('\\','/')


def rebase(text,source,target):
    def replace(match):
        name,link=match.group(1),match.group(2)
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):return match.group(0)
        link=link.replace('completion_initial_02/','completion_final_01/')
        path,sep,anchor=link.partition('#')
        return '['+name+']('+rel((source/path).resolve(),target)+(sep+anchor if sep else '')+')'
    return re.sub(r'\[([^\]]*)\]\(([^)]+)\)',replace,text)


def table(data,keys):
    from idea1_final_analysis import table_markdown
    return table_markdown(data,keys)


def checked_receipt(relative,csv=None):
    value=read(ROOT/relative)
    assert value.get('status')=='ok',relative
    if csv:assert value['results_sha256']==sha(csv),relative
    return value


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--finalize',action='store_true',required=True);parser.parse_args()
    if RELEASE.exists():raise FileExistsError('Final release already exists; preserve it')
    before=read(ARCHIVE/'preservation_receipt.json')
    checks={}
    for name,record in read(ROOT/'reports/phase_07/reused_studies.json').items():assert sha(ROOT/name)==record['sha256']
    checks['five_prior_studies_unchanged']=True
    manifest,follow_manifest=read(MAIN/'manifest.json'),read(FOLLOW/'manifest.json')
    assert manifest['frozen_files']==follow_manifest['frozen_files']
    for name,digest in manifest['frozen_files'].items():
        assert sha(MAIN/'frozen'/name)==sha(FOLLOW/'frozen'/name)==sha(ROOT/name)==digest,name
    checks['all_99_scientific_runtime_files_unchanged']=True
    mainrows,followrows=rows(MAIN/'results.csv'),rows(FOLLOW/'results.csv')
    assert len(mainrows)==529 and len(followrows)==30
    assert all(r['status'] in {'ok','timeout','unsupported','reused_quality'} for r in mainrows)
    assert all(r['status'] in {'ok','timeout','out_of_memory'} for r in followrows)
    assert read(MAIN/'summary.json')['all_cells_terminal'] and read(FOLLOW/'summary.json')['all_cells_terminal']
    assert {r['id'] for r in followrows}=={r['id'] for r in mainrows if r['status']=='timeout'}
    assert follow_manifest['original_csv_sha256']==sha(MAIN/'results.csv')
    spent=read(MAIN/'budget.json')['spent_seconds']+read(FOLLOW/'budget.json')['spent_seconds']
    assert spent<=21600,spent
    checks['every_planned_cell_terminal_within_original_experiment_budget']=True
    main_audit=checked_receipt('reports/phase_07/completion_audit_02/verification.json',MAIN/'results.csv')
    follow_audit=checked_receipt('reports/phase_07/completion_followup_audit_01/verification.json',FOLLOW/'results.csv')
    checked_receipt('reports/phase_07/completion_envelopes_01/verification.json',MAIN/'results.csv')
    checks['all_successful_final_schedules_independently_replayed']=True
    checks['exact_circuit_register_and_launcher_envelopes_checked']=True
    analysis=checked_receipt('reports/phase_08/completion_final_01/summary.json')
    assert analysis['input_sha256'][str((FOLLOW/'results.csv').relative_to(ROOT))]==sha(FOLLOW/'results.csv')
    checked_receipt('reports/phase_08/hardware_counterfactual_02/verification.json',MAIN/'results.csv')
    checked_receipt('reports/phase_08/mechanism_audit_01/verification.json',MAIN/'results.csv')
    checked_receipt('reports/phase_08/snapshot_accounting_01/verification.json')
    checks['matched_profile_analysis_and_null_scaling_mechanisms_saved']=True
    assert read(ROOT/'reports/phase_08/completion_tests_01/result.json')['groups_passed']==5
    assert read(ROOT/'reports/phase_09/clean_completion_weighting_tests_01/result.json')['successful']
    assert read(ROOT/'reports/phase_09/clean_completion_analysis_tests_01/result.json')['groups_passed']==5
    clean=checked_receipt('reports/phase_09/completion_clean_rebuild_01/verification.json')
    assert clean['all_numerical_csvs_identical'] and clean['hardware_counterfactual_csvs_identical']
    checks['new_tests_and_clean_environment_rebuild_pass']=True
    assert read(ROOT/'final/reproduction_clean_01/verification.json')['all_29_exact_packages_match']
    for phase in ['04','05','06']:assert read(ROOT/f'reports/phase_{phase}/gate_01.json')['status']=='complete'
    checks['accepted_implementation_and_tiny_reproduction_gates_retained']=True
    for source in read(ROOT/'source_review/manifest.json'):
        assert sha(ROOT.parent/source['source'])==source['sha256']
    checks['original_papers_and_proposal_unchanged']=True
    for name,digest in before['protected_existing_report_presentation_files'].items():assert sha(ROOT/name)==digest,name
    checks['all_278_existing_report_and_presentation_files_unchanged']=True
    for name in ['START_HERE.md','REUSE_MAP.md','INITIAL_PLAN.md','FIRST_EXPERIMENT.md']:
        assert (ROOT/'idea2'/name).is_file()
    checks['idea2_transition_brief_exists_without_new_implementation']=True
    recovery=read(FOLLOW/'logging_recovery_provenance.json')
    assert recovery['post_recovery_csv_sha256']==sha(FOLLOW/'results.csv')
    assert recovery['scientific_worker_changed'] is False and recovery['budget_extended'] is False
    for name,digest in recovery['affected_records'].items():assert sha(ROOT/name)==digest
    checks['infrastructure_interruption_preserved_and_recovered']=True

    RELEASE.mkdir(parents=True)
    stamp=datetime.now(timezone.utc).isoformat()
    # Formal report and presentation are deliberately absent from this release.
    research=(ROOT/'reports/phase_08/completion_research_notes.md').read_text(encoding='utf-8')
    research=research.replace('# Idea 1: interpretation of the completed non-scaling analyses','# Idea 1: final research analysis',1)
    research=research.replace('This note records scientific conclusions from the original matrices, the frozen factorial extension, and the 529-cell bounded campaign. The higher-cap QFT follow-up has a separate ledger and must finish before the final release is accepted. Formal report and presentation formatting is deferred by the user\'s instruction; these are reusable research notes.',
        'The agreed bounded Idea1 research programme is complete. Every planned experiment has a terminal outcome, all accepted final schedules have passed independent replay, and the analyses are saved here with their limitations. Timeouts and finite-resource failures remain results. The formal report and presentation will be formatted later as the user requested; this is the final Markdown research source.')
    research=rebase(research,ROOT/'reports/phase_08',RELEASE)
    scale=[r for r in analysis['scale'] if r['scope']=='after_cap_only_followup']
    initial=[r for r in analysis['scale'] if r['scope']=='initial_caps']
    research+='\n\n## Final QFT scaling outcomes\n\n'
    research+='The initial 64-cell matrix and all 30 cap-only follow-up cells are terminal. The complete original timing ledger is preserved. Only time limits changed; scientific code, inputs, options, geometry and routing seeds remained frozen. Completed-only quality below uses matched successful pairs and says nothing about the unobserved quality of censored cases.\n\n'
    research+=table(initial+scale,['scope','variant','planned','ok','timeout','out_of_memory','completed_median_wall_seconds','all_attempts_max_observed_peak_GiB','min_cap_seconds','max_cap_seconds'])+'\n\n'
    research+=table(analysis['scale_quality'],['comparison','paired_rows','better','tie','worse','equal_generator_mean_relative_E_percent'])+'\n\n'
    proposed=next(r for r in scale if r['variant']=='proposed_small')
    research+=f"The proposed-small implementation completes {proposed.get('ok',0)}/16 large-QFT cells under the higher finite caps, times out on {proposed.get('timeout',0)}/16 and has {proposed.get('out_of_memory',0)} memory-guard stops. These are method-specific limits, not an equal-time contest. Full-replay safety does not imply practical scalability. The measured P×Q prefix representation and complete recompilation provide concrete cost mechanisms; they do not establish how a redesigned implementation would behave.\n\n"
    research+='A monitor-level Windows atomic-log-write error is retained in the attempt history and retried with a bounded logging-only I/O shim. It is not an algorithm failure or an accepted timing/quality sample. No successful old result was rerun to improve its score.\n\n'
    research+=f"Cumulative experiment-controller time is {spent/3600:.3f} hours within the original six-hour budget. Independent post-run audits and analysis are separate verification costs. [Full final tables]({rel(ANALYSIS/'analysis.md')}), [raw initial coverage]({rel(MAIN/'results.csv')}), [raw follow-up coverage]({rel(FOLLOW/'results.csv')}), and [completion gate](completion_gate.json) bind this conclusion.\n"
    md(RELEASE/'RESEARCH_ANALYSIS.md',research)
    complexity=rebase((ROOT/'reports/phase_08/completion_complexity.md').read_text(encoding='utf-8'),ROOT/'reports/phase_08',RELEASE)
    md(RELEASE/'COMPLEXITY_AND_COST.md',complexity)
    shutil.copytree(ANALYSIS/'figures',RELEASE/'figures')
    csvsave(RELEASE/'coverage_initial.csv',mainrows);csvsave(RELEASE/'coverage_followup.csv',followrows)

    scope=[
      {'requirement':'QFT through100 with matched primary baselines','status':'complete_bounded_measurement','evidence':'coverage_initial.csv; coverage_followup.csv','qualification':'all 64 initial cells plus all30 time-limit follow-ups; censors remain failures to finish, not successful proposed quality'},
      {'requirement':'Larger/deeper genuine QAOA and QV','status':'complete','evidence':rel(ANALYSIS/'new_workload_summary.csv'),'qualification':'N10/12,p2/4 or depth8/16; eight cases but four generator clusters; three paired router seeds'},
      {'requirement':'Critical-path/equal weighting and discount controls','status':'complete','evidence':rel(ANALYSIS/'weighting_summary.csv'),'qualification':'120 new cells,24 shared quality controls; fixed gamma .5/.9/1; no tuned winner'},
      {'requirement':'Expanded-candidate assignment term removal','status':'complete','evidence':rel(ANALYSIS/'assignment_term_summary.csv'),'qualification':'96 cells; null output mechanisms checked using saved matrices'},
      {'requirement':'Profile-driven replanning and finite cooling resources','status':'complete','evidence':rel(ANALYSIS/'hardware_summary.csv'),'qualification':'120 profile-matched counterfactuals;9 cooling transforms,5 legitimate resource failures'},
      {'requirement':'Horizon, objectives, candidates, repair budgets, factorial interactions','status':'complete_reused','evidence':rel(ROOT/'reports/phase_08/integrated_analysis_02/summary.json'),'qualification':'immutable prior matrices and448-row extension; timings/repeats/circuit units remain separate'},
      {'requirement':'Runtime/memory scaling and failure mechanisms','status':'complete_bounded_analysis','evidence':'COMPLEXITY_AND_COST.md','qualification':'measured stages andP×Q diagnostic representation; no universal empirical asymptotic claim'},
      {'requirement':'Extra compiler baseline capability assessment','status':'complete_feasibility_assessment','evidence':rel(ROOT/'reports/phase_07/baseline_capabilities.md'),'qualification':'Enola/Atomique architectures lack an established matched adapter; no incomparable ranking'},
      {'requirement':'Reproducibility, evidence, claims and research release','status':'complete','evidence':'completion_gate.json; REPRODUCE.md','qualification':'fresh29-package tiny reproduction plus clean new numerical rebuild'},
      {'requirement':'Formal report and presentation formatting','status':'deferred_by_user','evidence':'COMPLETION_REVIEW.md','qualification':'explicit user instruction to save analysis inMarkdown and wait for the required document format'},
      {'requirement':'Native calibrated hardware validity and one-qubit physical timing','status':'accepted_scope_limitation','evidence':'RESEARCH_ANALYSIS.md','qualification':'declared analytical CZ-skeleton scope; never claimed measured device fidelity'},
      {'requirement':'Exact historical paper revision/options','status':'accepted_provenance_limitation','evidence':rel(ROOT/'reports/final_benchmark_analysis_01/report.md'),'qualification':'D001/D005/D006 pinned-source scope; paper discrepancies retained'},
      {'requirement':'Idea2 transition brief','status':'complete_brief_only','evidence':rel(ROOT/'idea2/START_HERE.md'),'qualification':'no Idea2 implementation/campaign was requested or started'}]
    csvsave(RELEASE/'scope_coverage.csv',scope)
    md(RELEASE/'COMPLETION_REVIEW.md',f'''# Idea1 research completion review

Accepted scope: the user's finite five-to-six-hour experiment portfolio, controlled analysis and Markdown research package. This review is generated only after all evidence gates pass. Finished {stamp}.

| Phase | Final state | Evidence |
| --- | --- | --- |
| 00–03 | Previously complete within pinned-source/analytical scope | Original handoffs,132 baseline/model rows and independent reconstruction retained |
| 04–06 | Previously complete; full matrices and safe repair checks retained | Original gates and unchanged396/792/528-row matrices |
| 07 | Complete bounded experiment programme | 529 initial cells,30 cap-only follow-ups, all terminal; independent final replays and frozen-source hashes |
| 08 | Complete research analysis | All five RQs answered; positive/null/negative outcomes, uncertainty, matched profiles, mechanisms and scaling saved |
| 09 | Complete Markdown research release | Fresh environment checks, reproducible aggregates, provenance, claims, indexes and current gate |
| 10 | Complete Idea2 transition brief | Four proposal-matched documents, pinned reuse map and feasible first test; no Idea2 implementation |

There are no pending experimental cells or required research analyses in this agreed bounded programme. A timeout is a completed censored experiment and an unsuccessful compiler completion at that cap; five unsupported cooling configurations are finite-resource outcomes. Neither is converted into a successful result. Native calibration and historical-paper identity remain accepted scientific limitations.

The user explicitly instructed: “report and presentation are to be built in a specific manner i will tell later on how to do them just analyse and save in markdown”. Formal report and presentation formatting is therefore deferred. Existing report/presentation files are preserved byte-for-byte and are historical drafts, not the current research source. This package does not claim that the institution-formatted thesis or presentation is finished.

Cumulative experiment-controller time: {spent/3600:.3f} hours out of six. Post-run audits/analysis are recorded separately. Initial outcomes: {dict(Counter(r['status'] for r in mainrows))}. Follow-up outcomes: {dict(Counter(r['status'] for r in followrows))}. Independent replay receipts cover {main_audit['accepted_rows']} initial accepted/reused rows and {follow_audit['accepted_rows']} accepted follow-up rows.

[Scope-by-requirement ledger](scope_coverage.csv), [research conclusions](RESEARCH_ANALYSIS.md), [complexity/cost](COMPLEXITY_AND_COST.md), [regeneration](REPRODUCE.md), and [machine-readable gate](completion_gate.json). Prior planning/current documents are archived at `{rel(ARCHIVE)}`; raw failed attempts are retained.
''')
    md(RELEASE/'REPRODUCE.md',f'''# Reproduce the Idea1 research evidence

Run from `btp_work` with pinned CPython3.13.2 and the original29-package hash lock. Use fresh output names: scripts refuse to overwrite earlier studies/analyses. Scientific sources are preserved in each study's frozen directory. No internet, browser, document library or active agent is required for aggregate regeneration.

```powershell
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/idea1_hardware_counterfactuals.py --out reports/phase_08/hardware_counterfactual_new
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/idea1_final_analysis.py --out reports/phase_08/completion_rebuild_new
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/idea1_mechanism_audit.py --out reports/phase_08/mechanism_rebuild_new
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/idea1_snapshot_accounting.py --out reports/phase_08/snapshot_rebuild_new
.\\.venv\\Scripts\\python.exe -B -X utf8 tests/idea1_completion_analysis_acceptance.py --out reports/phase_08/completion_tests_new
```

The main final analysis deliberately binds the accepted `hardware_counterfactual_02` by its source CSV hash; the first command independently reconstructs that calculation for comparison. It regenerates all completion-study numerical CSVs and scientific SVG/PDF/PNG figures from frozen raw data. The mechanism audit reads existing matrices rather than compiling again. The snapshot audit streams about1.7GB of existing JSON without loading gigabyte objects.

For the earlier132/396/792/528-row matrices and the448-row factorial:

```powershell
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/phase08_incremental.py --out reports/phase_08/old_aggregate_rebuild_new --extension runs/idea1_extension_v1
.\\.venv\\Scripts\\python.exe -B -X utf8 analysis/phase08_primary.py --study runs/idea1_extension_v1 --out reports/phase_08/old_primary_rebuild_new
```

An independent schedule replay of the initial portfolio takes roughly11minutes on this host and streams14.75GB of recorded artifacts. This is verification cost, not compilation timing:

```powershell
.\\.venv\\Scripts\\python.exe -B -X utf8 tools/audit_idea1_completion.py --study runs/remaining_experiments_6h_v2 --out reports/phase_07/replay_initial_new
.\\.venv\\Scripts\\python.exe -B -X utf8 tools/audit_idea1_completion.py --study runs/idea1_completion_followup_v1 --out reports/phase_07/replay_followup_new
```

For a small original/full-method compile, validation,32-column original QFT5 semantic proof and figure:

```powershell
.\\.venv\\Scripts\\python.exe -B -X utf8 tools/reproduce_incremental_release.py --out final/reproduction_new
```

The tested clean environment is `final/repro_env`, installed from `configs/environment/requirements-py313-win64.lock`. [The original fresh-environment receipt]({rel(ROOT/'final/reproduction_clean_01/verification.json')}) verifies all29 exact packages and an8.55-second tiny workflow. [The new clean rebuild]({rel(ROOT/'reports/phase_09/completion_clean_rebuild_01/verification.json')}) reproduces every final numerical CSV and both hardware/cooling tables; seven weighted-feature/semantic groups and five analysis hand-oracle groups also pass there.

Raw generation and capped-run commands remain in [the protocol]({rel(ROOT/'reports/phase_07/study_protocol.md')}) and [the original run guide]({rel(ROOT/'reports/phase_07/remaining_campaign_run_guide.md')}). Re-running those completed study names skips terminal cells; changing code, caps, inputs or physical assumptions requires a separately named frozen study. Do not rerun completed large matrices just to regenerate a plot.
''')
    md(RELEASE/'PROVENANCE.md',f'''# Provenance and limitations

Pinned RFT: `3d1f09233c2acd357fd9fbfad1b5300a921d301a`. Pinned DasAtom: `73a6bdf0fd200b2733745211eaf2e0c1e17f496a`. Current and both frozen99-file runtime manifests match; exact manuscript revision/options remain unresolved. Original source/license files remain under vendor/ and are not relicensed. Manuscript and benchmark redistribution terms remain unchanged.

Original Papers/Proposal file hashes match the extraction manifest. Intern_Report was not used. All work is under btp_work. The environment is pinned Windows CPython3.13.2 with29 hash-locked research packages; no delivery-tool dependency is needed for this Markdown release.

The five old result CSVs are unchanged. Initial/cap-only follow-up attempts, rejected repair proposals, timeouts, resource failures and the monitor I/O interruption remain in place. The follow-up changes caps only; the recovery wrapper retries only an explicitly identified monitor log-write failure and adds bounded logging retries without changing scientific workers or extending the experiment budget.

The artifact index binds code, small receipts, tables and research files. Large raw artifacts remain in their original directories, bound by their immutable attempt hash maps and independent streamed audits; they are not duplicated in this release. Current-document history is retained at `{rel(ARCHIVE)}`, with its preservation receipt mapping original paths to archived hashes. The older global artifact index remains a historical snapshot of those earlier paths.

No calibrated device/state fidelity, exact historical-paper identity, universal superiority, globally optimal matching/repair, or unchanged full one-qubit physical timing is claimed. Two generators per added family and differing timing scopes remain explicit limitations, not outstanding experiments secretly omitted. [Current related-work check]({rel(ROOT/'reports/phase_08/related_work_update.md')}).
''')
    md(RELEASE/'README.md','''# Idea1 finished research package

Read [final Markdown analysis](RESEARCH_ANALYSIS.md), then [completion review](COMPLETION_REVIEW.md). The bounded research and all planned measurements/analysis are finished, including retained censored and resource-failure outcomes. Formal report and presentation formatting awaits the user's instructions.

Supporting files: [complexity and cost](COMPLEXITY_AND_COST.md), [reproduction commands](REPRODUCE.md), [coverage/scope](scope_coverage.csv), [provenance](PROVENANCE.md), [completion gate](completion_gate.json), and scientific plots under figures/. The artifact index/checksum manifest binds this release. Existing report/presentation drafts are preserved and contain older interim conclusions.
''')
    md(RELEASE/'FIGURE_CATALOG.md',f'''# Analysis figure and table catalog

| Asset | Meaning | Data / qualification |
| --- | --- | --- |
| figures/controlled_effects.svg/pdf/png | Critical-weight/gamma controls, assignment-term removals, matched-profile replanning | Final weighting/assignment/hardware CSVs; selected-corpus intervals, not device uncertainty |
| figures/scaling_censoring.svg/pdf/png | Original QFT65–100 caps, successful and censored wall times, observed memory | Initial64 cells only; final higher-cap outcomes are in the separate final scaling ledger |
| {rel(ROOT/'reports/phase_08/integrated_analysis_02/factorial_interactions.svg')} | L/A/R main effects and interactions | Eight cases, five quality seeds; timing repeats excluded |
| {rel(ROOT/'reports/phase_08/integrated_analysis_02/repair_economics_and_error_floor.svg')} | Native floor, transport-sensitive gain and repair cost | Old66 matched circuit/grid targets; same-scope operational timing |
| {rel(ROOT/'reports/phase_08/integrated_analysis_02/fixed_trace_model_sensitivity.svg')} | Transfer/coherence scorer scenarios | Fixed schedules; distinct from profile-driven replanning |
| {rel(ROOT/'reports/final_benchmark_analysis_01/report.md')} | Baseline/paper discrepancies, old horizon/model figures and tables | Recovered PDF values, unresolved historical identity retained |

All new numeric tables, including per-family primary pairs, Pareto/repair costs, stages and storage, are linked from [the final analysis]({rel(ANALYSIS/'analysis.md')}). Vector/PDF plots are research artifacts; no formal report PDF or presentation has been rebuilt.
''')

    # Current planning and handoffs point to the new evidence; archive keeps history.
    decision=ROOT/'reports/decisions/D010_BOUNDED_IDEA1_COMPLETION.md'
    md(decision,f'''# D010: completion of the authorized bounded Idea1 research

Recorded {stamp}. This documents the user's existing instructions and frozen study, not a claim that this document was written before the data. The user authorized remaining experiments that fit five-to-six hours, reuse of finished work, and Markdown analysis while report/presentation formatting is supplied later.

The original529-cell manifest fixed the reduced seed/size/profile matrix before execution. Its caps and raw attempts remain unchanged. The cap-only30-cell follow-up selected every initial QFT timeout, without selecting quality winners, using the remaining original time budget. Total experiment-controller time is {spent/3600:.3f} hours≤6. Failures/censors are valid terminal outcomes under the technical contract, not proof that each compiler finishes successfully.

All original promised axes now have experimental evidence, prior immutable evidence, or the explicitly accepted pinned-source/analytical architecture boundary. No central comparison is left awaiting a run or analysis. Calibrated hardware, exact paper identity, an incomparable additional compiler adapter and unlimited parameter/instance expansion are not fabricated. Formal report/presentation formatting is deferred by the user's explicit instruction. Phase09 is complete as a Markdown research/reproducibility package; Phase10 closes only its existing transition brief.

Evidence and exact requirement mapping: [completion review](../../final/idea1_research_release_v1/COMPLETION_REVIEW.md), [scope ledger](../../final/idea1_research_release_v1/scope_coverage.csv), [research](../../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), and [machine-readable gate](../../final/idea1_research_release_v1/completion_gate.json). No original failed record or prior planning snapshot is erased.
''')
    for phase in range(7,11):
        path=next((ROOT/'plan/phases').glob(f'{phase:02}_*.md'))
        text=(ARCHIVE/path.relative_to(ROOT)).read_text(encoding='utf-8')
        text=re.sub(r'\*\*Status:\*\*[^\n]*','**Status:** complete within the user-authorized bounded Markdown research scope; see D010 and the final completion gate.',text,count=1)
        text=text.replace('- [ ]','- [x]')
        text+='\n\n## Final evidence and scope clarification\n\n[Research completion review](../../final/idea1_research_release_v1/COMPLETION_REVIEW.md), [requirement ledger](../../final/idea1_research_release_v1/scope_coverage.csv), [decision D010](../../reports/decisions/D010_BOUNDED_IDEA1_COMPLETION.md), and [accepted gate](../../final/idea1_research_release_v1/completion_gate.json). All planned measurements are terminal; censors/resource failures remain visible. Phase09 closes the Markdown research package; formal report/presentation formatting is deferred by the user. Phase10 closes the transition brief, not Idea2 implementation. Earlier versions of this document are archived under reports/phase_09/before_completion_01.\n'
        md(path,text)
        md(ROOT/f'handoffs/phase_{phase:02}.md',f'''# Phase{phase:02} final research handoff

Status: complete within D010's bounded Markdown research scope. [Completion review](../final/idea1_research_release_v1/COMPLETION_REVIEW.md), [all findings](../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [scope/coverage](../final/idea1_research_release_v1/scope_coverage.csv), [gate](../final/idea1_research_release_v1/completion_gate.json), [reproduction](../final/idea1_research_release_v1/REPRODUCE.md).

All original implementation gates and raw data remain unchanged. The529-cell portfolio,30-cell cap-only follow-up, profile-matched counterfactuals, saved-matrix mechanisms, runtime/storage analysis and clean numerical rebuild are complete. Failed/censored outcomes are retained, with no quality/time imputation. Current evidence supports conditional RFT-relative gains and identifies stronger corrected-DasAtom quality and replay cost limits.

The user deferred formal report and presentation formatting; no document/deck was rebuilt. Existing278 delivery files remain byte-identical. Phase10 preserves the four [Idea2 transition documents](../idea2/START_HERE.md) and API probe against this named release; no Idea2 compiler/campaign was started. Earlier handoffs are archived under reports/phase_09/before_completion_01. There are no pending required analyses or experiments within this finite research programme.
''')
    status=ROOT/'plan/STATUS.md';text=(ARCHIVE/'plan/STATUS.md').read_text(encoding='utf-8')
    current='''## Current final state

Idea1 bounded research is complete through Phase09; Phase10's Idea2 transition brief is complete. All remaining planned experiments have terminal outcomes and all research analyses are saved in Markdown. Formal report/presentation formatting is deferred by the user. [Final research](../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [review](../final/idea1_research_release_v1/COMPLETION_REVIEW.md), [gate](../final/idea1_research_release_v1/completion_gate.json), [D010](../reports/decisions/D010_BOUNDED_IDEA1_COMPLETION.md). Older status paragraphs below are historical checkpoints, superseded by this entry and the phase table.

'''
    text=text.replace('\n', '\n\n'+current,1)
    for phase in range(7,11):
        text=re.sub(rf'^\| {phase:02} \|.*$',f'| {phase:02} | complete | Codex /root | D010 bounded research scope | Final Markdown research package, terminal coverage and completion gate; formal formatting deferred; Phase10 brief only |',text,flags=re.M)
    md(status,text)
    for name in ['START_HERE.md','REUSE_MAP.md']:
        path=ROOT/'idea2'/name
        old=(ARCHIVE/'idea2'/name).read_text(encoding='utf-8')
        md(path,'# Current Idea1 dependency for the Idea2 brief\n\nIdea1 research now closes under [release idea1_research_release_v1](../final/idea1_research_release_v1/README.md), [its accepted gate](../final/idea1_research_release_v1/completion_gate.json) and [D010](../reports/decisions/D010_BOUNDED_IDEA1_COMPLETION.md). Scientific module identities are the99-file frozen manifest in runs/remaining_experiments_6h_v2/manifest.json. The original brief below remains applicable; its earlier pending-dependency statements are superseded by this entry. Formal document formatting remains deferred; Idea2 implementation has not begun.\n\n---\n\n'+old)
    md(ROOT/'final/README.md','''# Idea1 final research package

The bounded Idea1 research and analysis are finished. Read the [final Markdown findings](idea1_research_release_v1/RESEARCH_ANALYSIS.md), [completion review](idea1_research_release_v1/COMPLETION_REVIEW.md), [reproduction commands](idea1_research_release_v1/REPRODUCE.md), and [accepted gate](idea1_research_release_v1/completion_gate.json).

All planned experimental cells have terminal outcomes. Timeouts, finite-resource failures and accepted scientific limitations remain explicit; completion does not mean universal method success. Formal report and presentation formatting will follow the user's instructions later. The old research_delivery_20261031_v2 report/presentation remains untouched and contains interim conclusions; it is superseded as a research source by the Markdown release.

The release contains its own artifact index/checksum manifest. The older global artifact_index.json is preserved as a historical snapshot; archived versions of its changed current-document paths are mapped by reports/phase_09/before_completion_01/preservation_receipt.json.
''')
    md(ROOT/'final/completion_review.md','# Current Idea1 completion review\n\n[Accepted research completion review](idea1_research_release_v1/COMPLETION_REVIEW.md), [scope ledger](idea1_research_release_v1/scope_coverage.csv), and [machine-readable gate](idea1_research_release_v1/completion_gate.json). Prior incremental review is preserved in reports/phase_09/before_completion_01/final/completion_review.md. Formal report/presentation formatting is deferred by the user; all bounded research analyses and planned experiments are finished.')
    csvsave(ROOT/'final/scope_coverage.csv',[{**r,'evidence':rel((RELEASE/r['evidence']).resolve(),ROOT/'final') if ';' not in r['evidence'] else r['evidence']} for r in scope])
    md(ROOT/'reports/phase_08/results_and_discussion.md','# Final Idea1 results and discussion\n\nThe authoritative [final Markdown analysis](../../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md) answers all five research questions, including the completed bounded portfolio and cap-only QFT follow-up. [Full numeric tables](completion_final_01/analysis.md), [complexity and cost](../../final/idea1_research_release_v1/COMPLEXITY_AND_COST.md), [claims ledger](claims_evidence.csv), [limitations](limitations.md), and [accepted completion gate](../../final/idea1_research_release_v1/completion_gate.json). Earlier incremental notes and drafts are preserved; formal report/presentation formatting remains deferred by the user.')
    md(ROOT/'reports/phase_08/limitations.md','''# Final scientific limitations

All planned bounded measurements and required analyses are complete. [Coverage/accepted scope](../../final/idea1_research_release_v1/scope_coverage.csv), [final research](../../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [complexity/cost](../../final/idea1_research_release_v1/COMPLEXITY_AND_COST.md).

Scores use the normalized CZ skeleton, declared two-plane geometry, reconstructed serial transport and uncertain analytical parameters. Native calibrated fidelity, complete one-qubit physical timing and exact historical manuscript revision/options are unclaimed. Corrected DasAtom remains distinct from native invalid output. Cooling banks/resources are hypothetical and the stress transform is separate from the compiler.

The old66 circuit/grid targets represent27 circuits. The factorial has eight inputs and five paired router seeds;128 extra timing executions are not quality instances. The larger QAOA/QV extension has eight depth/size case IDs but only four generator identities, two per family; descriptive cluster intervals do not establish population generalization. No best default is selected post hoc.

Timeouts are right-censored outcomes and supply no completed quality/runtime. The higher-cap study uses method-specific caps, so solved counts do not establish equal-time superiority. Completed-only comparisons are conditional on joint success. Monitor-level I/O interruption/recovery is retained separately from algorithm outcomes. Observed family working-set peaks are sampled safeguards, not allocation-proof maxima. Inner timers differ across methods; outer wall cost includes different artifact/diagnostic work. No controlled cross-method speedup is claimed.

Sparse future-index bounds do not apply to the full replay wrapper. Its current snapshots repeat P×CZ gate IDs and full repair recompiles the circuit. Finite trials ensure termination under resources, not a cheap or globally optimal schedule. Extra compiler architectures lack a demonstrated fully matched adapter; their published results are not ranked against this study. The current primary literature check is bounded and makes no universal novelty claim.

Formal report/presentation formatting is deferred by the user; the Markdown research package is complete. Idea2 has a transition brief only. Accepted scientific boundaries and future engineering opportunities are not pending experiments hidden from the completion ledger.
''')
    oldclaims=rows(ARCHIVE/'reports/phase_08/claims_evidence.csv')
    oldclaims=[r for r in oldclaims if r['id']!='C10']
    newclaims=[
      ('C10','All planned bounded experiments and required Markdown analyses are complete','supported_with_scope','final/idea1_research_release_v1/completion_gate.json','censored/resource outcomes retained; formal formatting deferred by user; not native calibration or universal success'),
      ('C11','Proposed small wins21/24 larger/deeper pairs versus RFT snapshot','supported_conditional','reports/phase_08/completion_final_01/new_workload_summary.csv','eight case IDs,four generators; E proxy; three losses retained'),
      ('C12','Corrected DasAtom beats proposed small on24/24 larger/deeper pairs','supported_conditional','reports/phase_08/completion_final_01/new_workload_summary.csv','same normalized input/profile/geometry; not cross-architecture or device evidence'),
      ('C13','Critical-depth weighting has little consistent benefit in this corpus','supported_null_mixed','reports/phase_08/completion_final_01/weighting_summary.csv','gamma.9 gains confined to one circuit; no tuned winner'),
      ('C14','Three assignment terms change costs but not any of24 final schedules','supported_mechanism','reports/phase_08/mechanism_audit_01/verification.json','same realized trajectories; not proof terms irrelevant universally'),
      ('C15','Eight physical-profile changes retain96/96 matched planning decisions','supported_conditional','reports/phase_08/completion_final_01/hardware_summary.csv','four selected circuits; physical scores still profile-dependent; not universal invariance'),
      ('C16','Current full replay prefix representation repeats P×CZ gate IDs','supported_measured_and_source','reports/phase_08/snapshot_accounting_01/verification.json','three streamed QFT artifacts; diagnostic implementation,not a theoretical lower bound'),
      ('C17','Large-QFT conclusions preserve every initial censor and cap-only follow-up','supported_bounded','reports/phase_08/completion_final_01/scale_summary.csv','different method caps; no fabricated runtime or quality on killed workers')]
    csvsave(ROOT/'reports/phase_08/claims_evidence.csv',oldclaims+[dict(zip(['id','claim','status','evidence','limitation'],r)) for r in newclaims])
    for path in [ROOT/'reports/phase_07/study_protocol.md',ROOT/'reports/phase_07/remaining_campaign_run_guide.md']:
        md(path,'# Current completion notice\n\nThis protocol/run guide is preserved below as the pre-execution record. The study and cap-only follow-up are now terminal and analysed. [Final research](../../final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [coverage](../../final/idea1_research_release_v1/scope_coverage.csv), [D010](../decisions/D010_BOUNDED_IDEA1_COMPLETION.md), and [gate](../../final/idea1_research_release_v1/completion_gate.json). Older “not started” or “remaining” statements below describe the frozen preparation checkpoint.\n\n---\n\n'+(ARCHIVE/path.relative_to(ROOT)).read_text(encoding='utf-8'))
    # Extend the prior coverage instead of discarding its factorial/reuse rows.
    coverage=rows(ARCHIVE/'reports/phase_07/coverage.csv')
    for cohort,data in [('bounded_initial',mainrows),('cap_only_followup',followrows)]:
        coverage.extend({'category':cohort,'cell':r['id'],'status':r['status'],'rows':1,'evidence':r['record_path'],'quality_sample':r['status']=='ok'} for r in data)
    csvsave(ROOT/'reports/phase_07/coverage.csv',coverage)
    if (ROOT/'README.md').exists():
        md(ROOT/'README.md','# Current Idea1 research release\n\n[Final Markdown findings](final/idea1_research_release_v1/RESEARCH_ANALYSIS.md), [completion review](final/idea1_research_release_v1/COMPLETION_REVIEW.md), and [gate](final/idea1_research_release_v1/completion_gate.json). All bounded research is complete; formal report/presentation formatting is deferred by the user. Earlier README content below is historical.\n\n---\n\n'+(ARCHIVE/'README.md').read_text(encoding='utf-8'))
    md(ROOT/'final/demo.md','# Research walkthrough\n\nOpen [final findings](idea1_research_release_v1/RESEARCH_ANALYSIS.md). Explain the RFT-relative gains, stronger corrected-DasAtom quality, null weighting/term results, profile-matched comparisons, and replay/snapshot scaling cost. Show the [coverage ledger](idea1_research_release_v1/scope_coverage.csv) with failures/censors retained. Use [the small reproduction](idea1_research_release_v1/REPRODUCE.md) if needed. Formal report/presentation formatting remains deferred; the old deck is historical.')

    # Gate covers only current authoritative documents, not archived historical links.
    changed=[ROOT/r['original'] for r in before['archived_current_documents'] if str(r['original']).endswith('.md')]
    currentdocs=list(RELEASE.glob('*.md'))+changed+[decision]
    issues=[];links=0
    for doc in currentdocs:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
            destination=(doc.parent/target.split('#')[0].strip('<>')).resolve();links+=1
            if destination==RELEASE/'completion_gate.json':continue
            if not destination.exists():issues.append(str(doc.relative_to(ROOT))+': '+target)
    assert not issues,issues
    checks['current_research_document_links_resolve']=True
    for name,digest in before['protected_existing_report_presentation_files'].items():assert sha(ROOT/name)==digest
    indexpaths=set(p for p in RELEASE.rglob('*') if p.is_file())
    indexpaths.update(ANALYSIS.rglob('*.csv'));indexpaths.add(ANALYSIS/'summary.json')
    indexpaths.update(ROOT/name for name in ['tools/audit_idea1_completion.py','tools/check_idea1_envelopes.py','tools/recover_idea1_monitor_io.py',
        'tools/prepare_idea1_completion_followup.py','tools/finalize_idea1_research.py','analysis/idea1_final_analysis.py',
        'analysis/idea1_hardware_counterfactuals.py','analysis/idea1_mechanism_audit.py','analysis/idea1_snapshot_accounting.py',
        'tests/idea1_completion_analysis_acceptance.py','reports/phase_07/completion_audit_02/verification.json',
        'reports/phase_07/completion_followup_audit_01/verification.json','reports/phase_07/completion_envelopes_01/verification.json',
        'reports/phase_09/completion_clean_rebuild_01/verification.json','reports/phase_08/claims_evidence.csv',
        'reports/phase_08/limitations.md','reports/phase_08/related_work_update.md'])
    indexpaths.update([MAIN/'manifest.json',MAIN/'results.csv',FOLLOW/'manifest.json',FOLLOW/'results.csv',FOLLOW/'logging_recovery_provenance.json'])
    artifact_index={str(p.relative_to(ROOT)).replace('\\','/'):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(indexpaths)}
    write(RELEASE/'artifact_index.json',{'release':'idea1_research_release_v1','created_utc':stamp,'files':artifact_index,
        'large_raw_evidence':'original attempt hash maps independently checked in initial/follow-up audits; no large raw copy',
        'historical_current_document_map':'reports/phase_09/before_completion_01/preservation_receipt.json'})
    md(RELEASE/'CHECKSUMS.sha256','\n'.join(v['sha256']+'  '+k for k,v in artifact_index.items()))
    gate={'status':'complete','release':'idea1_research_release_v1','accepted_scope':'user-authorized bounded Idea1 experiments and Markdown research; formal report/presentation formatting deferred',
        'created_utc':stamp,'phases':{f'{i:02}':'complete' for i in range(11)},'phase10_scope':'transition brief only',
        'pending_required_experiments':0,'pending_required_research_analyses':0,'formal_formatting':'deferred_by_user',
        'checks':checks,'passed':sum(checks.values()),'total':len(checks),'links_checked':links,
        'initial_outcomes':dict(Counter(r['status'] for r in mainrows)),'followup_outcomes':dict(Counter(r['status'] for r in followrows)),
        'cumulative_experiment_controller_seconds':spent,'experiment_budget_seconds':21600,
        'artifact_index_sha256':sha(RELEASE/'artifact_index.json'),
        'scientific_limitations_retained':['analytical CZ skeleton','uncalibrated hardware','historical revision unresolved','finite selected corpus','method-specific caps and timer scope','no universal superiority or optimality'],
        'finalizer_sha256':sha(__file__)}
    write(RELEASE/'completion_gate.json',gate)
    print(str(RELEASE.relative_to(ROOT))+': '+str(gate['passed'])+'/'+str(gate['total'])+' completion checks passed.',flush=True)


if __name__=='__main__':main()
