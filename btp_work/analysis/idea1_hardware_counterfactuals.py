"""Score fixed default decisions and replanned decisions under IDENTICAL profiles.

Comparing a new-profile score to a default-profile score confounds the planner
with the physical model. This creates the necessary matched counterfactuals.
"""
import argparse
from copy import deepcopy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'analysis')]
sys.dont_write_bytecode = True
from phase08_incremental import read, rows, write, csvsave
from audit_idea1_completion import sha, locations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT): raise ValueError('Fresh output required')
    out.mkdir(parents=True)
    study = ROOT / 'runs/remaining_experiments_6h_v2'
    manifest = read(study / 'manifest.json')
    sys.path.insert(0, str(study / 'frozen'))
    from implementation.trace.model import fingerprint, load_trace
    from implementation.lookahead.evaluation import pilot_geometry_profile
    from implementation.movement_error.schedule import make_schedule
    from implementation.movement_error.evaluator import evaluate
    from implementation.movement_error.profiles import validate_profile
    data = rows(study / 'results.csv')
    by = {r['id']: r for r in data}
    jobs = {j['id']: j for j in manifest['jobs']}
    scores, recipes, cooling = [], [], []
    for row in data:
        if row['suite'] != 'hardware': continue
        job = jobs[row['id']]
        worker = (ROOT / row['record_path']).parent / 'worker'
        if job['kind'] == 'cooling':
            profile = read(worker / 'resolved_profile.json')
            no_cooling = deepcopy(profile)
            no_cooling['cooling']['enabled'] = False
            no_cooling['cooling']['bank_count'] = 0
            no_cooling['profile_id'] += '.cooling_disabled_counterfactual'
            trace = load_trace(ROOT / job['source_trace'])
            fixed = evaluate(make_schedule(trace, validate_profile(no_cooling), 'retime'), include_audit=False)
            assert fixed['status'] == 'ok' and fixed['valid_for_comparison']
            record = {'id': row['id'], 'banks': job['banks'], 'threshold': job['threshold'], 'status': row['status'],
                      'without_cooling_E': fixed['budget']['total_E'], 'without_cooling_makespan_us': fixed['makespan_us'],
                      'scope': 'same synthetic route, acceleration=.05, initial_n=3; cooling transform adds resources and operations'}
            if row['status'] == 'ok':
                evaluation = read(worker / 'evaluation.json')
                record.update(cooling_E=evaluation['budget']['total_E'], cooling_makespan_us=evaluation['makespan_us'],
                              delta_E=evaluation['budget']['total_E'] - fixed['budget']['total_E'],
                              **evaluation['counts'], **evaluation['budget']['terms'])
            else: record['reason'] = read(ROOT / row['record_path'])['result']['error']
            cooling.append(record)
            continue
        assert row['status'] == 'ok'
        reference = by[row['reference_id']]
        source_path, _ = locations(reference)
        original = read(source_path)
        request = read(worker / 'resolved_request.json')
        trace = deepcopy(original['source_trace'])
        if job.get('grid', 11) != 11:
            hardware = pilot_geometry_profile(request['geometry'])
            trace['metadata'].update(hardware=hardware, hardware_sha256=fingerprint(hardware), physical_evidence_complete=False)
            trace['metadata'].setdefault('assumptions', []).extend(hardware['assumptions'])
        transformed = make_schedule(trace, request['profile'], 'retime')
        score = evaluate(transformed, include_audit=False)
        assert score['status'] == 'ok' and score['valid_for_comparison'], row['id']
        new_path, new_evaluation = locations(row)
        new_schedule, new_score = read(new_path), read(new_evaluation)
        assert transformed['profile_sha256'] == new_schedule['profile_sha256'] == row['profile_sha256']
        assert trace['metadata']['hardware_sha256'] == new_schedule['source_trace']['metadata']['hardware_sha256']
        fixed_E, new_E = score['budget']['total_E'], float(row['extended_E'])
        scores.append({'id': row['id'], 'case_id': row['case_id'], 'seed': row['seed'], 'variant': row['variant'],
                       'control_E': fixed_E, 'new_E': new_E, 'delta_E': new_E-fixed_E,
                       'relative_E_percent': 100*(new_E/fixed_E-1),
                       'fixed_decisions_makespan_us': score['makespan_us'], 'new_plan_makespan_us': new_score['makespan_us'],
                       'decision_sequence_changed': transformed['source_decisions_sha256'] != new_schedule['source_decisions_sha256'],
                       'profile_sha256': transformed['profile_sha256'], 'hardware_sha256': trace['metadata']['hardware_sha256'],
                       **{'fixed_'+k: v for k, v in score['budget']['terms'].items()},
                       **{'new_'+k: v for k, v in new_score['budget']['terms'].items()}})
        recipes.append({'id': row['id'], 'fixed_source_schedule_path': str(source_path.relative_to(ROOT)),
                        'fixed_source_schedule_file_sha256': sha(source_path), 'resolved_request_path': str((worker/'resolved_request.json').relative_to(ROOT)),
                        'resolved_request_sha256': sha(worker/'resolved_request.json'),
                        'counterfactual_schedule_sha256': fingerprint(transformed),
                        'counterfactual_source_trace_sha256': fingerprint(trace), 'budget': score['budget'],
                        'method': 'default source decisions; requested geometry metadata if changed; requested profile; make_schedule(retime); evaluate'})
    assert len(scores) == 120 and len(cooling) == 9
    csvsave(out / 'profile_matched_pairs.csv', scores)
    csvsave(out / 'finite_cooling_cases.csv', cooling)
    write(out / 'replay_recipes.json', recipes)
    write(out / 'verification.json', {'status': 'ok', 'results_sha256': sha(study/'results.csv'),
          'analysis_script_sha256': sha(__file__), 'profile_matched_replays': len(scores), 'cooling_cases': len(cooling),
          'scope': 'Counterfactual analysis only; original planner results are unchanged; extended CZ skeleton analytical model'})
    print('Verified 120 profile-matched counterfactuals and 9 finite cooling cases.', flush=True)


if __name__ == '__main__': main()
