import json
import math
from pathlib import Path

SCHEMA = 'repair_options.phase06.v1'


def validate_options(value):
    options = dict(value)
    required = {'schema_version', 'variant_id', 'enabled', 'max_rounds', 'transitions_per_round',
        'decisions_per_transition', 'candidates_per_decision', 'max_evaluations',
        'max_replay_route_calls', 'improvement_tolerance_E', 'max_repair_seconds',
        'parking_site_scan_limit', 'swap_pair_scan_limit', 'slot_scan_limit'}
    if set(options) != required or options['schema_version'] != SCHEMA:
        raise ValueError('Unknown/missing repair options')
    if not isinstance(options['variant_id'], str) or not options['variant_id']:
        raise ValueError('Missing repair identity')
    if type(options['enabled']) is not bool:
        raise ValueError('Repair enabled must be boolean')
    for key in ('max_rounds', 'transitions_per_round', 'decisions_per_transition',
                'candidates_per_decision', 'max_evaluations', 'max_replay_route_calls',
                'parking_site_scan_limit', 'swap_pair_scan_limit', 'slot_scan_limit'):
        if type(options[key]) is not int or options[key] < 0:
            raise ValueError('Invalid deterministic repair budget: ' + key)
    tolerance = options['improvement_tolerance_E']
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Invalid improvement tolerance')
    wall = options['max_repair_seconds']
    if wall is not None and (type(wall) not in (int, float) or not math.isfinite(wall) or wall < 0):
        raise ValueError('Invalid optional wall-time safeguard')
    return options


def load_options(path):
    return validate_options(json.loads(Path(path).read_text(encoding='utf-8')))
