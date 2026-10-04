"""Failure-preserving post-collection analysis; does not replace the registered summary."""
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
F = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'scripts'))
from analyze_application_expansion import failure_flags
spec = importlib.util.spec_from_file_location('audit', ROOT/'research/audit-general-development-v3-linux-v1.py')
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
suite = json.loads((F/'suite.json').read_text())
collection = json.loads((F/'collection.json').read_text())
terminal = json.loads((F/'terminal.json').read_text())
assert collection['suite_sha256'] == terminal['suite_sha256'] == sha(F/'suite.json')
assert terminal['exit_code'] == 0 and terminal['completed'] == [b['name'] for b in suite['blocks']]
methods = suite['methods']
candidate = 'native-reduced'
blocks = []
all_rows = {}
all_accepted = {}
issues = []
rejected = []
metadata = None

def stats(values):
    values = [v for v in values if type(v) in (int, float) and math.isfinite(v) and v >= 0]
    return dict(observations=len(values), median=statistics.median(values), minimum=min(values), maximum=max(values)) if values else dict(observations=0, median=None, minimum=None, maximum=None)

for block in suite['blocks']:
    name = block['name']
    folder = F/name
    assert sha(folder/'plan.json') == block['plan_sha256']
    plan = json.loads((folder/'plan.json').read_text())
    audit = json.loads((folder/'audit.json').read_text())
    raw = ROOT/plan['output']/'runs.jsonl'
    assert sha(raw) == collection['files_sha256'][str(raw.relative_to(ROOT))] == audit['artifact_sha256'][str(raw.relative_to(ROOT))]
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    assert rows == audit['full_rows'] and len(rows) == 704 and not audit['invalid_rows']
    cases = {c['query']: c for c in audit['classification']['cases']}
    current_metadata = {q: {k: c[k] for k in ['family', 'representative', 'kind']} for q, c in cases.items()}
    if metadata is None: metadata = current_metadata
    assert current_metadata == metadata
    representatives = {q for q, c in cases.items() if c['representative'] == q}
    assert len(representatives) == 175 and len(cases) == 176
    indexed = {(r['query'], r['method']): r for r in rows}
    assert len(indexed) == 704
    accepted = {m: {q for q, c in cases.items() if m in c['definitive_methods']} for m in methods}
    all_rows[name], all_accepted[name] = indexed, accepted
    for row in rows:
        definitive = row['verdict'] in ['reachable', 'unreachable'] and row.get('property_truth') is not None
        if definitive and row['query'] not in accepted[row['method']]:
            log = ROOT/plan['output']/(row['query']+'.'+row['method']+'.0.log')
            rejected.append(dict(block=name, query=row['query'], method=row['method'], row=row,
                failure_flags=sorted(failure_flags(row)), log=str(log.relative_to(ROOT)), log_sha256=sha(log)))
    if audit['status'] != 'passed': issues.append(dict(block=name, audit_issues=audit['audit_issues']))
    views = {}
    for label, selected in [('representatives', representatives), ('all_properties', set(cases))]:
        solved = {m: accepted[m] & selected for m in methods}
        views[label] = dict(denominator=len(selected), methods={m: dict(
            accepted_solved=len(solved[m]),
            par2_mean_seconds=statistics.mean(indexed[q, m]['wall_seconds'] if q in accepted[m] else 2*block['seconds'] for q in selected),
            failure_flags=dict(Counter(flag for q in selected for flag in failure_flags(indexed[q, m])))) for m in methods},
            pairs={m: dict(gains=sorted(solved[candidate]-solved[m]), losses=sorted(solved[m]-solved[candidate])) for m in methods if m != candidate})
    blocks.append(dict(name=name, seconds=block['seconds'], audit_status=audit['status'], audit_issues=audit['audit_issues'],
        warnings=len(audit['warnings']), views=views))

assert issues == [dict(block='b2-30s', audit_issues=['Classification reports conflicts or invalid definitive answers'])]
assert len(rejected) == 1 and (rejected[0]['block'], rejected[0]['query'], rejected[0]['method']) == ('b2-30s', 'RefineWMG-PT-100101__RC09', 'smpt-mcc-portable')
assert rejected[0]['failure_flags'] == ['error']
queries = set(metadata)
representatives = {q for q in queries if metadata[q]['representative'] == q}
for q in queries:
    truths = {all_rows[b['name']][q, m]['property_truth'] for b in suite['blocks'] for m in methods if q in all_accepted[b['name']][m]}
    assert len(truths) <= 1
