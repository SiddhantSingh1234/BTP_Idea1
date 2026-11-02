"""One capped measurement; never builds a report or interprets research results."""
import argparse
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback

sys.dont_write_bytecode = True
CODE = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get('BTP_WORK_ROOT', CODE)).resolve()
sys.path[:0] = [str(CODE), str(CODE / 'tools')]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    from implementation.repair.artifacts import write as save
    save(path, value)


def profile_options(label):
    from implementation.movement_error.profiles import load_profile, validate_profile
    p = load_profile(CODE / 'configs/hardware/extended_no_cooling.json')
    changes = {
        'heating_half': ('heating', 'multiplier', .5), 'heating_double': ('heating', 'multiplier', 2.),
        'acceleration_half': ('movement', 'acceleration_um_per_us2', .0005),
        'acceleration_double': ('movement', 'acceleration_um_per_us2', .002),
        'coherence_short': ('exposure', 'T2_us', 150000.),
        'coherence_long': ('exposure', 'T2_us', 15000000.),
        'transfer_lower': ('noise', 'f_transfer', .9932),
        'transfer_higher': ('noise', 'f_transfer', .9999)}
    if label in changes:
        section, key, value = changes[label]
        p[section][key] = value
        p['profile_id'] = 'budgeted_' + label + '.v1'
        p['assumptions'].append('Predeclared hypothetical parameter sensitivity; no device calibration')
    elif label != 'default':
        raise ValueError('Unknown profile label: ' + label)
    return validate_profile(p)


@contextmanager
def compact_replay():
    import implementation.repair.search as search
    from phase06_memory import memory_scope, freeze_compilation
    with memory_scope() as release:
        original = search.replay
        def compact(*args, **kwargs):
            value = freeze_compilation(original(*args, **kwargs))
            release()
            return value
        search.replay = compact
        try:
            yield release
        finally:
            search.replay = original


