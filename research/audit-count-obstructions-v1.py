"""Independently check initial firing counts and exhaust their execution orders."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'research/count-obstructions-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads((F / 'plan.json').read_text())
assert sha(F / 'candidate') == plan['binary_sha256']
assert sha(F / 'source.rs') == plan['source_sha256']
rows = [json.loads(x) for x in (F / 'runs.jsonl').read_text().splitlines()]
assert len(rows) == len(plan['inputs']) == 5
assert {r['input'] for r in rows} == set(plan['inputs'])
assert json.loads((F / 'terminal.json').read_text()) == {'exit_code': 0, 'rows': 5}
reports = []
for row in rows:
    assert sha(ROOT / row['input']) == plan['inputs'][row['input']]
    assert sha(F / row['log']) == row['log_sha256']
    assert row['exit_code'] == 0 and not row['expired']
    assert not row['resources']['memory_limit_exceeded']
    p = json.loads((ROOT / row['input']).read_text())
    a = json.loads((F / row['log']).read_text())
    if a['status'] == 'no-model':
        reports.append(dict(input=row['input'], status='no-model; no infeasibility conclusion'))
        continue
    counts = a['counts']
    assert len(counts) == len(p['transitions'])
    assert all(isinstance(x, int) and x >= 0 for x in counts)
    final = p['initial'].copy()
    for n, t in zip(counts, p['transitions']):
        for place, weight in t['pre']:
            final[place] -= n * weight
        for place, weight in t['post']:
            final[place] += n * weight
    assert min(final) >= 0
    for constraint in p['target']:
        value = sum(x*c for x,c in zip(final, constraint['coefficients']))
        assert value == constraint['bound'] if constraint['equality'] else value >= constraint['bound']

    def fire(marking, t):
        if any(marking[q] < w for q,w in t['pre']):
            return None
        result = list(marking)
        for q,w in t['pre']:
            result[q] -= w
        for q,w in t['post']:
            result[q] += w
        return tuple(result)

    marking = tuple(p['initial'])
    remaining = counts.copy()
    for i in a['greedy_prefix']:
        assert remaining[i] > 0
        remaining[i] -= 1
        marking = fire(marking, p['transitions'][i])
        assert marking is not None
    assert list(marking) == a['marking'] and remaining == a['remaining']
    enabled_outside = [i for i,t in enumerate(p['transitions'])
                       if remaining[i] == 0 and fire(marking, t) is not None]
    start = tuple(counts)
    seen = {start}
    queue = [(start, tuple(p['initial']))]
    edges = deadlocks = 0
    realized = False
    prefix_target = False
    frontier = set()
    while queue:
        left, marking = queue.pop()
        prefix_target |= all(
            (sum(x*c for x,c in zip(marking, constraint['coefficients'])) == constraint['bound']
             if constraint['equality'] else
             sum(x*c for x,c in zip(marking, constraint['coefficients'])) >= constraint['bound'])
            for constraint in p['target'])
        for i,n in enumerate(left):
            if n == 0 and fire(marking, p['transitions'][i]) is not None:
                frontier.add(i)
        if not any(left):
            realized = True
            break
        children = 0
        for i,n in enumerate(left):
            if n == 0:
                continue
            after = fire(marking, p['transitions'][i])
            if after is None:
                continue
            children += 1
            edges += 1
            rest = list(left)
            rest[i] -= 1
            rest = tuple(rest)
            if rest not in seen:
                seen.add(rest)
                assert len(seen) <= 100_000, 'diagnostic state bound'
                queue.append((rest, after))
        deadlocks += children == 0
    reports.append(dict(input=row['input'], status='fixed-count-vector-exhausted' if not realized else 'realizable',
                        total_firings=sum(counts), explored_states=len(seen), edges=edges,
                        deadlocks=deadlocks, greedy_prefix_length=len(a['greedy_prefix']),
                        any_prefix_satisfies_target=prefix_target,
                        escape_frontier=[dict(transition=i, name=p['transitions'][i]['name'],
                                              minimum_total_count=counts[i]+1) for i in sorted(frontier)],
                        enabled_outside_remaining_counts=enabled_outside))
result = dict(status='passed', scope='fixed count vectors only; no original property verdicts',
              plan_sha256=sha(F / 'plan.json'), rows_sha256=sha(F / 'runs.jsonl'),
              audit_script_sha256=sha(Path(__file__)), results=reports)
(F / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
