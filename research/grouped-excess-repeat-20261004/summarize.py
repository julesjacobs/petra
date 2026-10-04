"""Report two complete audited repetitions without mixing earlier candidate versions."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[2]
F=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((F/'plan.json').read_text())
rows={};audits={}
for block in ['repeat1','repeat2']:
    audit=json.loads((F/(block+'-audit.json')).read_text())
    assert audit['status']=='passed' and audit['plan_sha256']==sha(F/'plan.json')
    audits[block]=audit
    terminal=json.loads((F/(block+'-terminal.json')).read_text())
    assert sha(F/(block+'-terminal.json'))==audit['terminal_sha256']
    raw=ROOT/'results/grouped-excess-repeat-20261004'/block/'runs.jsonl'
    assert sha(raw)==terminal['artifact_sha256'][str(raw.relative_to(ROOT))]
    entries=[json.loads(line) for line in raw.read_text().splitlines()]
    rows[block]={(r['corpus'],r['query'],r['method']):r for r in entries}
    assert len(entries)==len(rows[block])==736
queries={}
for name,corpus in plan['corpora'].items():
    for q in json.loads((ROOT/corpus['path']/'manifest.json').read_text())['queries']:
        queries[name,q['name']]=q
methods=plan['protocol']['methods']
solved=lambda r:r['verdict'] in ('reachable','unreachable') and r.get('property_truth') is not None
reports={}
for label,selected in [('pooled',set(queries))]+[(name,{q for q in queries if q[0]==name}) for name in plan['corpora']]:
    groups=defaultdict(list)
    for key in selected:
        q=queries[key]
        fingerprint=tuple(b['sha256'] for b in q['branches']) if q['status']=='imported' else ('unavailable',*key)
        groups[fingerprint].append(key)
    views={}
    for view,subset in [('all_properties',selected),('representatives',{min(g) for g in groups.values()})]:
        sets={m:[{q for q in subset if solved(rows[b][*q,m])} for b in rows] for m in methods}
        stable={m:set.intersection(*s) for m,s in sets.items()};ever={m:set.union(*s) for m,s in sets.items()}
        common=stable['candidate']&stable['baseline']
        per_method={}
        for method in methods:
            observations=[rows[b][*q,method] for b in rows for q in subset]
            per_method[method]=dict(solved_by_repeat=[len(s) for s in sets[method]],stable=len(stable[method]),any_repeat=len(ever[method]),
                solver_par2_mean_seconds=statistics.mean(r['wall_seconds'] if solved(r) else 2*plan['protocol']['seconds'] for r in observations),
                solver_wall_total_seconds=sum(r.get('wall_seconds',0) for r in observations),
                validation_wall_total_seconds=sum((r.get('validation') or {}).get('wall_seconds',0) for r in observations),
                end_to_end_wall_total_seconds=sum(r.get('wall_seconds',0)+(r.get('validation') or {}).get('wall_seconds',0) for r in observations))
        ratios={}
        for timing in ['solver','solver_plus_validation']:
            def value(r):return r['wall_seconds']+((r.get('validation') or {}).get('wall_seconds',0) if timing=='solver_plus_validation' else 0)
            values=[statistics.median(value(rows[b][*q,'baseline']) for b in rows)/statistics.median(value(rows[b][*q,'candidate']) for b in rows) for q in common]
            ratios[timing]=math.exp(statistics.mean(math.log(v) for v in values)) if values else None
        views[view]=dict(denominator=len(subset),methods=per_method,
            gains_by_repeat=[sorted(a-b) for a,b in zip(sets['candidate'],sets['baseline'])],
            losses_by_repeat=[sorted(b-a) for a,b in zip(sets['candidate'],sets['baseline'])],
            stable_gain_queries=sorted(set.intersection(*(a-b for a,b in zip(sets['candidate'],sets['baseline'])))),
            stable_loss_queries=sorted(set.intersection(*(b-a for a,b in zip(sets['candidate'],sets['baseline'])))),
            common_solved=dict(queries=sorted(common),geometric_mean_baseline_over_candidate=ratios,
                scope='Selected queries solved by both methods in both repeats; medians per query.'))
    reports[label]=views
result=dict(status='two-complete-audited-repeats',plan_sha256=sha(F/'plan.json'),rows=1472,reports=reports,
    audit_sha256={b:sha(F/(b+'-audit.json')) for b in rows},scope=plan['protocol']['claim_scope'])
with (F/'summary.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps(result,indent=2))
