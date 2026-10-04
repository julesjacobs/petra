import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'results/target-stubborn-diagnostic-v1'
plan_path = ROOT / 'research/target-stubborn-diagnostic-v1-plan.json'
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
require(digest(ROOT / plan['binary']) == plan['binary_sha256'], 'Binary differs')
require(digest((ROOT / plan['binary']).parent / 'source.tar.gz') == plan['source_sha256'], 'Source differs')
corpus = ROOT / plan['corpus']
require(digest(corpus / 'manifest.json') == plan['manifest_sha256'], 'Manifest differs')
for name, expected in env['runner_sha256'].items():
    require(digest(folder / 'scripts' / name) == expected, f'Runner differs:{name}')
require(len(rows) == plan['expected_rows'] == 36, 'Wrong row count')
matrix = {(r['query'], r['method'], r['repeat']):r for r in rows}
require(len(matrix) == len(rows), 'Duplicate rows')
require(set(matrix) == {(n,m,0) for n in plan['queries'] for m in plan['methods']}, 'Incomplete matrix')
queries = {q['name']:q for q in json.loads((corpus / 'manifest.json').read_text())['queries']}
seen = set()
for name in plan['queries']:
    q = queries[name]
    for path, expected in [(corpus/q[k],q[k+'_sha256']) for k in ('pnml','xml')] + [(corpus/b['path'],b['sha256']) for b in q['branches']]:
        if path not in seen:
            require(digest(path) == expected, f'Input differs:{path}')
            seen.add(path)
checked = 0
stats = collections.defaultdict(collections.Counter)
cases = []
for name in plan['queries']:
    case = dict(query=name, methods={})
    answers = set()
    for method in plan['methods']:
        r = matrix[name,method,0]
        require(not r['other_profile_lines'], f'Non-JSON profile:{name}')
        require(not r.get('validation_failure') and not r.get('error'), f'Validation failure:{name}')
        require(r['resources']['memory_limit_bytes'] == 2048*1024**2, 'Memory limit differs')
        require(r['command'][r['command'].index('--method')+1] == plan['methods'][method], 'Wrong method')
        require(r['command'][r['command'].index('--seconds')+1] == str(plan['seconds']), 'Wrong deadline')
        if r['verdict'] in ('reachable','unreachable'):
            answers.add(r['verdict'])
            require(r['verdict']=='reachable' and any(b.get('verdict')=='reachable' and b.get('independent_check','').startswith('python-') for b in r['branches']), 'Unverified definitive answer')
            checked += 1
        fallback = [e['stats'] for e in r['events'] if e.get('event')=='relaxed-search' and not e['stats']['focused']]
        total = collections.Counter()
        for e in fallback:
            total.update({k:v for k,v in e.items() if isinstance(v,int) and not isinstance(v,bool)})
        full = sum(total[k] for k in ('full_all_enabled','full_closure_limit','full_periodic','full_seen','full_visible'))
        if method == 'after':
            total['incomplete_selection'] = total['expanded']-total['reductions']-full
            require(total['incomplete_selection']>=0, 'Profile counts disagree')
        stats[method].update(total)
        phases = [e['name'] for e in r['events'] if e.get('event')=='phase-end' and e['verdict']=='reachable']
        case['methods'][method] = dict(verdict=r['verdict'],fallback_attempts=len(fallback),fallback=dict(total),successful_phases=phases)
    require(len(answers)<=1, f'Disagreement:{name}')
    cases.append(case)
report = dict(rows=len(rows),properties=len(cases),checked_definitive_rows=checked,input_files_verified=len(seen),identities_verified=True,counts={m:dict(collections.Counter(r['verdict'] for r in rows if r['method']==m)) for m in plan['methods']},fallback_totals={k:dict(v) for k,v in stats.items()},cases=cases,caveat='Diagnostic 7second outer cap,5second internal budget,one repetition; not strict-screen timing or equal-work comparison. Counts aggregate distinct trajectories and branch attempts.')
(ROOT/'research/target-stubborn-diagnostic-v1-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
