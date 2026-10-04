import collections
import hashlib
import json
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from replay_fastforward_results import check_source_query

folder = ROOT / 'results/target-closure-diagnostic-v1'
plan_path = ROOT / 'research/target-closure-diagnostic-v1-plan.json'
plan = json.loads(plan_path.read_text())
env = json.loads((folder / 'environment.json').read_text())
rows = [json.loads(line) for line in (folder / 'runs.jsonl').read_text().splitlines()]

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

require((folder / 'plan.json').read_bytes() == plan_path.read_bytes(), 'Plan differs')
require(env['plan'] == plan, 'Environment plan differs')
require(json.loads((folder/'completed.json').read_text()) == dict(rows=38, all_inputs_unchanged=True), 'Completion differs')
for method, spec in plan['binaries'].items():
    require(digest(ROOT/spec['path']) == spec['sha256'], 'Binary differs:'+method)
    require(digest((ROOT/spec['path']).parent/'source.tar.gz') == plan['source_sha256'][method], 'Source differs:'+method)
for name, expected in plan['selection_evidence'].items():
    require(digest(ROOT/name) == expected, 'Selection evidence differs:'+name)
corpus = ROOT / plan['corpus']
require(digest(corpus/'manifest.json') == plan['manifest_sha256'], 'Manifest differs')
for name, expected in env['runner_sha256'].items():
    require(digest(folder/'scripts'/name) == expected, 'Runner differs:'+name)
require(len(rows) == plan['expected_rows'] == 38, 'Wrong row count')
matrix = {(r['query'],r['method'],r['repeat']):r for r in rows}
require(len(matrix) == len(rows), 'Duplicate rows')
require(set(matrix) == {(n,m,0) for n in plan['queries'] for m in plan['methods']}, 'Incomplete matrix')
rng = random.Random(plan['order_seed'])
order = list(plan['queries'])
rng.shuffle(order)
require(order == env['query_order'], 'Query order differs')
expected_order = []
for name in order:
    methods = list(plan['methods'])
    rng.shuffle(methods)
    expected_order.extend((name,m,0) for m in methods)
require([(r['query'],r['method'],r['repeat']) for r in rows] == expected_order, 'Execution order differs')
queries = {q['name']:q for q in json.loads((corpus/'manifest.json').read_text())['queries']}
seen = set()
for name in plan['queries']:
    q = queries[name]
    for path, expected in [(corpus/q[k],q[k+'_sha256']) for k in ('pnml','xml')] + [(corpus/b['path'],b['sha256']) for b in q['branches']]:
        if path not in seen:
            require(digest(path) == expected, 'Input differs:'+str(path))
            seen.add(path)
