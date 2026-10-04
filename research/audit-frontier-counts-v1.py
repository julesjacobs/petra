"""Audit the matched five-branch frontier-count diagnostic."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'research/frontier-counts-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads((F / 'plan.json').read_text())
for path,digest in plan['input_sha256'].items():
    assert sha(ROOT/path) == digest
for path,digest in plan['source_sha256'].items():
    assert sha(F/'source'/path) == digest
for mode,digest in plan['binary_sha256'].items():
    assert sha(F/mode) == digest
assert sha(Path(plan['checker'])) == plan['checker_sha256']
rows = [json.loads(x) for x in (F/'runs.jsonl').read_text().splitlines()]
assert len(rows) == plan['rows'] == 10
assert Counter((r['input'],r['mode']) for r in rows) == Counter(itertools.product(plan['input_sha256'],plan['modes']))
assert json.loads((F/'terminal.json').read_text()) == {'exit_code':0,'rows':10}
for r in rows:
    assert sha(F/r['log']) == r['log_sha256']
    assert r['command'] == [str(F/r['mode']),'--json',str(ROOT/r['input']),
                            '--method',plan['modes'][r['mode']],'--seconds','5','--max-states','2000000']
    assert r['resources']['memory_limit_bytes'] == plan['sampled_memory_bytes']
    try: answer = json.loads((F/r['log']).read_text())
    except ValueError: answer = {}
    assert answer.get('verdict') == r['candidate_verdict']
    assert answer.get('reason') == r['reason']
    assert answer.get('states') == r['states']
    if r['verdict'] != 'unknown':
        assert r['exit_code'] == 0 and not r['expired'] and r['wall'] <= plan['seconds']
        assert not r['resources']['memory_limit_exceeded']
        assert answer['verdict'] == r['verdict']
        c = r['check']
        assert c['exit_code'] == 0 and not c['expired'] and c['wall'] <= plan['checker_seconds']
        assert not c['resources']['memory_limit_exceeded']
        assert sha(F/c['log']) == c['log_sha256']
        assert json.loads((F/c['log']).read_text())['status'] == 'passed'
summary = dict(status='passed',rows=len(rows),coverage={m:dict(Counter(r['verdict'] for r in rows if r['mode']==m)) for m in plan['modes']},
               expired=sum(r['expired'] for r in rows),memory_limit_exceeded=sum(r['resources']['memory_limit_exceeded'] for r in rows),
               plan_sha256=sha(F/'plan.json'),rows_sha256=sha(F/'runs.jsonl'),audit_sha256=sha(Path(__file__)))
(F/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
