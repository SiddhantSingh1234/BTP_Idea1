"""Independent schedule replay and provenance audit of incremental experiments."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase07_extension import read,write,sha
from implementation.trace.model import fingerprint
from implementation.movement_error.evaluator import evaluate


def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();study=args.study.resolve();out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh audit under btp_work required')
    out.mkdir(parents=True);started=time.perf_counter();protocol=read(study/'protocol.json')
    for name,digest in protocol['artifact_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,record in read(ROOT/'reports/phase_07/reused_studies.json').items():assert sha(ROOT/name)==record['sha256'],name
    rows=list(csv.DictReader((study/'campaign/results.csv').open(encoding='utf-8-sig',newline='')))
    assert len(rows)==448
    assert len({(r['case'],r['seed'],r['repeat'],r['variant']) for r in rows})==448
    records=[];cache={};accepted=0;trials=0;traps=0;rawseen=set();budget_max=0
    for row in rows:
        if row['status']!='ok':
            records.append({'case':row['case'],'seed':row['seed'],'status':row['status'],'accepted':False});continue
        bundle=ROOT/row['final_bundle_directory'];schedule=read(bundle/'schedule.json')
        digest=fingerprint(schedule)
        assert digest==row['final_schedule_sha256']
        if digest not in cache:
            scored=evaluate(schedule,include_audit=False)
            assert scored['status']=='ok' and scored['valid_for_comparison']
            assert scored['budget']==read(bundle/'evaluation.json')['budget']
            cache[digest]=scored['budget']['total_E']
        assert cache[digest]==float(row['E'])
        assert row['accepted_schedule'].lower()=='true'
        assert row['baseline_compatibility_verified'].lower()=='true'
        assert row['baseline_input_unchanged'].lower()=='true' and row['caller_rng_restored'].lower()=='true'
        assert float(row['E'])<=float(row['baseline_E'])+1e-12
        if row['raw_result'] not in rawseen:
            rawseen.add(row['raw_result']);raw=read(ROOT/row['raw_result'])
            assert raw['candidate_evaluations']==len(raw['audit'])<=raw['options']['max_evaluations']
            budget_max=max(budget_max,raw['candidate_evaluations'])
            trials+=len(raw['audit'])
            for entry in raw['audit']:
                assert entry['incumbent_unchanged_after_trial'] and entry['caller_rng_restored_after_trial']
                if entry.get('accepted'):
                    accepted+=1
                    assert entry['valid'] and entry['prefix_unchanged']
                    assert entry['actual_full_E']<entry['parent_full_E']-1e-12
                    evidence=entry['prefix_evidence']
                    assert evidence['incumbent_prefix_sha256']==evidence['candidate_prefix_sha256']
                if entry.get('locally_better_globally_worse'):
                    traps+=1;assert not entry['accepted']
        records.append({'case':row['case'],'seed':row['seed'],'repeat':row['repeat'],'variant':row['variant'],
            'status':'ok','schedule_sha256':digest,'E':cache[digest],'accepted':True})
    coverage=read(study/'campaign/coverage.json')
    assert len(coverage)==56
    for entry in coverage:
        if entry.get('attempt_record'):
            path=ROOT/entry['attempt_record'];record=read(path)
            assert record['worker_sha256']==sha(ROOT/'tools/phase07_extension.py')
            for name,digest in record.get('worker_artifact_sha256',{}).items():assert sha(path.parent/name)==digest,name
    write(out/'schedule_replays.json',records)
    summary={'status':'ok','planned_rows':448,'accepted_rows':sum(r['accepted'] for r in records),
        'quality_rows':sum(r['quality_sample'].lower()=='true' for r in rows),
        'unique_schedule_hashes_independently_replayed':len(cache),'candidate_audits_checked':trials,
        'accepted_repairs_checked':accepted,'local_global_traps_rejected':traps,'maximum_evaluations':budget_max,
        'baseline_compatibility_checks':224,'attempt_records_verified':len(coverage),
        'independent_candidate_recompilation_performed':False,
        'scope':'every final serialized schedule is validated/scored; exact duplicate hashes reuse verified evaluation; trial decisions audited, not all rejected candidates recompiled',
        'protocol_sha256':sha(study/'protocol.json'),'results_sha256':sha(study/'campaign/results.csv'),
        'audit_script_sha256':sha(Path(__file__)),'seconds':time.perf_counter()-started}
    write(out/'verification.json',summary);print(json.dumps(summary));return 0
if __name__=='__main__':raise SystemExit(main())
