"""Freeze a scoped execution revision without modifying the prepared study."""
import argparse
import json
import shutil
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import model_comparison as service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    if study.parent != ROOT / 'runs':
        raise ValueError('Study must be under runs')
    manifest = service.verify(study, runtime=True)
    if manifest['track'] != 'phase6':
        raise ValueError('Memory revision only applies to Phase06')
    revision = study / 'execution_optimization_v1'
    if (revision / 'manifest.json').exists():
        service.verify_execution_revision(study)
        print(json.dumps({'verified': True, 'revision': str(revision)}))
        return
    files = {}
    for name in ['model_comparison.py', 'model_comparison_worker.py',
                 'phase06_comparison_worker.py', 'phase06_memory.py']:
        relative = 'tools/' + name
        target = revision / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        files[relative] = service.sha(target)
    service.write(revision / 'manifest.json', {'schema': 'phase06-execution-memory-revision.v1',
        'created_utc': service.now(), 'parent_manifest_sha256': service.sha(study / 'manifest.json'),
        'revision_id': 'phase06_memory.context_release.v1', 'files': files,
        'scientific_sources_unchanged': True, 'memory_limit_bytes': 4 * 1024**3,
        'changes': ['lossless immutable snapshot sharing', 'streaming JSON/hash',
            'optional already-discarded event audit suppressed', 'finished replay contexts detached',
            'prior budget bundle references released'],
        'unchanged': ['candidate budgets/order', 'full replay/validation', 'strict full-E acceptance',
            'profile/geometry', 'original Phase05 routing RNG state', 'complete saved prefix evidence']})
    (revision / 'manifest.sha256').write_text(service.sha(revision / 'manifest.json') + '\n', encoding='ascii')
    service.verify_execution_revision(study)
    print(json.dumps({'prepared': True, 'revision': str(revision)}))


if __name__ == '__main__':
    main()