def compilation(request, out):
    from implementation.assignment.integration import compile_schedule
    from implementation.assignment.costs import load_options as assignment_options
    from implementation.lookahead.potential import load_options as parking_options
    from implementation.lookahead.evaluation import evaluate_compilation
    from implementation.budgeted_study.weighting import parking_weight_scope
    from implementation.trace.model import fingerprint
    from implementation.repair.evaluation import total_E
    from implementation.repair.artifacts import write_bundle, save_result
    from implementation.repair.config import load_options as repair_options
    import implementation.repair.search as search
    case = read(WORK / request['case_path'])
    if request.get('grid'):
        case = deepcopy(case)
        case['geometry']['rows'] = case['geometry']['columns'] = request['grid']
    look = parking_options(CODE / ('configs/variants/lookahead.' + request.get('lookahead', 'next_events_h4') + '.json'))
    look.update(gamma=request.get('gamma', .9), weight_mode=request.get('weight_mode', 'uniform'))
    look['variant_id'] = request.get('variant', look['variant_id'])
    assignment = assignment_options(CODE / ('configs/variants/assignment.' + request.get('assignment', 'composite_bottleneck_expanded') + '.json'))
    if request.get('remove_term'):
        assignment['weights'][request['remove_term']] = 0.
        assignment['variant_id'] += '_without_' + request['remove_term']
    profile = profile_options(request.get('profile', 'default'))
    write(out / 'resolved_request.json', {**request, 'case_sha256': fingerprint(case), 'lookahead': look,
          'assignment': assignment, 'profile': profile, 'geometry': case['geometry']})
    write(out / 'stage.json', {'stage': 'compile_validate_measure'})
    seed = request['seed']
    history = None
    started = time.perf_counter()
    with parking_weight_scope(case['circuit'], look['weight_mode']):
        if request.get('repair', 'disabled') == 'disabled':
            # All non-repair methods use the same compilation + validation scope.
            random.seed(seed)
            compiled = compile_schedule(case['schedule'], case['circuit']['num_qubits'], case['layout'],
                case['geometry'], case['baseline_options'], look, assignment, profile,
                circuit=case['circuit'], routing_seed=seed)
            evaluated = evaluate_compilation(compiled, case['circuit'], case['geometry'], profile)
            value = {'compilation': compiled, 'evaluation': evaluated, 'recipe_sha256': fingerprint(request)}
            seconds = time.perf_counter() - started
            evaluations, accepted = 0, 0
        else:
            with compact_replay():
                baseline = search.prepare(case, look, assignment, profile, seed=seed)
                if not baseline['evaluation']['accepted_schedule']:
                    raise ValueError('Invalid baseline is not repairable')
                baseline_path = out / 'baseline'
                write_bundle(baseline_path, baseline)
                options = repair_options(CODE / ('configs/variants/repair.' + request['repair'] + '.json'))
                def checkpoint(incumbent, entry):
                    destination = out / 'accepted' / entry['candidate_id']
                    write_bundle(destination, incumbent)
                    write(out / 'last_incumbent.json', {'path': str(destination.relative_to(WORK)),
                          'E': entry['actual_full_E'], 'candidate_id': entry['candidate_id']})
                history = search.repair(case, look, assignment, profile, options, seed=seed,
                                        baseline=baseline, checkpoint=checkpoint)
                seconds = time.perf_counter() - started
                value = history['incumbent']
                evaluations, accepted = history['candidate_evaluations'], len(history['accepted_history'])
                if value is None:
                    raise ValueError('No feasible retained incumbent')
                if history['final_E'] > history['original_E'] + 1e-12:
                    raise AssertionError('Repair worsened its parent')
                save_result(out / 'repair', history, baseline_path)
    if not value['evaluation']['accepted_schedule']:
        result = value['evaluation']['result']
        return {'status': result['status'], 'accepted_schedule': False,
                'validation': result.get('validation'), 'error': 'Common validator/evaluator did not accept schedule'}
    result = value['evaluation']['result']
    write(out / 'stage.json', {'stage': 'artifact_export'})
    write_bundle(out / 'final', value)
    stats = value['compilation']['statistics']
    return {'status': 'ok', 'accepted_schedule': True, 'extended_E': total_E(result),
        'extended_fidelity': result['budget']['fidelity_proxy'], 'makespan_us': result['makespan_us'],
        'normalization_seconds': case.get('normalization_seconds'),
        'compile_validate_repair_seconds': seconds,
        'timing_scope': 'required compilation, prefix work where used, validation/scoring and all repair work; imports/final export excluded',
        'candidate_evaluations': evaluations, 'accepted_repairs': accepted,
        'N': case['circuit']['num_qubits'], 'CZ': len(case['circuit']['gates']),
        'grid': case['geometry']['rows'], 'normalized_sha256': case['normalized_sha256'],
        'profile_sha256': result['profile_sha256'], 'schedule_sha256': fingerprint(value['evaluation']['schedule']),
        'instructions_sha256': __import__('hashlib').sha256(value['compilation']['instructions'].encode()).hexdigest(),
        'physical_scope': 'declared analytical geometry and normalized CZ skeleton; no native-device fidelity claim',
        'final_bundle': str((out / 'final').relative_to(WORK)),
        'parking_calls': stats.get('parking_calls'), 'eviction_calls': stats.get('eviction_calls'),
        'assignment_solves': stats.get('assignment_solves'),
        **{k: v for k, v in stats.items() if k.endswith('_seconds') or 'bytes' in k},
        **result['budget']['terms']}


