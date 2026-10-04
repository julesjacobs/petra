"""Verify the saved original-input diagnostic and its preserved source identities."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'research/portfolio-walk-counts-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads((F / 'original-plan.json').read_text())
for name, digest in plan['source_sha256'].items():
    assert sha(F / 'snapshot/source' / name) == digest, name
for name, digest in plan['input_sha256'].items():
    assert sha(Path(name)) == digest, name
assert sha(F / 'snapshot/vass-reach') == plan['pins']['research/portfolio-walk-counts-v1/snapshot/vass-reach']
rows = json.loads((F / 'original-results.json').read_text())
assert [r['method'] for r in rows] == plan['methods']
summary = []
for row in rows:
    method = row['method']
    log = F / (method + '.original.json')
    assert sha(log) == row['log_sha256']
    cmd = row['command']
    assert cmd[0] == str(F / 'snapshot/vass-reach')
    for flag, value in [('--pnml', str(ROOT / 'benchmarks/general-development-v3' / plan['query']['pnml'])), ('--xml', str(ROOT / 'benchmarks/general-development-v3' / plan['query']['xml'])), ('--method', method), ('--seconds', '5'), ('--max-states', '2000000')]:
        assert cmd[cmd.index(flag) + 1] == value
    assert '--buffer-agglomeration' in cmd
    validation = row['validation']
    assert row['resources']['memory_limit_bytes'] == plan['memory_bytes']
    if method == 'portfolio-walk-counts':
        assert row['exit_code'] == 0 and not row['expired']
        assert not row['resources']['memory_limit_exceeded']
        assert row['wall'] < plan['seconds']
        assert validation['verdict'] == 'reachable'
        assert validation['independent_checks'] == ['python-witness']
        assert validation['translation_check'] == 'independent-original-input-equals-all-canonical-branches'
        assert not validation['deadline_exceeded']
        check = validation['validation']
        assert check['exit_code'] == 0 and not check['outer_timeout']
        assert not check['resources']['memory_limit_exceeded']
        answer = json.loads(log.read_text())
        attempt = answer['attempts'][0]
        assert attempt['branch'] == 0
        assert attempt['outcome']['method'] == 'sparse-count-plan'
        assert len(attempt['outcome']['trace']) == 29381
    else:
        assert validation['verdict'] == 'unknown'
        assert row['expired'] and row['exit_code'] == -9
    summary.append(dict(method=method, verdict=validation['verdict'], expired=row['expired'], wall=row['wall']))
artifacts = {str(p.relative_to(F)): sha(p) for p in F.glob('*') if p.is_file() and p.name != 'original-audit.json'}
result = dict(status='passed', rows=summary, artifact_sha256=artifacts, scope='Saved source/input identities and bounded independent-validator receipts; no new solver run or stable timing claim.')
(F / 'original-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result['rows']))
