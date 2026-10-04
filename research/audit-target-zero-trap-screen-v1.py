"""Read-only audit of the registered target-zero trap screen and saved replay."""
import collections
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from analyze_original_comparison import analyze

NAME = 'target-zero-trap-screen-v1'
folder = ROOT/'results'/NAME
plan_path = ROOT/'research'/f'{NAME}-plan.json'
plan = json.loads(plan_path.read_text())
env = json.loads((folder/'environment.json').read_text())
corpus = ROOT/plan['corpus']
manifest = json.loads((corpus/'manifest.json').read_text())
rows = [json.loads(line) for line in (folder/'runs.jsonl').read_text().splitlines()]


def require(condition, message):
    if not condition:
        raise ValueError(message)


hashes = {}
def digest(path):
    path = path.resolve()
    if path not in hashes:
        with path.open('rb') as stream:
            hashes[path] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return hashes[path]


def read(path):
    return json.loads(path.read_text())


require(plan['properties']==104 and plan['expected_rows']==208 and len(rows)==208, 'Wrong denominator')
require(env['methods']==list(plan['methods'])==['before','after'], 'Wrong methods')
require(env['target_zero_trap_methods']==plan['target_zero_trap_methods']==['after'], 'Wrong flag configuration')
require(plan['profiling'] is False, 'Profiling plan differs')
require(digest(corpus/'manifest.json')==plan['manifest_sha256']==env['manifest_sha256'], 'Manifest differs')
require(env['rust_original'] and env['track_resources'] and not env['native_original'], 'Wrong input/resource mode')
require(env['rust_original_methods']==[] and env['linux_cpus'] is None and not env['perf'], 'Unexpected mode override')
for key in ('seconds','repeat','max_states','memory_mib','outer_grace','order_seed'):
    require(env[key]==plan[key], 'Environment differs:'+key)
require(env['seconds']==5 and env['repeat']==1 and env['outer_grace']==0 and env['memory_mib']==2048 and env['max_states']==2_000_000, 'Wrong limits')
require(env['bounded_validation']==dict(enabled=True,seconds=60,memory_mib=2048,response_mib=64,dag_check_max_work=200_000_000,included_in_solver_timing=False), 'Validation environment differs')
require(plan['validation']==dict(seconds=60,memory_mib=2048,response_mib=64,dag_max_work=200_000_000,separate_from_solver_timing=True), 'Validation plan differs')
for method,spec in plan['binaries'].items():
    require(digest(ROOT/spec['path'])==spec['sha256']==env['native_tools'][method]['binary_sha256'], 'Binary differs:'+method)
    require(env['native_tools'][method]['binary']==str(ROOT/spec['path']), 'Binary path differs:'+method)
    require(env['native_tools'][method]['engine']==plan['methods'][method]=='portfolio-focused', 'Engine differs:'+method)
    require(digest((ROOT/spec['path']).parent/'source.tar.gz')==plan['source_sha256'][method], 'Source archive differs:'+method)
require(plan['binaries']['before']==plan['binaries']['after'], 'Not the same frozen binary')
require(env['binary_sha256']==plan['binaries']['before']['sha256'], 'Default binary differs')
require(digest(Path(env['native_python']))==env['native_python_sha256'], 'Validation Python differs')
for name, expected in env['script_sha256'].items():
    require(digest(folder/'runner-source'/name)==expected, 'Runner snapshot differs:'+name)
    require(plan['required_file_sha256']['scripts/'+name]==expected, 'Runner registration differs:'+name)
current_runner_drift = []
for name, expected in plan['required_file_sha256'].items():
    if name.startswith('scripts/'):
        require(digest(folder/'runner-source'/Path(name).name)==expected, 'Registered runner snapshot differs:'+name)
        if digest(ROOT/name)!=expected:
            current_runner_drift.append(name)
    else:
        require(digest(ROOT/name)==expected, 'Registered input/artifact differs:'+name)

queries = {q['name']:q for q in manifest['queries']}
require(len(queries)==len(manifest['queries'])==104, 'Duplicate/missing properties')
require(env['queries']==104 and env['collection_counts']==dict(planned=104,imported=104,unsupported=0,explicitly_unobserved=0), 'Collection denominator differs')
order = list(queries)
random.Random(plan['order_seed']).shuffle(order)
require(env['property_order']==order, 'Randomized property order differs')
expected_order=[]
for i,name in enumerate(order):
    methods=env['methods'][i%2:]+env['methods'][:i%2]
    expected_order.extend((name,m,0) for m in methods)
require([(r['query'],r['method'],r['repeat']) for r in rows]==expected_order, 'Matrix/order differs')
inputs={}
for q in manifest['queries']:
    require(q['status']=='imported', 'Unexpected collection failure')
    pairs=[(corpus/q[k],q[k+'_sha256']) for k in ('net','property','pnml','xml')]
    pairs.extend((corpus/b['path'],b['sha256']) for b in q['branches'])
    for path, expected in pairs:
        require(digest(path)==expected, 'Manifest input differs:'+str(path))
        inputs[path.resolve()]=path.stat().st_size