def dasatom(request, out):
    # Invoke the exact existing corrected worker inside this owned worker family;
    # common physical scoring remains inside the same external wall/memory cap.
    from implementation.trace.model import load_trace, fingerprint, save_trace
    from implementation.lookahead.evaluation import pilot_geometry_profile
    from implementation.validation.checker import check_trace
    from implementation.movement_error.schedule import make_schedule
    from implementation.movement_error.evaluator import evaluate
    import corrected_dasatom_worker
    case = read(WORK / request['case_path'])
    original_argv = sys.argv[:]
    total_started = time.perf_counter()
    try:
        sys.argv = ['corrected_dasatom_worker.py', '--input', str(WORK / case['normalized_path']),
                    '--grid', str(case['geometry']['rows']), '--seed', str(request['seed']),
                    '--out', str(out / 'native')]
        with redirect_stdout(io.StringIO()):
            code = corrected_dasatom_worker.main()
    finally:
        sys.argv = original_argv
    raw = read(out / 'native/result.json')
    if code or raw['status'] != 'ok':
        return {'status': raw['status'], 'accepted_schedule': False, 'error': raw.get('error')}
    started = time.perf_counter()
    trace = load_trace(out / 'native/trace')
    hardware = pilot_geometry_profile(case['geometry'])
    trace['metadata'].update(hardware=hardware, hardware_sha256=fingerprint(hardware), physical_evidence_complete=False)
    trace['metadata'].setdefault('assumptions', []).extend(hardware['assumptions'])
    validation = check_trace(trace)
    schedule = make_schedule(trace, profile_options('default'), 'retime')
    result = evaluate(schedule, include_audit=False)
    score_seconds = time.perf_counter() - started
    accepted = validation['status'] == result['status'] == 'ok' and result['valid_for_comparison']
    total_seconds = time.perf_counter() - total_started
    save_trace(out / 'common_trace', trace)
    write(out / 'schedule.json', schedule);write(out / 'evaluation.json', result)
    write(out / 'validation.json', validation)
    return {'status': 'ok' if accepted else ('invalid' if result['status'] == 'ok' else result['status']), 'accepted_schedule': accepted,
        'extended_E': (result.get('budget') or {}).get('total_E'),
        'makespan_us': result.get('makespan_us'), 'N': case['circuit']['num_qubits'],
        'CZ': len(case['circuit']['gates']), 'grid': case['geometry']['rows'],
        'normalized_sha256': case['normalized_sha256'], 'profile_sha256': result.get('profile_sha256'),
        'compile_validate_repair_seconds': total_seconds,
        'native_independent_validation_seconds_included_in_total': False,
        'timing_scope': 'full native corrected worker plus common validation/scoring, including native artifact writes; final common artifact export excluded; process wall is the common outer scope',
        'native_compile_seconds': raw['corrected_compile_seconds'], 'common_scoring_seconds': score_seconds,
        'stage_seconds': raw.get('stage_seconds'), **((result.get('budget') or {}).get('terms') or {})}


def cooling(request, out):
    from implementation.trace.model import load_trace, fingerprint
    from implementation.movement_error.profiles import load_profile, validate_profile
    from implementation.movement_error.schedule import make_schedule, UnsupportedSchedule
    from implementation.movement_error.evaluator import evaluate
    trace = load_trace(WORK / request['source_trace'])
    p = load_profile(CODE / 'configs/hardware/extended_registered_cooling.json')
    p['movement']['acceleration_um_per_us2'] = .05
    p['heating']['initial_n'] = 3.
    p['cooling'].update(bank_count=request['banks'], threshold_n=request['threshold'])
    p['profile_id'] = f"budgeted_cooling_b{request['banks']}_t{request['threshold']}.v1"
    p = validate_profile(p)
    write(out / 'resolved_profile.json', p)
    try:
        schedule = make_schedule(trace, p, 'retime_and_cool')
    except UnsupportedSchedule as exc:
        return {'status': 'unsupported', 'accepted_schedule': False, 'error': str(exc),
                'scope': 'finite resource/cooling transform of a fixed synthetic route, not a compiler gain'}
    result = evaluate(schedule, include_audit=False)
    write(out / 'schedule.json', schedule);write(out / 'evaluation.json', result)
    return {'status': result['status'], 'accepted_schedule': result['status'] == 'ok' and result['valid_for_comparison'],
        'extended_E': (result.get('budget') or {}).get('total_E'), 'makespan_us': result.get('makespan_us'),
        'profile_sha256': fingerprint(p), 'counts': result.get('counts'),
        'scope': 'fixed synthetic route, extra hypothetical cooling banks/resources; no planner optimization claim',
        **((result.get('budget') or {}).get('terms') or {})}


def main():
    p = argparse.ArgumentParser();p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True);p.add_argument('--seed', type=int, required=True)
    p.add_argument('--grid', type=int, required=True);args = p.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(WORK):
        raise ValueError('Fresh worker output required under project')
    out.mkdir(parents=True)
    request = read(args.input)
    if request['seed'] != args.seed:
        raise ValueError('Routing seed differs from request')
    try:
        kind = request['kind']
        if kind == 'compile': result = compilation(request, out)
        elif kind == 'dasatom': result = dasatom(request, out)
        elif kind == 'cooling': result = cooling(request, out)
        elif kind == 'timeout_test': time.sleep(2);result = {'status': 'ok', 'accepted_schedule': False}
        else: raise ValueError('Unknown measurement kind')
    except Exception as exc:
        result = {'status': 'error', 'accepted_schedule': False,
                  'error': {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}}
    write(out / 'result.json', result)
    print(json.dumps({'status': result['status'], 'accepted_schedule': result.get('accepted_schedule', False)}), flush=True)
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
