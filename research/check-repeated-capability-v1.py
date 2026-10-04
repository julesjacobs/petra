"""Audit fresh capability runs and the explicit seed-only derivations."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'research/repeated-comparison-linux-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_application_expansion import registered_native_tools
suite=json.loads((F/'suite.json').read_text())
q=json.loads((F/'qualification.json').read_text())
assert q['status']=='passed' and q['suite_sha256']==sha(F/'suite.json')
collection=json.loads((F/'capability-collection.json').read_text())
for path,digest in collection['files_sha256'].items():assert sha(ROOT/path)==digest,path
fresh=[]
for b in suite['blocks']:
    f=F/b['name'];p=json.loads((f/'plan.json').read_text());r=json.loads((f/'capability.json').read_text())
    assert sha(f/'plan.json')==b['plan_sha256']
    assert sha(f/'capability.json')==q['capability_sha256'][b['name']]
    assert r['status']=='passed' and r['plan_sha256']==b['plan_sha256']
    assert r['methods']==list(p['methods']) and r['runner_archive_sha256']==p['runner_archive_sha256']
    if 'derivation' in r:
        d=r['derivation'];source=ROOT/d['source'];parent=json.loads(source.read_text())
        assert sha(source)==d['source_sha256'] and sha(source.parent/'plan.json')==d['source_plan_sha256']
        pp=json.loads((source.parent/'plan.json').read_text())
        changes={k for k in p if p[k]!=pp[k]}
        assert changes==set(d['changed_fields'])=={'output','order_seed','suite_block','capability_preflight'}
        expected=dict(parent,plan_sha256=b['plan_sha256'],derivation=d)
        assert r==expected
        continue
    o=ROOT/f"results/linux-repeated-capability-{p['seconds']}s-v1"
    assert r['runs_sha256']==sha(o/'runs.jsonl') and r['environment_sha256']==sha(o/'environment.json')
    assert r['harness_receipt_sha256']==sha(f/'capability-harness.json')
    environment=json.loads((o/'environment.json').read_text())
    registered_native_tools(p,environment)
    rows=[json.loads(x) for x in (o/'runs.jsonl').read_text().splitlines()]
    assert Counter((x['query'],x['method'],x['repeat']) for x in rows)==Counter((name,m,0) for name in r['expected'] for m in p['methods'])
    for x in rows:
        assert x['property_truth'] is r['expected'][x['query']]
        assert x['exit_code']==0 and not x['outer_timeout']
        resources=x['resources']
        assert resources['cpus']==[8] and resources['memory_limit_bytes']==2**31
        assert resources['runner']=='linux-systemd-user' and not resources.get('memory_limit_exceeded')
        assert resources['perf_enabled'] and resources['perf_counters']['instructions:u']['value']>0
        if x['method'].startswith('native-'):
            assert x['independent_checks'] and x['validation']['exit_code']==0
            assert not x['validation']['outer_timeout'] and not x['validation']['resources']['memory_limit_exceeded']
    assert len(r['component_rows'])==5
    for x in r['component_rows']:
        assert x['passed'] and x['exit_code']==0 and not x['expired']
        assert sha(f/'components'/f"{x['method']}-{x['label']}.log")==x['log_sha256']
    fresh.append(p['seconds'])
assert sorted(fresh)==[5,30]
result=dict(status='passed',suite_sha256=sha(F/'suite.json'),qualification_sha256=sha(F/'qualification.json'),
            fresh_harness_rows=32,fresh_component_rows=10,derived_blocks=4,
            collector_archive_sha256=collection['archive_sha256'],audit_script_sha256=sha(Path(__file__)))
(F/'capability-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
