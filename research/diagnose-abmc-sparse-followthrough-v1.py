"""Follow previously summary-capped branches through the audited sparse run."""
from collections import Counter
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OLD = 'abmc-mcc-development-v1'
NEW = 'abmc-mcc-sparse-v1'
for name in [OLD, NEW]:
    assert json.loads((ROOT/'research'/name/'audit.json').read_text())['status'] == 'passed'
old = [json.loads(line) for line in (ROOT/'results'/OLD/'runs.jsonl').read_text().splitlines()]
new = {(r['query'], r['mode']): r for r in map(json.loads, (ROOT/'results'/NEW/'runs.jsonl').read_text().splitlines())}
report = dict(scope='Saved artifacts only; file existence identifies launched phases, not measured phase durations.', modes={})
for mode in ['ordinary', 'singleton', 'cycles']:
    details = []
    for row in old:
        if row['mode'] != mode:
            continue
        for branch in row['branches']:
            if branch.get('reason') != 'summary cell limit':
                continue
            query, index = row['query'], branch['branch']
            current = new[query, mode]
            b = next((x for x in current['branches'] if x['branch'] == index), None)
            assert b is not None
            folder = ROOT/'results'/NEW/f'{query}.{mode}.{index}.artifacts'
            phases = []
            for output in sorted(folder.glob('z3-*.stdout'), key=lambda p: int(p.stem.split('-')[1])):
                first = output.read_text().splitlines()
                phases.append(dict(depth=int(output.stem.split('-')[1]),
                                   first_line=first[0] if first else None,
                                   stdout_sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
            details.append(dict(query=query, branch=index, verdict=b['verdict'],
                                reason=b.get('reason'), expired=b['expired'], exit_code=b['exit_code'],
                                memory_limit_exceeded=b['resources']['memory_limit_exceeded'], phases=phases))
    report['modes'][mode] = dict(branches=len(details), properties=len({r['query'] for r in details}),
                                verdicts=dict(Counter(r['verdict'] for r in details)),
                                outer_expirations=sum(r['expired'] for r in details),
                                memory_limit_exceeded=sum(r['memory_limit_exceeded'] for r in details),
                                reasons=dict(Counter(str(r['reason']) for r in details)), details=details)
(ROOT/'research'/NEW/'previous-cap-followthrough.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({m:{k:v for k,v in r.items() if k != 'details'} for m,r in report['modes'].items()}))
