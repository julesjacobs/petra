"""Reconcile original-input validation and all seed rows without rerunning solvers."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/walk-gap-pilot-v1'
OUT=ROOT/'results/local-walk-gap-pilot-v1'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(path.read_text())

plan=read(BASE/'plan.json');env=read(OUT/'environment.json')
for name,digest in plan['file_sha256'].items():assert sha(ROOT/name)==digest,name
for name,digest in env['script_sha256'].items():
    assert sha(OUT/'runner-source'/name)==digest==plan['file_sha256']['scripts/'+name]
assert env['seconds']==5 and env['repeat']==1 and env['memory_mib']==2048
assert env['max_states']==2000000 and env['outer_grace']==0
assert env['bounded_validation']['enabled'] and env['bounded_validation']['seconds']==60
for name,tool in env['native_tools'].items():
    assert sha(Path(tool['binary']))==tool['binary_sha256']
    if name!='native-batched':
        seed=int(name.rsplit('-',1)[1]);assert seed in plan['seeds']
        assert tool['engine']=='walk'
    else:assert tool['engine']=='portfolio-batched' and tool['binary_sha256']==plan['binary_sha256']
manifest=read(ROOT/'benchmarks/application-portfolio-comparison-v1/manifest.json')
queries={q['name']:q for q in manifest['queries'] if q['name'] in plan['cases']}
rows=[json.loads(line) for line in (OUT/'runs.jsonl').read_text().splitlines()]
assert len(rows)==36 and {(r['query'],r['method'],r['repeat']) for r in rows}=={(q,m,0) for q in queries for m in plan['methods']}
verdicts=defaultdict(set)
for row in rows:
    q=queries[row['query']];label=f"{row['query']}.{row['method']}.0.rust-original.json"
    answer_path=OUT/label
    assert row['collection_status']=='imported' and row['execution_attempted']
    assert row['command'][0]==env['native_tools'][row['method']]['binary']
    assert row['command'][row['command'].index('--method')+1]==env['native_tools'][row['method']]['engine']
    assert row['command'][row['command'].index('--seconds')+1]=='5.0'
    if 'validation' in row:
        request=read(OUT/(label+'.validation-request.json'))
        assert request['query']==q and request['mode']=='rust-original-v1'
        assert request['log']==str(answer_path)
        assert request['corpus']==str(ROOT/'benchmarks/application-portfolio-comparison-v1') and request['artifacts']==str(OUT)
        assert request['exit_code']==row['exit_code'] and request['outer_timeout']==row['outer_timeout']
        validation=row['validation']; response_path=OUT/(label+'.validation-response.json')
        if validation['exit_code']==0 and not validation['outer_timeout']:
            response=read(response_path)
            assert all(row.get(key)==value for key,value in response.items())
    if row['verdict'] in ['reachable','unreachable']:
        verdicts[row['query']].add(row['verdict'])
        assert row['exit_code']==0 and not row['outer_timeout'] and not row['resources']['memory_limit_exceeded']
        assert validation['exit_code']==0 and not validation['outer_timeout'] and not validation['resources']['memory_limit_exceeded']
        assert row['translation_check']=='independent-original-input-equals-all-canonical-branches'
        answer=read(answer_path)
        assert answer['verdict']==row['verdict'] and not answer['deadline_exceeded']
        assert answer['property_id']==q['property_id'] and answer['property_kind']==q['kind']
        assert answer['branch_count']==len(q['branches'])
        checked=lambda b,v:b['verdict']==v and b.get('independent_check','').startswith('python-')
        if row['verdict']=='reachable':assert any(checked(b,'reachable') for b in row['branches'])
        else:
            assert len(row['branches'])==len(q['branches']) and all(checked(b,'unreachable') for b in row['branches'])
        if row['method'].startswith('native-walk-'):
            assert row['verdict']=='reachable'
            seed=row['method'].rsplit('-',1)[1]
            assert any(a['outcome']['verdict']=='reachable' and f'seed={seed};' in a['outcome']['reason'] for a in answer['attempts'])
assert all(len(values)<=1 for values in verdicts.values())
report=dict(status='passed',rows=36,queries=9,
            coverage={m:dict(Counter(r['verdict'] for r in rows if r['method']==m)) for m in plan['methods']},
            checked_definitive_rows=sum(r['verdict'] in ['reachable','unreachable'] for r in rows),
            artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in OUT.rglob('*') if p.is_file()},
            scope='Saved original-input translation/witness/proof check reconciliation, frozen wrapper/underlying binary/input/runner hashes. Every seed kept separately; no best-seed substitution, repeated-run stability or competitive Linux timing claim.')
report['artifact_sha256']['research/walk-gap-pilot-v1/plan.json']=sha(BASE/'plan.json')
(BASE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='artifact_sha256'},indent=2))