require(env['input_preflight']==dict(mode='streaming-deduplicated-sha256',unique_files=len(inputs),bytes_hashed=sum(inputs.values())), 'Preflight count differs')

validation_rows=0
proofs=collections.defaultdict(collections.Counter)
raw_details={}
failures=[]
for r in rows:
    q=queries[r['query']]
    method=r['method']
    stem=f'{r["query"]}.{method}.0'
    expected=[str(ROOT/plan['binaries'][method]['path']), '--pnml',str(corpus/q['pnml']), '--xml',str(corpus/q['xml']), '--property-id',q['property_id'], '--method','portfolio-focused', '--seconds','5.0', '--max-states','2000000']
    if method=='after':
        expected.append('--target-zero-trap')
    require(r['command']==expected, 'Exact command differs:'+stem)
    require(r['input_mode']=='rust-original-v1' and r['suite']==q['suite'] and r['property_kind']==q['kind'], 'Input identity differs:'+stem)
    require(r['execution_attempted'] and r['collection_status']=='imported' and r['collection_observed']==q.get('observed') and r['property_slot']==q.get('property_slot'), 'Collection metadata differs:'+stem)
    require(r['resources']['memory_limit_bytes']==2048*1024**2, 'Memory limit differs:'+stem)
    if r['verdict'] in ('reachable','unreachable'):
        require(not r['outer_timeout'] and r['wall_seconds']<=5 and r['exit_code']==0, 'Definitive answer outside budget:'+stem)
        require(r['property_truth']==((r['verdict']=='reachable')==(q['kind']=='EF')), 'Property polarity differs:'+stem)
    else:
        require(r['property_truth'] is None, 'Unknown has property truth:'+stem)
    if r.get('validation_failure') or r.get('error') or r.get('failure_stage') or r['verdict']=='error':
        failures.append({k:r.get(k) for k in ('query','method','verdict','failure_stage','validation_failure','error')})
    if 'validation' not in r:
        require(r['outer_timeout'] and r['verdict']=='unknown' and not r['branches'] and not r['independent_checks'], 'Missing validation:'+stem)
        continue
    validation_rows+=1
    v=r['validation']
    for key,value in dict(seconds_limit=60,memory_limit_bytes=2048*1024**2,response_limit_bytes=64*1024**2,dag_check_max_work=200_000_000,included_in_solver_timing=False).items():
        require(v[key]==value, 'Validation limit differs:'+stem+'/'+key)
    answer=folder/(stem+'.rust-original.json')
    request=read(Path(str(answer)+'.validation-request.json'))
    response=read(Path(str(answer)+'.validation-response.json'))
    require(request['query']==q and request['corpus']==str(corpus) and request['log']==str(answer), 'Validation input differs:'+stem)
    require(request['mode']=='rust-original-v1' and request['memory_bytes']==v['memory_limit_bytes'] and request['response_bytes']==v['response_limit_bytes'] and request['dag_check_max_work']==v['dag_check_max_work'], 'Validation request limits differ:'+stem)
    for key in ('verdict','branches','independent_checks','translation_check'):
        require(response.get(key)==r.get(key), 'Validation result differs:'+stem+'/'+key)
    if r['verdict'] not in ('reachable','unreachable'):
        continue
    require(v['exit_code']==0 and not v['outer_timeout'] and not v['resources']['memory_limit_exceeded'], 'Definitive checker failure:'+stem)
    require(r['translation_check']=='independent-original-input-equals-all-canonical-branches', 'Missing independent translation check:'+stem)
    raw=read(answer)
    require(raw['verdict']==r['verdict'] and raw['property_truth']==r['property_truth'] and raw['property_id']==q['property_id'] and raw['property_kind']==q['kind'] and not raw['deadline_exceeded'], 'Raw answer differs:'+stem)
    details=[]
    for a in raw['attempts']:
        out=a['outcome']
        proof=out.get('proof')
        kind=proof.get('kind') if isinstance(proof,dict) else None
        if out['verdict']=='unreachable':
            proofs[method][kind or 'legacy-certificate']+=1
        details.append(dict(branch=a['branch'],verdict=out['verdict'],engine=out['method'],reason=out['reason'],proof_kind=kind))
    raw_details[stem]=dict(answer_sha256=digest(answer),attempts=details)

for q in manifest['queries']:
    if 'family' not in q:
        require(q['suite']=='fastforward-repository-random_walk', 'Missing family')
        q['family']='FastForward/'+q['instance'].split('.')[0]
