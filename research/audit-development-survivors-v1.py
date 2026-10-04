"""Audit the complete survivor budget sweep, preserving all unknowns."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'research/development-survivors-v1'
S = ROOT / 'results/solver-portfolio-reduced-development-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads((F / 'plan.json').read_text())
rows = [json.loads(x) for x in (F / 'runs.jsonl').read_text().splitlines()]
for group in ['selection_sha256', 'input_sha256']:
    for path, digest in plan[group].items():
        assert sha(ROOT / path) == digest, path
for mode, digest in plan['binary_sha256'].items():
    assert sha(S / plan['modes'][mode][0]) == digest
assert sha(ROOT / 'research/probe-development-survivors-v1.py') == plan['script_sha256']
assert sha(ROOT / 'research/portfolio-reduced-development-v1/plan.json') == plan['source_plan_sha256']
assert json.loads((F / 'terminal.json').read_text()) == {'exit_code': 0, 'rows': 18}
expected = set(itertools.product(plan['properties'], plan['modes'], plan['budgets']))
assert len(rows) == plan['rows'] == len(expected)
assert {(r['query'], r['mode'], r['seconds']) for r in rows} == expected
manifest = json.loads((ROOT / 'benchmarks/mcc2021-development/manifest.json').read_text())
queries = {q['name']: q for q in manifest['queries']}
reasons = Counter()
expired = over_share = memory = 0
peak = 0
for row in rows:
    branches = row['branches']
    query = queries[row['query']]
    assert [b['branch'] for b in branches] == list(range(len(branches)))
    assert 0 < len(branches) <= len(query['branches'])
    accepted = []
    for b in branches:
        prefix = F / f"{row['query']}.{row['seconds']}.{row['mode']}.{b['branch']}"
        log = Path(str(prefix) + '.json')
        assert sha(log) == b['log_sha256']
        cmd = b['command']
        binary, engine = plan['modes'][row['mode']]
        assert cmd[0] == str(S / binary)
        assert cmd[1] == '--json' and cmd[3:6] == ['--method', engine, '--seconds']
        assert cmd[7:] == ['--max-states', str(plan['max_states'])]
        problem = (ROOT / 'benchmarks/mcc2021-development' / query['branches'][b['branch']]['path']).resolve()
        assert Path(cmd[2]).resolve() == problem
        assert str(problem.relative_to(ROOT)) in plan['input_sha256']
        share = float(cmd[6])
        assert 0 < share <= row['seconds'] / (len(query['branches']) - b['branch'])
        resource = b['resources']
        assert resource['memory_limit_bytes'] == plan['sampled_memory_bytes']
        memory += resource['memory_limit_exceeded']
        peak = max(peak, resource['sampled_peak_rss_bytes'])
        expired += b['expired']
        over_share += b['wall'] > share
        try:
            answer = json.loads(log.read_text())
        except ValueError:
            answer = {}
        for key, recorded in [('verdict', 'candidate_verdict'), ('reason', 'reason'), ('states', 'states')]:
            assert answer.get(key) == b[recorded]
        eligible = (b['exit_code'] == 0 and not b['expired'] and b['wall'] <= share
                    and not resource['memory_limit_exceeded'])
        if b['verdict'] != 'unknown':
            assert eligible and b['verdict'] == answer['verdict']
            check = b['check']
            assert check['exit_code'] == 0 and not check['expired']
            assert check['wall'] <= plan['checker_seconds']
            assert not check['resources']['memory_limit_exceeded']
            receipt = Path(str(prefix) + '.check.json')
            assert sha(receipt) == check['log_sha256']
            assert json.loads(receipt.read_text())['status'] == 'passed'
        accepted.append(b['verdict'])
        reasons[b['reason'] or 'no JSON answer'] += 1
    verdict = ('reachable' if 'reachable' in accepted else
               'unreachable' if len(branches) == len(query['branches']) and
               all(x == 'unreachable' for x in accepted) else 'unknown')
    assert row['verdict'] == verdict
    if verdict != 'unknown':
        assert row['solver_wall_seconds'] <= row['seconds']
result = dict(status='passed', rows=len(rows), verdicts=dict(Counter(r['verdict'] for r in rows)),
              branch_verdicts=dict(Counter(b['verdict'] for r in rows for b in r['branches'])),
              branches=sum(len(r['branches']) for r in rows), reasons=dict(reasons),
              expired_branches=expired, branches_over_assigned_wall=over_share,
              memory_limit_branches=memory, sampled_peak_rss_bytes=peak,
              plan_sha256=sha(F / 'plan.json'), rows_sha256=sha(F / 'runs.jsonl'),
              audit_script_sha256=sha(Path(__file__)))
(F / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
