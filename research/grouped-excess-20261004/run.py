"""Freeze, run and audit a paired original-input development screen. Never builds."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT/'results/grouped-excess-20261004'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def load_runner(folder):
    sys.path.insert(0, str(folder/'scripts'))
    import benchmark_smpt_classic as runner
    runner.ROOT = ROOT
    return runner


def idle():
    import psutil
    from process_runner import workspace_workloads
    conflicts = workspace_workloads(ROOT)
    drivers = {'benchmark.py', 'benchmark_smpt_classic.py', 'collect_stress_mcc.py',
               'run-linux-application-expansion-v1.py', 'linux_benchmark_segments.py'}
    for process in psutil.process_iter():
        try:
            if process.pid == os.getpid() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            command = process.cmdline()
            if 'python' not in process.name().lower() or not Path(process.cwd()).is_relative_to(ROOT):
                continue
            if any(Path(a).name in drivers for a in command) or any('grouped-excess-20261004/run.py' in a for a in command):
                conflicts.append(dict(pid=process.pid, name=process.name(), command=command))
        except (psutil.Error, OSError):
            pass
    assert not conflicts, f'Overlapping workload: {conflicts}'


def freeze(candidate):
    assert not (HERE/'plan.json').exists() and not (HERE/'snapshot').exists()
    protocol = json.loads((HERE/'protocol.json').read_text())
    baseline = ROOT/protocol['baseline_binary']
    assert sha(baseline) == protocol['baseline_sha256']
    candidate = candidate.resolve()
    assert candidate.is_file() and os.access(candidate, os.X_OK)
    assert candidate != baseline.resolve()
    snapshot = HERE/'snapshot'
    snapshot.mkdir()
    source_pins = {}
    paths = [*sorted((ROOT/'scripts').glob('*.py')), *sorted((ROOT/'src').glob('*.rs')),
             ROOT/'Cargo.toml', ROOT/'Cargo.lock', HERE/'run.py', HERE/'protocol.json']
    for source in paths:
        rel = source.relative_to(ROOT)
        target = snapshot/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        source_pins[str(rel)] = sha(target)
    binaries = {}
    for label, source, engine in [('candidate', candidate, protocol['candidate_engine']),
                                  ('baseline', baseline, protocol['baseline_engine'])]:
        target = snapshot/(label+'-vass-reach')
        shutil.copy2(source, target)
        binaries[label] = dict(binary=str(target.relative_to(ROOT)), binary_sha256=sha(target),
                               engine=engine, original=str(source))
    input_pins = {}
    corpora = {}
    for spec in protocol['corpora']:
        corpus = ROOT/spec['path']
        manifest = corpus/'manifest.json'
        queries = json.loads(manifest.read_text())['queries']
        assert len(queries) == spec['properties']
        input_pins[str(manifest.relative_to(ROOT))] = sha(manifest)
        groups = defaultdict(list)
        for q in queries:
            if q['status'] != 'imported':
                groups[('unavailable', q['name'])].append(q['name'])
                continue
            groups[tuple(b['sha256'] for b in q['branches'])].append(q['name'])
            for p, h in [(q[k], q[k+'_sha256']) for k in ('pnml', 'xml', 'net', 'property')] + [(b['path'], b['sha256']) for b in q['branches']]:
                path = corpus/p
                key = str(path.relative_to(ROOT))
                if key not in input_pins:
                    assert sha(path) == h
                    input_pins[key] = h
                assert input_pins[key] == h
        assert len(groups) == spec['representatives']
        corpora[spec['name']] = dict(spec, queries=[q['name'] for q in queries],
                                    groups=[sorted(g) for g in groups.values()])
    stages = {}
    for stage, spec in protocol['stages'].items():
        schedule = []
        for ci, name in enumerate(spec['corpora']):
            corpus = corpora[name]
            queries = json.loads((ROOT/corpus['path']/'manifest.json').read_text())['queries']
            queries = [q for q in queries if spec['family'] is None or q['family'] == spec['family']]
            random.Random(protocol['order_seed']+ci).shuffle(queries)
            for qi, q in enumerate(queries):
                methods = protocol['methods'][qi % 2:]+protocol['methods'][:qi % 2]
                schedule.extend(dict(corpus=name, query=q['name'], method=m) for m in methods)
        assert len(schedule) == spec['expected_rows']
        stages[stage] = dict(spec, schedule=schedule)
    save(HERE/'plan.json', dict(protocol=protocol, protocol_sha256=sha(HERE/'protocol.json'),
        frozen_utc=now(), runner_sha256=sha(HERE/'run.py'), source_sha256=source_pins,
        input_sha256=input_pins, binaries=binaries, corpora=corpora, stages=stages,
        python=str(Path(sys.executable).absolute()), python_sha256=sha(Path(sys.executable)),
        candidate_provenance='Candidate binary supplied by root after tests/build. Current sources and checker scripts snapshot with binary; no build is performed by this harness.'))
    print(json.dumps(dict(status='frozen-not-run', plan_sha256=sha(HERE/'plan.json'),
                         diagnostic_rows=64, full_rows=736)))


def pin_checks(plan):
    from bounded_validation import InputChecks
    checks = InputChecks()
    checks.check(HERE/'run.py', plan['runner_sha256'])
    checks.check(HERE/'protocol.json', plan['protocol_sha256'])
    checks.check(Path(plan['python']), plan['python_sha256'])
    for p, h in plan['source_sha256'].items():
        checks.check(HERE/'snapshot'/p, h)
    for p, h in plan['input_sha256'].items():
        checks.check(ROOT/p, h)
    for tool in plan['binaries'].values():
        checks.check(ROOT/tool['binary'], tool['binary_sha256'])
    return checks


def arguments(plan):
    p = plan['protocol']
    return argparse.Namespace(seconds=p['seconds'], max_states=p['max_states'],
        outer_grace=p['outer_grace'], memory_mib=p['memory_mib'], track_resources=True,
        linux_cpus=None, perf=False, rust_original=True, native_original=False,
        rust_original_method=[], native_tools={m: dict(info, binary=str(ROOT/info['binary'])) for m, info in plan['binaries'].items()},
        buffer_agglomeration_method=p['buffer_agglomeration_methods'], target_zero_trap_method=[],
        target_path_potential_method=[], geometric_branches_method=[],
        native_python=Path(plan['python']), validation_seconds=p['validation_seconds'],
        validation_memory_mib=p['validation_memory_mib'], validation_response_mib=p['validation_response_mib'],
        validation_dag_work=p['validation_dag_work'], bounded_validation=True)


def run_stage(stage):
    plan = json.loads((HERE/'plan.json').read_text())
    runner = load_runner(HERE/'snapshot')
    checks = pin_checks(plan)
    idle()
    if stage == 'full':
        diagnostic = json.loads((HERE/'diagnostic-audit.json').read_text())
        assert diagnostic['status'] == 'passed' and diagnostic['plan_sha256'] == sha(HERE/'plan.json')
    folder = OUT/stage
    assert not folder.exists() and not (HERE/(stage+'-execution.json')).exists()
    folder.mkdir(parents=True)
    for name in plan['stages'][stage]['corpora']:
        (folder/name).mkdir()
    queries = {name: {q['name']: q for q in json.loads((ROOT/c['path']/'manifest.json').read_text())['queries']}
               for name, c in plan['corpora'].items()}
    args = arguments(plan)
    save(HERE/(stage+'-execution.json'), dict(plan_sha256=sha(HERE/'plan.json'), stage=stage, started_utc=now(), pid=os.getpid()))
    count = 0
    completed = False
    try:
        with (folder/'runs.jsonl').open('x') as output:
            for item in plan['stages'][stage]['schedule']:
                checks.unchanged()
                idle()
                q = queries[item['corpus']][item['query']]
                corpus = ROOT/plan['corpora'][item['corpus']]['path']
                result = runner.rust_original(q, corpus, folder/item['corpus'], item['method'], 0, args) if q['status'] == 'imported' else runner.import_failure(q)
                row = dict(item, repeat=0, family=q['family'], property_kind=q.get('kind'), **result)
                row.update(execution_attempted=q['status']=='imported', collection_status=q['status'])
                row['property_truth'] = runner.property_truth(q.get('kind'), row['verdict'])
                output.write(json.dumps(row)+'\n')
                output.flush()
                count += 1
                print(item['corpus'], item['query'], item['method'], row['verdict'], flush=True)
        checks.unchanged()
        completed = True
    finally:
        artifacts = {str(p.relative_to(ROOT)): sha(p) for p in folder.rglob('*') if p.is_file()}
        save(HERE/(stage+'-terminal.json'), dict(plan_sha256=sha(HERE/'plan.json'), stage=stage,
            finished_utc=now(), exit_code=0 if completed else 1, rows=count, artifact_sha256=artifacts))


def audit_stage(stage):
    plan = json.loads((HERE/'plan.json').read_text())
    runner = load_runner(HERE/'snapshot')
    from analyze_application_expansion import failure_flags, native_checked
    pin_checks(plan)
    terminal = json.loads((HERE/(stage+'-terminal.json')).read_text())
    execution = json.loads((HERE/(stage+'-execution.json')).read_text())
    assert terminal['plan_sha256'] == execution['plan_sha256'] == sha(HERE/'plan.json')
    assert terminal['exit_code'] == 0 and terminal['rows'] == plan['stages'][stage]['expected_rows']
    for p, h in terminal['artifact_sha256'].items():
        assert sha(ROOT/p) == h, p
    folder = OUT/stage
    rows = [json.loads(line) for line in (folder/'runs.jsonl').read_text().splitlines()]
    assert [{k: r[k] for k in ('corpus','query','method')} for r in rows] == plan['stages'][stage]['schedule']
    queries = {name: {q['name']: q for q in json.loads((ROOT/c['path']/'manifest.json').read_text())['queries']}
               for name, c in plan['corpora'].items()}
    issues = []
    truth = defaultdict(set)
    normalized_truth = defaultdict(set)
    accepted = set()
    for r in rows:
        q = queries[r['corpus']][r['query']]
        if q['status'] != 'imported':
            assert not r['execution_attempted'] and r['verdict'] == 'unsupported'
            continue
        tool = plan['binaries'][r['method']]
        corpus = ROOT/plan['corpora'][r['corpus']]['path']
        cmd = [str(ROOT/tool['binary']), '--pnml', str(corpus/q['pnml']), '--xml', str(corpus/q['xml']),
               '--property-id', q['property_id'], '--method', tool['engine'], '--seconds', str(plan['protocol']['seconds']),
               '--max-states', str(plan['protocol']['max_states']), '--buffer-agglomeration']
        assert r['command'] == cmd
        assert r['resources']['memory_limit_bytes'] == plan['protocol']['memory_mib']*1024**2
        assert type(r['wall_seconds']) in (int,float) and math.isfinite(r['wall_seconds']) and r['wall_seconds'] >= 0
        assert r['property_truth'] is runner.property_truth(q['kind'], r['verdict'])
        if r['verdict'] in ('reachable','unreachable'):
            flags = failure_flags(r)
            valid = not flags and native_checked(r, q) and not r['outer_timeout'] and r['exit_code'] == 0 and r['wall_seconds'] <= plan['protocol']['seconds']
            v = r['validation']
            valid &= v['included_in_solver_timing'] is False and v['seconds_limit'] == plan['protocol']['validation_seconds'] and v['memory_limit_bytes'] == plan['protocol']['validation_memory_mib']*1024**2 and v['response_limit_bytes'] == plan['protocol']['validation_response_mib']*1024**2
            log = folder/r['corpus']/f"{r['query']}.{r['method']}.0.rust-original.json"
            answer = json.loads(log.read_text())
            valid &= answer['verdict'] == r['verdict'] and answer['property_truth'] is r['property_truth'] and answer['deadline_exceeded'] is False and answer['property_id'] == q['property_id'] and answer['property_kind'] == q['kind'] and answer['branch_count'] == len(q['branches'])
            response = json.loads(Path(str(log)+'.validation-response.json').read_text())
            valid &= response['verdict'] == r['verdict'] and response['branches'] == r['branches'] and response['translation_check'] == r['translation_check']
            if not valid: issues.append(dict(corpus=r['corpus'], query=r['query'], method=r['method'], reason='Unacceptable definitive answer'))
            else:
                accepted.add((r['corpus'],r['query'],r['method']))
                truth[r['corpus'],r['query']].add(r['property_truth'])
                normalized_truth[tuple(b['sha256'] for b in q['branches'])].add(r['verdict'])
    assert all(len(values)<=1 for values in truth.values()), 'Cross-method disagreement'
    assert all(len(values)<=1 for values in normalized_truth.values()), 'Canonical duplicate disagreement'
    reports = {}
    cohorts = [('pooled',rows)] + [(name,[r for r in rows if r['corpus']==name]) for name in plan['stages'][stage]['corpora']]
    cohorts += [('family:'+family,[r for r in rows if r['family']==family]) for family in sorted({r['family'] for r in rows})]
    for label, chosen in cohorts:
        selected_queries = sorted({(r['corpus'],r['query']) for r in chosen})
        groups = defaultdict(list)
        for corpus, name in selected_queries:
            q = queries[corpus][name]
            key = tuple(b['sha256'] for b in q['branches']) if q['status']=='imported' else ('unavailable',corpus,name)
            groups[key].append((corpus,name))
        representatives = {min(g) for g in groups.values()}
        indexed = {(r['corpus'],r['query'],r['method']):r for r in chosen}
        views = {}
        for view, subset in [('all_properties',set(selected_queries)),('representatives',representatives)]:
            solved = {m:{q for q in subset if (*q,m) in accepted} for m in plan['protocol']['methods']}
            views[view] = dict(denominator=len(subset), methods={m:dict(solved=len(solved[m]),
                par2_mean_seconds=statistics.mean(indexed[*q,m]['wall_seconds'] if q in solved[m] else 2*plan['protocol']['seconds'] for q in subset),
                verdicts=dict(Counter(indexed[*q,m]['verdict'] for q in subset)),
                failure_flags=dict(Counter(flag for q in subset for flag in failure_flags(indexed[*q,m]))),
                solver_wall_total_seconds=sum(indexed[*q,m].get('wall_seconds',0) for q in subset),
                validation_wall_total_seconds=sum((indexed[*q,m].get('validation') or {}).get('wall_seconds',0) for q in subset)) for m in plan['protocol']['methods']},
                gains=[dict(corpus=c,query=q) for c,q in sorted(solved['candidate']-solved['baseline'])],
                losses=[dict(corpus=c,query=q) for c,q in sorted(solved['baseline']-solved['candidate'])])
        reports[label] = dict(views=views, duplicate_groups=[g for g in groups.values() if len(g)>1])
    result = dict(status='passed' if not issues else 'failed', plan_sha256=sha(HERE/'plan.json'), stage=stage,
        rows=len(rows), issues=issues, reports=reports, accepted_definitive_rows=len(accepted),
        terminal_sha256=sha(HERE/(stage+'-terminal.json')), scope=plan['protocol']['claim_scope'])
    save(HERE/(stage+'-audit.json'), result)
    print(json.dumps(result,indent=2))
    return int(bool(issues))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action',required=True)
    p = commands.add_parser('freeze'); p.add_argument('--candidate',type=Path,required=True)
    for name in ('run','audit'):
        p = commands.add_parser(name); p.add_argument('stage',choices=['diagnostic','full'])
    args = parser.parse_args()
    if args.action=='freeze':freeze(args.candidate)
    elif args.action=='run':run_stage(args.stage)
    else:return audit_stage(args.stage)
    return 0

if __name__=='__main__':raise SystemExit(main())