suite=analyze(manifest,env,rows,'suite')
family=analyze(manifest,env,rows,'family')
replay=ROOT/'results'/f'{NAME}-lola-replay'
replay_report=read(replay/'report.json')
replay_rows=[json.loads(line) for line in (replay/'runs.jsonl').read_text().splitlines()]
positives={(r['query'],r['method'],r['repeat']) for r in rows if r['suite']=='fastforward-repository-random_walk' and r['verdict']=='reachable'}
require(len(replay_rows)==len(positives)==replay_report['expected_positives']==replay_report['completed'], 'Replay denominator differs')
require({(r['query'],r['method'],r['repeat']) for r in replay_rows}==positives, 'Replay matrix differs')
for name, expected in replay_report['sources'].items():
    require(digest(ROOT/name)==expected, 'Replay input differs:'+name)
for name, expected in replay_report['checker_sources'].items():
    require(digest(replay/'scripts'/name)==expected, 'Replay checker snapshot differs:'+name)
require(replay_report['source_manifest_sha256']==digest(ROOT/replay_report['source_corpus']/'manifest.json'), 'Replay source manifest differs')
replay_failures=[]
for r in replay_rows:
    stem=f'{r["query"]}.{r["method"]}.{r["repeat"]}'
    require(digest(folder/(stem+'.rust-original.json'))==r['answer_sha256'], 'Replayed answer differs:'+stem)
    response=read(ROOT/r['response'])
    accepted=response.get('verdict')=='reachable' and response.get('independent_check')=='python-original-lola-witness'
    require((r['status']=='verified')==accepted, 'Replay status differs:'+stem)
    if not accepted:
        replay_failures.append(r)
require(not replay_report['allow_unrebased_source_mapping'] and not replay_report['source_mapping_exceptions'], 'Unexpected legacy source-mapping exception')
comparison=suite['comparisons']['before -> after']
changed=[]
for kind in ('gained','lost'):
    for name in comparison[kind]:
        method='after' if kind=='gained' else 'before'
        r=next(r for r in rows if r['query']==name and r['method']==method)
        changed.append(dict(change=kind,query=name,method=method,verdict=r['verdict'],wall_seconds=r['wall_seconds'],branches=r['branches']))
groups=collections.defaultdict(list)
for q in manifest['queries']:
    groups[tuple(sorted(b['sha256'] for b in q['branches']))].append(q['name'])
categories={}
for category in sorted({q['challenge_category'] for q in manifest['queries']}):
    names={q['name'] for q in manifest['queries'] if q['challenge_category']==category}
    categories[category]=dict(properties=len(names),solved={m:sum(r['query'] in names and r['method']==m and r['verdict'] in ('reachable','unreachable') for r in rows) for m in env['methods']})
launch=ROOT/'research'/f'run-{NAME}.sh'
require('unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE' in launch.read_text(), 'Launcher does not disable profiling')
provenance={str(p.relative_to(ROOT)):digest(p) for p in (plan_path,folder/'environment.json',folder/'runs.jsonl',corpus/'manifest.json',replay/'report.json',launch,Path(__file__),ROOT/'scripts/analyze_original_comparison.py')}
report=dict(rows=len(rows),properties=len(queries),identities_and_limits_verified=True,input_files_hashed=len(inputs),input_bytes_hashed=sum(inputs.values()),registered_files_verified=len(plan['required_file_sha256']),runner_snapshots_verified=len(env['script_sha256']),current_runner_drift=current_runner_drift,checked_definitive_rows=sum(r['verdict'] in ('reachable','unreachable') for r in rows),validation_rows=validation_rows,failures=failures,original_lola_replay=dict(selected=len(positives),counts=replay_report['counts'],failures=replay_failures,legacy_mapping_exceptions=replay_report['source_mapping_exceptions']),categories=categories,families=family['families'],suites=suite['suites'],resources={m:dict(outer_timeouts=sum(r['outer_timeout'] for r in rows if r['method']==m),memory_limit_events=sum(bool(r['resources'].get('memory_limit_exceeded')) for r in rows if r['method']==m)) for m in env['methods']},comparison=comparison,changed_cases=changed,negative_proof_kinds={m:dict(c) for m,c in proofs.items()},definitive_raw_answers=raw_details,exact_branch_duplicate_groups=[v for v in groups.values() if len(v)>1],parent_denominators=[dict(corpus=s['corpus'],properties=s['full_denominator'],selected=s['selected']) for s in manifest['source_evidence']],profiling_evidence='Registered off; launcher unsets both profile flags. No per-phase reduction measurements are present.',sources=provenance,scope='One local five-second development screen with both labels using the same frozen binary. Parent denominator 620; no held-out or competitor comparison. Tied totals do not imply no effect; a conditional timing ratio from one run is not a speedup claim.')
suite['sources']=provenance
suite['scope']=report['scope']
(ROOT/'research'/f'{NAME}-analysis.json').write_text(json.dumps(suite,indent=2)+'\n')
(ROOT/'research'/f'{NAME}-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('definitive_raw_answers','sources','families','changed_cases')},indent=2))
