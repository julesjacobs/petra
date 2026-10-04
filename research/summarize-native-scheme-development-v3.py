"""Summarize an audited full native/SMT development comparison without timing claims."""
from collections import Counter
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'research/native-scheme-development-v3'
OUT = ROOT/'results/native-scheme-development-v3'


def main():
    audit = json.loads((HERE/'audit.json').read_text())
    assert audit['status'] == 'passed'
    data = (OUT/'runs.jsonl').read_bytes()
    assert hashlib.sha256(data).hexdigest() == audit['runs_sha256']
    rows = [json.loads(line) for line in data.splitlines()]
    plan = json.loads((HERE/'plan.json').read_text())
    initial = set()
    corpus = ROOT/'benchmarks/mcc2021-development'
    for query in json.loads((corpus/'manifest.json').read_text())['queries']:
        for branch in query['branches']:
            p = json.loads((corpus/branch['path']).read_text())
            if all((sum(c*m for c,m in zip(t['coefficients'],p['initial'])) == t['bound']) if t['equality']
                   else (sum(c*m for c,m in zip(t['coefficients'],p['initial'])) >= t['bound']) for t in p['target']):
                initial.add(query['name'])
                break
    result = dict(scope='Complete audited development screen. Completed-branch phase totals describe recorded work only; '
                        'killed branches have missing statistics. No stable timing or superiority claim.',
                  initial_properties=len(initial), methods={}, pairs=audit['positive_pairs'])
    for mode in plan['modes']:
        selected = [r for r in rows if r['mode'] == mode]
        positives = {r['query'] for r in selected if r['verdict'] == 'reachable'}
        reasons, counts, phases = Counter(), Counter(), Counter()
        samples = []
        for row in selected:
            for branch in row['branches']:
                reasons[str(branch.get('reason'))] += 1
                counts['attempted_branches'] += 1
                counts['expired_branches'] += branch['expired']
                counts['memory_limit_branches'] += branch['resources']['memory_limit_exceeded']
                path = OUT/f"{row['query']}.{mode}.{branch['branch']}.json"
                try: answer = json.loads(path.read_text())
                except ValueError: answer = {}
                stats = answer.get('statistics')
                if stats is None:
                    counts['branches_without_native_statistics'] += 1
                    continue
                counts['branches_with_native_statistics'] += 1
                for key in ['schemes','prefix_refutations','root_guard_checks','root_refutations','arithmetic_unknown','discovery_truncated']:
                    counts[key] += stats[key]
                for key in ['discovery_seconds','target_seconds','prefix_seconds']:
                    phases[key] += stats[key]
                samples.append(dict(query=row['query'],branch=branch['branch'],verdict=branch['verdict'],statistics=stats))
        result['methods'][mode] = dict(coverage=dict(Counter(r['verdict'] for r in selected)),
                                      initial_positives=len(positives & initial),noninitial_positives=len(positives-initial),
                                      reasons=dict(reasons),counts=dict(counts),completed_branch_phase_seconds=dict(phases),samples=samples)
    (HERE/'diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({mode:{key:value for key,value in r.items() if key != 'samples'} for mode,r in result['methods'].items()}))


if __name__ == '__main__': main()
