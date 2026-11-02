"""Freeze a controller-only repair without changing the scientific baseline."""
import argparse
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import standalone_baseline as service


def prepare(study):
    study, work = service.study_path(study)
    service.verify(study, runtime=True)
    bundle = study / 'controller_repair_v1'
    if bundle.exists(): return service.verify_controller_repair(study)
    records = {}
    for path in (study / 'measurements').glob('*/attempt_*/attempt_record.json'):
        records[str(path.relative_to(study))] = service.sha(path)
    bundle.mkdir()
    files = {}
    for name, source in [
        ('tools/standalone_baseline.py', work / 'tools/standalone_baseline.py'),
        ('tools/run_paper_focus.py', work / 'tools/run_paper_focus.py'),
        ('tools/baseline_campaign.py', study / 'frozen/tools/baseline_campaign.py')]:
        target = bundle / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files[name] = service.sha(target)
    manifest = {
        'schema': 'phase01-controller-repair.v1', 'created_utc': service.now(),
        'parent_manifest_sha256': service.sha(study / 'manifest.json'),
        'reason': 'Reproduced AssignProcessToJobObject WinError 5 race after running venv redirector starts; create suspended, assign root, resume initial thread.',
        'launcher_protocol': 'windows-suspended-job-v1', 'files': files,
        'archived_attempt_sha256': records,
        'unchanged': ['frozen worker, router, vendor, inputs, seed, environment, timer scope, timeout and memory caps, all existing attempt records'],
        'retry_policy': 'Retry only pre-repair WinError 5 monitor errors under one second with zero observed memory and no worker result/artifacts; real compiler failures/timeouts remain held.',
        'scheduling': 'Wait for the existing controller to release its study lock; never interrupt a running measurement.'}
    service.write(bundle / 'manifest.json', manifest)
    (bundle / 'manifest.sha256').write_text(service.sha(bundle / 'manifest.json') + '\n', encoding='ascii')
    return service.verify_controller_repair(study)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, default=service.DEFAULT)
    args = parser.parse_args()
    result = prepare(args.study)
    print('Controller repair frozen and verified:', result['launcher_protocol'])
    print('Original frozen baseline unchanged. Archived attempt hashes:', len(result['archived_attempt_sha256']))
