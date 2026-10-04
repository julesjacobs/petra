"""Paired coverage comparison of two complete, audited development screens."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = 'native-scheme-development-v2'
NEW = 'native-scheme-development-v3'


def load(name):
    folder = ROOT/'research'/name
    audit = json.loads((folder/'audit.json').read_text())
    assert audit['status'] == 'passed', name
    plan = json.loads((folder/'plan.json').read_text())
    rows = [json.loads(line) for line in (ROOT/'results'/name/'runs.jsonl').read_text().splitlines()]
    assert len(rows) == plan['rows']
    return plan, rows


def main():
    old, before = load(OLD)
    new, after = load(NEW)
    for field in ['properties', 'rows', 'modes', 'seconds', 'repeat', 'order_seed',
                  'query_order', 'input_sha256', 'native', 'z3_sha256', 'python',
                  'sampled_memory_bytes', 'checker_seconds', 'max_states', 'abmc_limits', 'native_scheme_limits', 'smt_reference']:
        assert old[field] == new[field], field
    assert [(r['query'], r['mode']) for r in before] == [(r['query'], r['mode']) for r in after]
    report = dict(scope='Paired development coverage; one shared-macOS repeat per candidate. '
                        'Exact root checks now precede arithmetic attempt accounting. '
                        'No stable timing, statistical significance, or held-out generalization claim.',
                  methods={}, evidence={})
    for name in [OLD, NEW]:
        for relative in [f'research/{name}/plan.json', f'research/{name}/audit.json', f'results/{name}/runs.jsonl']:
            report['evidence'][relative] = hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    for mode in old['modes']:
        a = {r['query']: r for r in before if r['mode'] == mode}
        b = {r['query']: r for r in after if r['mode'] == mode}
        result = dict(before=dict(Counter(r['verdict'] for r in a.values())),
                      after=dict(Counter(r['verdict'] for r in b.values())))
        assert not any({a[q]['verdict'], b[q]['verdict']} == {'reachable', 'unreachable'} for q in a)
        for verdict in ['reachable', 'unreachable']:
            left = {q for q, r in a.items() if r['verdict'] == verdict}
            right = {q for q, r in b.items() if r['verdict'] == verdict}
            result[verdict] = dict(gains=sorted(right-left), losses=sorted(left-right))
        for label, rows in [('before', a), ('after', b)]:
            capped = [(q, branch) for q, row in rows.items() for branch in row['branches']
                      if branch.get('reason') in ['search resource limit', 'agenda entry limit', 'discovery resource limit']]
            result[label+'_caps'] = dict(properties=sorted({q for q, _ in capped}),
                                         branch_reasons=dict(Counter(branch['reason'] for _, branch in capped)))
        report['methods'][mode] = result
    destination = ROOT/'research'/NEW/'paired-comparison.json'
    destination.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({mode: {key: r[key] for key in ['before', 'after']} for mode, r in report['methods'].items()}))


if __name__ == '__main__':
    main()
