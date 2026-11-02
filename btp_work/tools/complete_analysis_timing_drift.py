"""Use existing unchanged controls to document timing drift; no recompilation."""
import csv,hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    out=ROOT/'reports/final_benchmark_analysis_01'
    p1=list(csv.DictReader((ROOT/'runs/phase01_frozen_baseline_v1/results.csv').open()))
    p4=list(csv.DictReader((ROOT/'runs/phase04_matched_benchmark_v2/results.csv').open()))
    originals={r['target_id']:r for r in p1 if r['algorithm']=='rft'};drift=[]
    for r in p4:
        if r['variant']!='legacy_exact':continue
        old=originals[r['target_id']]
        drift.append({'target_id':r['target_id'],'case':r['case'],'grid':int(r['grid']),
            'historical_median_seconds':float(old['compile_seconds']),'historical_CV':float(old['compile_cv']),
            'fresh_control_seconds':float(r['compile_seconds']),
            'fresh_to_historical_ratio':float(r['compile_seconds'])/float(old['compile_seconds']),
            'instructions_and_final_RNG_exact':True,'timing_scopes_match':True})
    assert len(drift)==66
    with (out/'unchanged_RFT_timing_drift.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(drift[0]));w.writeheader();w.writerows(drift)
    grouped=[]
    for grid in [11,20,35]:
        values=[r['fresh_to_historical_ratio'] for r in drift if r['grid']==grid]
        grouped.append({'grid':grid,'targets':len(values),'median_fresh_to_historical_ratio':statistics.median(values),'minimum':min(values),'maximum':max(values)})
    summary=read(out/'summary.json');summary['unchanged_RFT_timing_drift']=grouped
    summary['matched_phase4_uses_fresh_controls_not_historical_time']=True;dump(out/'summary.json',summary)
    lines=[]
    for line in (out/'report.md').read_text().splitlines():
        if line.startswith('|'):
            cells=line.split('|')
            for i,cell in enumerate(cells):
                try:cells[i]=' '+format(float(cell.strip()),'.5g')+' '
                except ValueError:pass
            line='|'.join(cells)
        lines.append(line)
    report='\n'.join(lines)+'\n'
    section="""## Unchanged RFT timing drift

Phase 4 already measured a fresh unchanged RFT control on every target and verified exact instructions and final RNG. These 66 controls are reused here; no compiler was rerun. The following ratios compare one fresh sample to the Phase 1 three-sample median in the same timed region:

| Grid | Targets | Median fresh/historical | Minimum | Maximum |
| --- | --- | --- | --- | --- |
"""
    for r in grouped:section+=f"| {r['grid']} | {r['targets']} | {r['median_fresh_to_historical_ratio']:.4g} | {r['minimum']:.4g} | {r['maximum']:.4g} |\n"
    section+='\nDifferences measure combined host/process/timing variation, not a compiler change. They justify using fresh paired controls for Phase 4 overhead ratios. Fixed order and one new sample per variant do not establish confidence intervals. Full pairs are in `unchanged_RFT_timing_drift.csv`.\n\n'
    report=report.replace('## Phase 3: same decisions, different timing/error model',section+'## Phase 3: same decisions, different timing/error model',1)
    (out/'report.md').write_text(report,encoding='utf-8')
    evidence=read(out/'evidence.json');evidence['postprocessing_source_sha256']=sha(Path(__file__));evidence['timing_drift_controls_reused']=66;dump(out/'evidence.json',evidence)
    dump(out/'artifact_sha256.json',{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='artifact_sha256.json'})
    print(json.dumps(grouped))
if __name__=='__main__':main()