budgets = {}
for seconds in [5, 30]:
    selected = [b for b in blocks if b['seconds'] == seconds]
    names = [b['name'] for b in selected]
    stable = {m: set.intersection(*(all_accepted[n][m] for n in names)) & representatives for m in methods}
    ever = {m: set.union(*(all_accepted[n][m] for n in names)) & representatives for m in methods}
    unresolved = representatives-set.union(*ever.values())
    per_query = {}
    counters = {}
    timings = {}
    pairs = {}
    for q in sorted(queries):
        per_query[q] = {}
        for m in methods:
            rows = [all_rows[n][q, m] for n in names]
            per_query[q][m] = dict(solved_frequency=sum(q in all_accepted[n][m] for n in names),
                observed_wall_seconds=stats([r['wall_seconds'] for r in rows]),
                accepted_wall_seconds=stats([all_rows[n][q, m]['wall_seconds'] for n in names if q in all_accepted[n][m]]),
                peak_memory_bytes=stats([r['resources'].get('peak_memory_bytes') for r in rows]),
                validation_wall_seconds=stats([(r.get('validation') or {}).get('wall_seconds') for r in rows]),
                counters={event: dict(statuses=[auditor.perf_status(r['resources'], event) for r in rows],
                    full_coverage_values=stats([(r['resources'].get('perf_counters', {}).get(event) or {}).get('value') for r in rows if auditor.perf_status(r['resources'], event) == 'full-coverage']),
                    multiplexed_values=stats([(r['resources'].get('perf_counters', {}).get(event) or {}).get('value') for r in rows if auditor.perf_status(r['resources'], event) == 'multiplexed']))
                    for event in ['instructions:u', 'cycles:u', 'task-clock']})
    for m in methods:
        counters[m] = {event: dict(Counter(per_query[q][m]['counters'][event]['statuses'][i] for q in queries for i in range(3))) for event in ['instructions:u', 'cycles:u', 'task-clock']}
        if m == candidate: continue
        common = stable[m] & stable[candidate]
        ratios = [per_query[q][m]['accepted_wall_seconds']['median']/per_query[q][candidate]['accepted_wall_seconds']['median'] for q in common]
        timings[m] = dict(queries=sorted(common), geometric_mean_baseline_over_candidate=math.exp(statistics.mean(math.log(r) for r in ratios)) if ratios else None)
        pairs[m] = dict(gains_in_all_blocks=sorted(set.intersection(*(set(b['views']['representatives']['pairs'][m]['gains']) for b in selected))),
            losses_in_all_blocks=sorted(set.intersection(*(set(b['views']['representatives']['pairs'][m]['losses']) for b in selected))))
    budgets[str(seconds)] = dict(blocks=names, stable={m: sorted(s) for m, s in stable.items()}, any_repeat={m: sorted(s) for m, s in ever.items()},
        methods={m: dict(par2_mean_seconds=statistics.mean(b['views']['representatives']['methods'][m]['par2_mean_seconds'] for b in selected),
            solved_frequency=dict(Counter(per_query[q][m]['solved_frequency'] for q in representatives))) for m in methods},
        persistent_pairs=pairs, common_solved_timings=timings, counters=counters, per_query=per_query,
        never_solved_by_any_method=sorted(unresolved), unresolved_by_family=dict(sorted(Counter(metadata[q]['family'] for q in unresolved).items())))

report = dict(status='diagnostic-registered-summary-blocked', scope='Development cohort; conservative descriptive analysis following the existing auditor acceptance classification. One failed block prevents the registered complete-audited summary. No raw results, plans, frozen scripts, or failed audits were changed.',
    suite_sha256=sha(F/'suite.json'), source_sha256=sha(Path(__file__)), audit_issues=issues, rejected_definitive_rows=rejected,
    metadata=metadata, blocks=blocks, budgets=budgets,
    evidence={b['name']: {n: sha(F/b['name']/n) for n in ['plan.json', 'audit.json', 'execution.json', 'terminal.json', 'capability.json']} for b in suite['blocks']})