require(len(seen) == env['input_files_hashed'] == 54, 'Input count differs')
require(sum(p.stat().st_size for p in seen) == env['input_bytes_hashed'], 'Input byte count differs')
checked = 0
stats = collections.defaultdict(collections.Counter)
cases = []
phase_keys = ['target_limit_evaluation','target_limit_directions','target_limit_seeds','target_limit_closure']
for name in plan['queries']:
    case = dict(query=name, methods={})
    answers = set()
    q = queries[name]
    for method in plan['methods']:
        r = matrix[name,method,0]
        stem = f'{name}.{method}.0'
        require(not r['other_profile_lines'], 'Non-JSON profile:'+stem)
        require(not r.get('validation_failure') and not r.get('error'), 'Validation failure:'+stem)
        require(r['exit_code'] == 0 and not r['outer_timeout'], 'Solver failed:'+stem)
        require(not r['resources']['memory_limit_exceeded'], 'Solver memory exceeded:'+stem)
        require(r['resources']['memory_limit_bytes'] == plan['memory_mib']*1024**2, 'Memory limit differs')
        command = [str(ROOT/plan['binaries'][method]['path']), '--pnml',str(corpus/q['pnml']), '--xml',str(corpus/q['xml']), '--property-id',q['property_id'], '--method',plan['methods'][method], '--seconds',str(plan['seconds']), '--max-states',str(plan['max_states'])]
        require(r['command'] == command, 'Command differs:'+stem)
        profile = folder/(stem+'.profile.jsonl')
        answer = folder/(stem+'.rust-original.json')
        require(r['profile'] == str(profile) and r['answer'] == str(answer), 'Artifact path differs:'+stem)
        wrapper = 'VASS_PORTFOLIO_PROFILE=1 VASS_RELAXED_PROFILE=1 exec '+shlex.join(command)+' 2>'+shlex.quote(str(profile))+'\n'
        require((folder/(stem+'.sh')).read_text() == wrapper, 'Profile invocation differs:'+stem)
        require([json.loads(line) for line in profile.read_text().splitlines()] == r['events'], 'Events differ:'+stem)
        v = r['validation']
        for key,value in dict(seconds_limit=30,memory_limit_bytes=2048*1024**2,response_limit_bytes=64*1024**2,dag_check_max_work=20000000,included_in_solver_timing=False).items():
            require(v[key] == value, 'Validation limit differs:'+stem+'/'+key)
        require(v['exit_code']==0 and not v['outer_timeout'] and not v['resources']['memory_limit_exceeded'], 'Checker failed:'+stem)
        response = json.loads(Path(str(answer)+'.validation-response.json').read_text())
        for key in ('verdict','branches','translation_check'):
            require(response[key] == r[key], 'Validation response differs:'+stem+'/'+key)
        require(r['translation_check']=='independent-original-input-equals-all-canonical-branches', 'Missing translation check:'+stem)
        if r['verdict'] in ('reachable','unreachable'):
            answers.add(r['verdict'])
            require(r['verdict']=='reachable' and any(b.get('verdict')=='reachable' and b.get('independent_check','').startswith('python-') for b in r['branches']), 'Unverified definitive answer')
            checked += 1
        attempts = [e['stats'] for e in r['events'] if e.get('event')=='relaxed-search']
        fallback = [s for s in attempts if not s['focused']]
        total = collections.Counter()
        for s in fallback:
            require(s['target_directed'] and s['stubborn'], 'Wrong fallback:'+stem)
            full = sum(s[k] for k in ('full_all_enabled','full_closure_limit','full_periodic','full_seen','full_visible'))
            require(s['expanded'] >= s['reductions']+full, 'Profile counts disagree:'+stem)
            if method=='after':
                require(sum(s[k] for k in phase_keys)==s['full_closure_limit'], 'Failure phases disagree:'+stem)
                require(s['target_early_all_enabled'] <= s['full_all_enabled'], 'Early count disagrees:'+stem)
            total.update({k:v for k,v in s.items() if isinstance(v,int) and not isinstance(v,bool)})
        total['incomplete_selection'] = total['expanded']-total['reductions']-sum(total[k] for k in ('full_all_enabled','full_closure_limit','full_periodic','full_seen','full_visible'))
        stats[method].update(total)
        ends = [e for e in r['events'] if e.get('event')=='phase-end']
        case['methods'][method] = dict(verdict=r['verdict'], fallback_attempts=len(fallback),fallback=dict(total),attempts=attempts,successful_phases=[e['name'] for e in ends if e['verdict']=='reachable'],relaxed_phases=[e for e in ends if 'relaxed::' in e['name']],parse_seconds=r['rust_parse_seconds'],solve_seconds=r['rust_solve_seconds'],wall_seconds=r['wall_seconds'],deadline_exceeded=r.get('deadline_exceeded',False),answer_sha256=digest(answer))
    require(len(answers)<=1, 'Disagreement:'+name)
    cases.append(case)

replay = ROOT/'results/target-closure-diagnostic-v1-lola-replay'
source_corpus = ROOT/'benchmarks/fastforward-import-v2'
source_manifest = json.loads((source_corpus/'manifest.json').read_text())
source_queries = {q['name']:q for q in source_manifest['queries']}
ff_names = {name for name in plan['queries'] if queries[name]['suite']=='fastforward-repository-random_walk'}
exceptions = []
for name in sorted(ff_names):
    exceptions.extend(check_source_query(queries[name],source_queries[name],corpus,source_corpus,allow_unrebased_mapping=True))
