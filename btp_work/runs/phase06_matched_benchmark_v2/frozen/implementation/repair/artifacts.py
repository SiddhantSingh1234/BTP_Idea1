"""Compact durable artifacts: accepted bundles, every proposal and terminal audit."""
from copy import deepcopy
import json
import hashlib
import math
from pathlib import Path
from implementation.trace.model import save_trace, fingerprint


def safe(value):
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            if isinstance(item, float) and not math.isfinite(item):
                output[key] = None
                output[str(key) + '_nonfinite'] = 'positive_infinity' if item > 0 else 'negative_infinity' if item < 0 else 'nan'
            else:
                output[key] = safe(item)
        return output
    if isinstance(value, (list, tuple)):
        return [safe(item) for item in value]
    return value


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(safe(value), indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def write_bundle(directory, value):
    directory = Path(directory)
    marker = directory / 'bundle.json'
    identity = {'recipe_sha256': value['recipe_sha256'],
                'schedule_sha256': fingerprint(value['evaluation']['schedule']),
                'instructions_sha256': hashlib.sha256(value['compilation']['instructions'].encode()).hexdigest()}
    if marker.exists():
        if json.loads(marker.read_text(encoding='utf-8')) != identity:
            raise ValueError('Bundle output path already belongs to another state')
        return directory
    directory.mkdir(parents=True, exist_ok=True)
    compiled, evaluated = value['compilation'], value['evaluation']
    (directory / 'instructions.txt').write_text(compiled['instructions'], encoding='utf-8', newline='\n')
    write(directory / 'compilation.json', compiled)
    save_trace(directory / 'trace', evaluated['trace'])
    write(directory / 'schedule.json', evaluated['schedule'])
    result = deepcopy(evaluated['result'])
    result.pop('event_audit', None)
    result['event_audit_omitted_for_storage'] = True
    write(directory / 'evaluation.json', result)
    write(directory / 'validation.json', evaluated['source_validation'])
    write(directory / 'metrics.json', evaluated['metrics'])
    write(marker, identity)
    return directory


def save_result(directory, result, baseline_directory):
    directory = Path(directory)
    history = []
    for accepted in result.get('accepted_history', []):
        path = directory / 'accepted' / accepted['candidate_id']
        write_bundle(path, accepted['bundle'])
        history.append({**{k: v for k, v in accepted.items() if k != 'bundle'},
                        'bundle_directory': str(path)})
    summary = {k: v for k, v in result.items() if k not in ('incumbent', 'accepted_history')}
    summary['accepted_history'] = history
    summary['final_bundle_directory'] = history[-1]['bundle_directory'] if history else str(baseline_directory)
    if result.get('incumbent') is None:
        summary['final_bundle_directory'] = None
    write(directory / 'result.json', summary)
    return summary
