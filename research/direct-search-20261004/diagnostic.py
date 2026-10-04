"""Frozen development diagnostic on all 31 survivors of the grouped-only screen."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT/'results/direct-search-20261004'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, value):
    with path.open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')

def freeze():
    source_root=ROOT/'research/coverage-iteration-20261004/diagnostic-snapshot'
    previous = ROOT/'research/grouped-excess-20261004/full-audit.json'
    assert json.loads(previous.read_text())['status'] == 'passed'
    rows_path = ROOT/'results/grouped-excess-20261004/full/runs.jsonl'
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    selected = [dict(corpus=r['corpus'],query=r['query']) for r in rows if r['method']=='candidate' and r['verdict']=='unknown']
    assert len(selected)==31
    snapshot = HERE/'diagnostic-snapshot'
    snapshot.mkdir()
    pins = {str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)), str(previous.relative_to(ROOT)):sha(previous), str(rows_path.relative_to(ROOT)):sha(rows_path)}
    for source in [*sorted((source_root/'scripts').glob('*.py')), *sorted((source_root/'src').glob('*.rs')), source_root/'Cargo.toml',source_root/'Cargo.lock']:
        target = snapshot/source.relative_to(source_root)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        pins[str(target.relative_to(ROOT))]=sha(target)
    binary = snapshot/'vass-reach'
    shutil.copy2(source_root/'vass-reach',binary)
    pins[str(binary.relative_to(ROOT))]=sha(binary)
    corpora = dict(existing176='benchmarks/general-development-v3',expansion192='benchmarks/development-expansion-v4')
    for corpus in corpora.values():
        manifest = ROOT/corpus/'manifest.json'
        pins[str(manifest.relative_to(ROOT))]=sha(manifest)
        for q in json.loads(manifest.read_text())['queries']:
            for item in ('pnml','xml','net','property'):
                p=ROOT/corpus/q[item];assert sha(p)==q[item+'_sha256'];pins[str(p.relative_to(ROOT))]=sha(p)
            for b in q['branches']:
                p=ROOT/corpus/b['path'];assert sha(p)==b['sha256'];pins[str(p.relative_to(ROOT))]=sha(p)
    random.Random(2026100403).shuffle(selected)
    schedule=[]
    for i,q in enumerate(selected):
        methods=['walk-guided','relaxed-batched']
        if i%2:methods.reverse()
        schedule.extend(dict(q,method=m) for m in methods)
    save(HERE/'diagnostic-plan.json',dict(binary=str(binary.relative_to(ROOT)),pins=pins,corpora=corpora,schedule=schedule,
         seconds=5,max_states=2000000,memory_mib=2048,validation_seconds=60,
         scope='All31 survivors; selected diagnostic, no overall coverage or stable speed claim. Standalone walk-guided versus relaxed-batched, neither with buffer agglomeration. Independent original-input verification outside timing.',
         frozen_utc=datetime.now(timezone.utc).isoformat()))

def run():
    plan_path=HERE/'diagnostic-plan.json';plan=json.loads(plan_path.read_text())
    sys.path.insert(0,str(HERE/'diagnostic-snapshot/scripts'))
    import benchmark_smpt_classic as runner
    from process_runner import workspace_workloads
    from bounded_validation import InputChecks
    from analyze_application_expansion import native_checked, failure_flags
    runner.ROOT=ROOT
    checks=InputChecks()
    for p,h in plan['pins'].items():checks.check(ROOT/p,h)
    args=argparse.Namespace(seconds=5.0,max_states=2000000,outer_grace=0.0,memory_mib=2048,track_resources=True,
        linux_cpus=None,perf=False,rust_original=True,native_original=False,rust_original_method=[],
        native_tools={m:dict(binary=str(ROOT/plan['binary']),engine=m) for m in ['walk-guided','relaxed-batched']},
        buffer_agglomeration_method=[],target_zero_trap_method=[],target_path_potential_method=[],
        geometric_branches_method=[],native_python=Path(sys.executable),validation_seconds=60.0,validation_memory_mib=2048,
        validation_response_mib=64,validation_dag_work=200000000,bounded_validation=True)
    queries={c:{q['name']:q for q in json.loads((ROOT/p/'manifest.json').read_text())['queries']} for c,p in plan['corpora'].items()}
    OUT.mkdir()
    for c in plan['corpora']:(OUT/c).mkdir()
    save(HERE/'diagnostic-execution.json',dict(plan_sha256=sha(plan_path),started_utc=datetime.now(timezone.utc).isoformat()))
    count=0;complete=False;issues=[]
    try:
        with (OUT/'runs.jsonl').open('x') as stream:
            for item in plan['schedule']:
                assert not workspace_workloads(ROOT)
                checks.unchanged()
                q=queries[item['corpus']][item['query']]
                row=runner.rust_original(q,ROOT/plan['corpora'][item['corpus']],OUT/item['corpus'],item['method'],0,args)
                row.update(item, family=q['family'])
                if row['verdict'] in ('reachable','unreachable') and (failure_flags(row) or not native_checked(row,q)):
                    issues.append(item)
                stream.write(json.dumps(row)+'\n');stream.flush();count+=1
                print(item['query'],item['method'],row['verdict'],round(row['wall_seconds'],3),flush=True)
        checks.unchanged();complete=True
    finally:
        save(HERE/'diagnostic-terminal.json',dict(plan_sha256=sha(plan_path),completed=complete,rows=count,issues=issues,
            artifacts={str(p.relative_to(ROOT)):sha(p) for p in OUT.rglob('*') if p.is_file()}))

if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    elif sys.argv[1]=='run':run()
    else:raise ValueError('Expected freeze or run')