positives = [r for r in rows if r['query'] in ff_names and r['verdict']=='reachable']
if '--replay' in sys.argv:
    replay.mkdir(exist_ok=False)
    snapshot = replay/'scripts'
    snapshot.mkdir()
    for name in ('check_fastforward_source.py','fastforward_source_checker.py','process_runner.py','replay_fastforward_results.py','analyze_original_comparison.py'):
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    shutil.copyfile(__file__,snapshot/Path(__file__).name)
    records=[]
    for r in positives:
        stem=f'{r["query"]}.{r["method"]}.0'
        answer=folder/(stem+'.rust-original.json')
        request=dict(corpus=str(source_corpus),source=str(ROOT/'benchmarks/fastforward-repository-v1'),query=r['query'],answer=str(answer),seconds=30,memory_mib=2048,manifest_sha256=digest(source_corpus/'manifest.json'))
        request_path=replay/(stem+'.request.json')
        response_path=replay/(stem+'.response.json')
        request_path.write_text(json.dumps(request)+'\n')
        with (replay/(stem+'.driver.log')).open('w') as log:
            result=subprocess.run([str(ROOT/'vendor/venv/bin/python'),str(ROOT/'scripts/check_fastforward_source.py'),'--request',str(request_path),'--response',str(response_path)],stdout=log,stderr=subprocess.STDOUT)
        response=json.loads(response_path.read_text()) if response_path.exists() else {}
        records.append(dict(query=r['query'],method=r['method'],exit_code=result.returncode,response=response,answer_sha256=digest(answer)))
    replay_report=dict(selected=len(positives),records=records,source_mapping_exceptions=exceptions,scope='All FastForward positives in the complete 38-row diagnostic matrix; original-LoLA replay, separate from solver timing.',sources={str(p.relative_to(ROOT)):digest(p) for p in [folder/'runs.jsonl',plan_path,corpus/'manifest.json',source_corpus/'manifest.json']})
    (replay/'report.json').write_text(json.dumps(replay_report,indent=2)+'\n')
replay_report=json.loads((replay/'report.json').read_text())
require(replay_report['selected']==len(positives)==len(replay_report['records']), 'Replay count differs')
require({(r['query'],r['method']) for r in positives} == {(r['query'],r['method']) for r in replay_report['records']}, 'Replay matrix differs')
for r in replay_report['records']:
    response=r['response']
    require(r['exit_code']==0 and response.get('verdict')=='reachable' and response.get('independent_check')=='python-original-lola-witness', 'Source replay failed')
    require(digest(folder/f'{r["query"]}.{r["method"]}.0.rust-original.json')==r['answer_sha256'], 'Replayed answer differs')
report=dict(rows=len(rows),properties=len(cases),checked_definitive_rows=checked,original_lola_replay_verified=len(positives),input_files_verified=len(seen),identities_verified=True,limits_verified=True,counts={m:dict(collections.Counter(r['verdict'] for r in rows if r['method']==m)) for m in plan['methods']},fallback_queries={m:sum(c['methods'][m]['fallback_attempts']>0 for c in cases) for m in plan['methods']},positive_expansion_queries={m:sum(c['methods'][m]['fallback'].get('expanded',0)>0 for c in cases) for m in plan['methods']},fallback_totals={k:dict(v) for k,v in stats.items()},cases=cases,artifact_sha256={str(p.relative_to(ROOT)):digest(p) for p in [plan_path,folder/'runs.jsonl',folder/'environment.json',replay/'report.json']},caveat='Outcome-selected diagnostic subset, 7second outer cap, 5second internal budget, one repetition. Neither strict-screen timing nor an equal-work comparison. Counts aggregate distinct trajectories and branch attempts; before lacks phase and skipped-list counters, which must not be interpreted as measured zeros.')
(ROOT/'research/target-closure-diagnostic-v1-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('cases','artifact_sha256')},indent=2))
