"""Freeze execution-only Phase03 optimizations beside the original comparison."""
import argparse
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_comparison as service


def prepare(study):
    study = Path(study).resolve()
    work = Path(__file__).resolve().parents[1]
    if study.parent != work / 'runs': raise ValueError('Comparison must be under btp_work/runs')
    parent = service.verify(study, runtime=True)
    if parent['track'] != 'phase3': raise ValueError('This execution revision is Phase03 only')
    revision = study / 'execution_optimization_v1'
    if revision.exists(): return service.verify_execution_revision(study)
    handle = service.acquire(study / 'controller.lock')
    if handle is None: raise ValueError('Comparison is already running; preserve its active revision')
    try:
        revision.mkdir()
        files = {}
        for name, source in [
            ('tools/model_comparison.py', work / 'tools/model_comparison.py'),
            ('tools/model_comparison_worker.py', work / 'tools/model_comparison_worker.py'),
            ('tools/run_paper_focus.py', work / 'tools/run_paper_focus.py'),
            ('tools/baseline_campaign.py', study / 'frozen/tools/baseline_campaign.py')]:
            target = revision / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target); files[name] = service.sha(target)
        manifest = {'schema': 'phase03-execution-optimization.v1', 'created_utc': service.now(),
            'parent_manifest_sha256': service.sha(study / 'manifest.json'), 'files': files,
            'scientific_code_root': str(study / 'frozen'),
            'changes': ['Complete-trace-hash reuse of identical validation and legacy metrics within one score',
                        'Previously tested suspended-root Windows launcher'],
            'unchanged': ['All original frozen comparison files', 'Phase01 baseline and traces',
                          'Physics profile and equations', 'Independent transformed-schedule validation',
                          'Input matrix, seeds, geometry, timeout and memory limits',
                          'Serial execution and wait for Phase01 timing measurements'],
            'phase3_compiler_execution': False}
        service.write(revision / 'manifest.json', manifest)
        (revision / 'manifest.sha256').write_text(service.sha(revision / 'manifest.json') + '\n', encoding='ascii')
        return service.verify_execution_revision(study)
    finally: service.release(handle)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    args = parser.parse_args(); value = prepare(args.study)
    print('Verified Phase03 execution revision:', value['schema'])
    print('Saved Phase01 traces reused; no RFT or DasAtom recompilation.')
