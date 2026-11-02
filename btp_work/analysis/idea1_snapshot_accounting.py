"""Stream diagnostic JSON to measure repeated prefix-state gate-ID storage.

Only three existing frozen baseline artifacts are inspected. No large JSON
object is loaded, no compiler is invoked, and no snapshot schema is changed.
"""
import argparse
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'analysis'),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase08_incremental import read,write,csvsave
from audit_idea1_completion import sha


def count_prefixes(path):
    count=completed=pending=0
    prefix_indent=None;array_indent=None;field=None
    with Path(path).open(encoding='utf-8') as handle:
        for line in handle:
            stripped=line.strip()
            indent=len(line)-len(line.lstrip())
            if stripped=='"prefix_state": {':
                assert prefix_indent is None
                prefix_indent=indent;count+=1
            elif prefix_indent is not None:
                if stripped in ('},','}') and indent==prefix_indent:
                    prefix_indent=None;field=None;array_indent=None
                elif stripped in ('"completed_gate_ids": [','"pending_gate_ids": ['):
                    field='completed' if stripped.startswith('"completed') else 'pending';array_indent=indent
                elif field and stripped in ('],',']') and indent==array_indent:
                    field=None;array_indent=None
                elif field and stripped.startswith('"'):
                    if field=='completed':completed+=1
                    else:pending+=1
    return count,completed,pending


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required')
    out.mkdir(parents=True);results=[];started=time.perf_counter()
    study=ROOT/'runs/remaining_experiments_6h_v2'
    for n in [65,80,100]:
        case=read(study/f'inputs/qft_{n}/case.json');gates=len(case['circuit']['gates'])
        path=study/f'measurements/scale__qft_{n}__s42__proposed_small/attempt_01/worker/baseline/compilation.json'
        count,completed,pending=count_prefixes(path)
        assert count>0 and completed+pending==count*gates,(n,count,completed,pending,gates)
        result={'qubits':n,'CZ':gates,'prefix_boundaries':count,'completed_id_occurrences':completed,
                'pending_id_occurrences':pending,'total_gate_id_occurrences_in_prefix_states':completed+pending,
                'P_times_CZ':count*gates,'compilation_json_bytes':path.stat().st_size,
                'file_sha256':sha(path),'path':str(path.relative_to(ROOT))}
        results.append(result);print({k:v for k,v in result.items() if k not in {'path','file_sha256'}},flush=True)
    csvsave(out/'snapshot_accounting.csv',results)
    write(out/'verification.json',{'status':'ok','observations':results,'script_sha256':sha(__file__),
        'elapsed_seconds':time.perf_counter()-started,
        'conclusion':'This exact snapshot representation repeats P*CZ gate IDs; sparse event-index O(N+CZ) does not imply whole compiler linear memory. Not a lower bound for a redesigned compiler.'})


if __name__=='__main__':main()
