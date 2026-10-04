"""Recompute every learned frontier independently with Python integer arithmetic."""
import json
import sys
from pathlib import Path

problem_path, log_path = map(Path, sys.argv[1:])
p = json.loads(problem_path.read_text())
events = [json.loads(line) for line in log_path.read_text().splitlines()]
summaries = []
cumulative_states = 0
for event in events:
    if event.get('event') != 'execution-frontier':
        continue
    counts = [0]*len(p['transitions'])
    previous = -1
    for t,n in event['counts']:
        assert previous < t < len(counts) and isinstance(n,int) and n > 0
        counts[t] = n
        previous = t
    final = list(p['initial'])
    for t,n in zip(p['transitions'],counts):
        for q,w in t['pre']: final[q] -= n*w
        for q,w in t['post']: final[q] += n*w
    assert min(final) >= 0

    def accepts(marking):
        for c in p['target']:
            value = sum(a*x for a,x in zip(c['coefficients'],marking))
            if (value != c['bound'] if c['equality'] else value < c['bound']):
                return False
        return True

    assert accepts(final)
    first = tuple(counts)
    seen = {first}
    pending = [(first,tuple(p['initial']))]
    frontier = set()
    while pending:
        remaining,marking = pending.pop()
        assert not accepts(marking), 'cut despite a reachable target prefix'
        for i,t in enumerate(p['transitions']):
            if any(marking[q] < w for q,w in t['pre']):
                continue
            if remaining[i] == 0:
                frontier.add(i)
                continue
            rest = list(remaining)
            rest[i] -= 1
            rest = tuple(rest)
            if rest in seen:
                continue
            after = list(marking)
            for q,w in t['pre']: after[q] -= w
            for q,w in t['post']: after[q] += w
            seen.add(rest)
            assert len(seen) <= 2_000_000
            pending.append((rest,tuple(after)))
    exact = [[t,counts[t]] for t in sorted(frontier)]
    assert exact == event['frontier']
    cumulative_states += len(seen)
    assert cumulative_states == event['states']
    assert event['model'] == len(summaries)+1
    summaries.append(dict(model=event['model'],states=len(seen),total_firings=sum(counts),
                          frontier=exact))
print(json.dumps(dict(status='passed',cuts=len(summaries),states=cumulative_states,models=summaries)))
