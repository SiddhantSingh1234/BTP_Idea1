"""Regenerate final aggregates from a separate cwd and hash-locked environment."""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from audit_idea1_completion import read,write,sha


def main():
    out=ROOT/'reports/phase_09/completion_clean_rebuild_01'
    if out.exists():raise FileExistsError('Preserve previous clean check')
    out.mkdir(parents=True)
    python=ROOT/'final/repro_env/Scripts/python.exe'
    work=ROOT/'final/reproduction_workdir';work.mkdir(exist_ok=True)
    expected=read(ROOT/'final/reproduction_clean_01/verification.json')['package_versions']
    environment={**os.environ,'PYTHONNOUSERSITE':'1','PYTHONHASHSEED':'0','OPENBLAS_NUM_THREADS':'1',
        'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    environment.pop('PYTHONPATH',None)
    code="import importlib.metadata as m,json,sys; p=json.loads(sys.argv[1]); print(json.dumps({'versions':{k:m.version(k) for k in p},'prefix':sys.prefix}))"
    result=subprocess.run([str(python),'-B','-X','utf8','-c',code,json.dumps(list(expected))],
        cwd=work,env=environment,text=True,capture_output=True,check=True)
    actual=json.loads(result.stdout)
    assert actual['versions']==expected
    assert Path(actual['prefix']).resolve()==python.parent.parent.resolve()
    clean=ROOT/'reports/phase_09/completion_clean_analysis_01'
    command=[str(python),'-B','-X','utf8',str(ROOT/'analysis/idea1_final_analysis.py'),'--out',str(clean)]
    with (out/'analysis_stdout.txt').open('w',encoding='utf-8') as stdout, (out/'analysis_stderr.txt').open('w',encoding='utf-8') as stderr:
        subprocess.run(command,cwd=work,env=environment,stdout=stdout,stderr=stderr,check=True)
    accepted=ROOT/'reports/phase_08/completion_final_01'
    verified=[]
    for source in sorted(accepted.glob('*.csv')):
        assert sha(source)==sha(clean/source.name),source.name
        verified.append(source.name)
    hardware=[]
    for name in ['profile_matched_pairs.csv','finite_cooling_cases.csv']:
        assert sha(ROOT/'reports/phase_08/hardware_counterfactual_02'/name)==sha(ROOT/'reports/phase_09/clean_hardware_counterfactual_01'/name)
        hardware.append(name)
    write(out/'verification.json',{'status':'ok','script_sha256':sha(__file__),
        'separate_environment':'final/repro_env','separate_workdir':'final/reproduction_workdir',
        'all_29_exact_packages_match':True,'package_versions':actual['versions'],
        'all_numerical_csvs_identical':True,'verified_numerical_csvs':verified,
        'hardware_counterfactual_csvs_identical':True,'verified_hardware_csvs':hardware,
        'accepted_analysis_summary_sha256':sha(accepted/'summary.json'),
        'fresh_analysis_script_sha256':read(clean/'summary.json')['script_sha256'],
        'weighted_feature_semantic_test_receipt':'reports/phase_09/clean_completion_weighting_tests_01/result.json',
        'analysis_hand_oracle_receipt':'reports/phase_09/clean_completion_analysis_tests_01/result.json'})
    print('Clean environment reproduces '+str(len(verified))+' final numerical CSVs and both hardware/cooling CSVs.',flush=True)


if __name__=='__main__':main()