(F/'diagnostic-summary.json').write_text(json.dumps(report, indent=2)+'\n')
lines = ['# Repeated comparison: conservative diagnostic', '',
    'The six registered blocks completed with 4,224 rows. Five artifact audits pass; `b2-30s` fails. The frozen summarizer refuses the suite, so no registered complete-audited summary is available.', '',
    'SMPT reports FALSE for `RefineWMG-PT-100101__RC09` in `b2-30s`, with exit 0 and `subprocess_error=true`. Its log contains `BrokenPipeError` before the formula output. The existing auditor excludes this answer. Native checked answers and VerifyPN agree FALSE, but that agreement does not override the registered failure rule.', '',
    'These diagnostic tables use the existing auditor accepted-solved classification, retaining the rejected answer as failure and charging it the registered PAR-2 penalty. They do not waive the failed audit. All primary counts use 175 distinct ordered-branch representatives; the JSON also retains all 176 original properties.', '']
for seconds in ['5', '30']:
    d = budgets[seconds]
    selected = [b for b in blocks if b['name'] in d['blocks']]
    lines += [f'## {seconds}-second budget', '',
        '| Method | Solved by block /175 | Solved in all three /175 | Any repeat /175 | Mean PAR-2 seconds |',
        '|---|---|---:|---:|---:|']
    for m in methods:
        counts = ', '.join(str(b['views']['representatives']['methods'][m]['accepted_solved']) for b in selected)
        lines.append(f"| {m} | {counts} | {len(d['stable'][m])} | {len(d['any_repeat'][m])} | {d['methods'][m]['par2_mean_seconds']:.6f} |")
    lines += ['', 'Block order: '+', '.join(d['blocks'])+'.', '',
        '| Baseline | Candidate gains/losses by block | Gains/losses present in every block |', '|---|---|---|']
    for m, pair in d['persistent_pairs'].items():
        counts = ', '.join(f"{len(b['views']['representatives']['pairs'][m]['gains'])}/{len(b['views']['representatives']['pairs'][m]['losses'])}" for b in selected)
        lines.append(f"| {m} | {counts} | {len(pair['gains_in_all_blocks'])}/{len(pair['losses_in_all_blocks'])} |")
    lines += ['', f"Never solved by any method in any repeat: {len(d['never_solved_by_any_method'])} representatives ("+', '.join(f'{f}: {n}' for f, n in d['unresolved_by_family'].items())+').', '']
lines += ['## Interpretation and limits', '',
    'The candidate has higher coverage than VerifyPN at both budgets. Its five-second solved set contains VerifyPN’s solved set in every block. At thirty seconds the methods complement each other: the candidate gains 12 representatives and loses 8 in every block. All 8 losses are DNAwalker-PT-09ringLR properties. A five-second superset claim therefore does not extend to thirty seconds.', '',
    'At thirty seconds the 24 representatives unresolved by every method comprise 5 DNAwalker-PT-18lozangeBlock properties and 19 RERS17pb114 properties. Unresolved describes these budgets and configurations; it does not prove hardness.', '',
    'Native answers were independently checked during the original runs; the artifact audit verifies saved validation evidence without rerunning proofs. External verdicts remain tool-reported. The cohort informed development, so these results do not establish held-out generalization. Three repeats describe repeatability, not precise population-level uncertainty. CPU affinity is not exclusive host isolation.', '',
    'PAR-2 charges accepted answers their solver wall time and other outcomes twice the invocation budget. Native validation time is separate. Missing counters are not zero; availability below includes unsuccessful runs and retains all 176 properties × three repeats per method.', '',
    '| Budget | Method | Counter | Coverage counts /528 |', '|---:|---|---|---|']
for seconds, d in budgets.items():
    for m, counts in d['counters'].items():
        for event, statuses in counts.items():
            lines.append(f"| {seconds} | {m} | {event} | "+', '.join(f'{status}: {count}' for status, count in sorted(statuses.items()))+' |')
lines += ['', 'Exact paired queries, solved frequencies, accepted and observed timing ranges, separate validation time, peak memory, and counter coverage are retained in `diagnostic-summary.json`. `summary.log` preserves the registered summarizer refusal. `b2-30s/audit.json` preserves the failed audit; raw results and all frozen inputs remain unchanged.', '',
    'Transfer used a read-only remote tar stream at nice 19, idle I/O priority, CPU 9 affinity, and 2 MiB/s; compression and every artifact audit ran locally. No benchmark or build was started.', '',
    'Suite SHA-256: `'+sha(F/'suite.json')+'`.', '']
(F/'diagnostic-report.md').write_text('\n'.join(lines))
print(json.dumps(dict(status=report['status'], blocks=len(blocks), rows=4224, rejected_definitive_rows=len(rejected))))
