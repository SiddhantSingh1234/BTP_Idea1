"""Run only extension cells not already measured by the identical cost pilot."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
sys.dont_write_bytecode = True
import phase07_extension as extension
import run_paper_focus as bounded


def main():
    p = argparse.ArgumentParser(); p.add_argument('--study', type=Path, required=True)
    args = p.parse_args(); study = args.study.resolve()
    if not study.is_relative_to(ROOT): raise ValueError('Study outside workspace')
    original = bounded.bounded_job
    imports = []
    def reuse(job, timeout, **kwargs):
        source = study / 'cost_pilot/raw' / job['target_id'] / 'attempt_01/attempt_record.json'
        if source.exists():
            record = extension.read(source)
            assert record['status'] == 'ok'
            assert record['worker_sha256'] == extension.sha(kwargs['worker_path'])
            assert record['router_sha256'] == extension.sha(kwargs['router_path'])
            assert record['input_sha256'] == job['expected_normalized_sha256']
            assert record['timeout_seconds'] == timeout
            imports.append({'source': source.relative_to(ROOT).as_posix(), 'sha256': extension.sha(source),
                            'target_id': job['target_id'], 'reason': 'identical predeclared worker/input/budget; no duplicate compilation'})
            extension.write(study / 'measurement_imports.json', imports)
            return record
        return original(job, timeout, **kwargs)
    bounded.bounded_job = reuse
    try:
        extension.run_study(study)
    finally:
        bounded.bounded_job = original


if __name__ == '__main__': main()
