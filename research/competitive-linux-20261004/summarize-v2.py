"""Summarize two complete audited comparison blocks without rerunning tools."""
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
import statistics

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
spec = importlib.util.spec_from_file_location('competitive_audit', F/'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
sha, solved, finite = audit.sha, audit.solved, audit.finite
CANDIDATE = 'native-excess'


def geomean(values):
    return math.exp(statistics.mean(map(math.log, values))) if values else None


def validation_time(row):
    value = (row.get('validation') or {}).get('wall_seconds', 0)
    assert finite(value)
    return value


def stats(values):
    values = [v for v in values if finite(v)]
    return dict(observations=len(values), median=statistics.median(values) if values else None,
                minimum=min(values) if values else None, maximum=max(values) if values else None)


def summarize_view(names, methods, cases):
    names = set(names)
    blocks = list(cases)
    solved_sets = {m:[{q for q in names if solved(cases[b][q,m])} for b in blocks] for m in methods}
    stable = {m:set.intersection(*sets) for m,sets in solved_sets.items()}
    ever = {m:set.union(*sets) for m,sets in solved_sets.items()}
    metrics = {}
    for method in methods:
        rows = [cases[b][q,method] for b in blocks for q in sorted(names)]
        solver = sum(r['wall_seconds'] for r in rows)
        validation = sum(validation_time(r) for r in rows)
        metrics[method] = dict(solved_by_repeat=[len(s) for s in solved_sets[method]], stable=len(stable[method]), any_repeat=len(ever[method]),
            stable_queries=sorted(stable[method]), any_repeat_queries=sorted(ever[method]),
            unknown_by_repeat=[len(names)-len(s) for s in solved_sets[method]],
            solver_wall_total_seconds=solver, validation_wall_total_seconds=validation,
            solver_plus_recorded_validation_seconds=solver+validation,
            solver_par2_mean_seconds=statistics.mean(r['wall_seconds'] if solved(r) else 10 for r in rows),
            verdicts_by_repeat=[dict(Counter(cases[b][q,method]['verdict'] for q in names)) for b in blocks],
            failure_flags_by_repeat=[dict(Counter(f for q in names for f in audit.failure_flags(cases[b][q,method]))) for b in blocks],
            admission_failures_by_repeat=[dict(Counter(f for q in names for f in cases[b][q,method].get('admission_failures',[]))) for b in blocks],
            peak_memory_bytes=stats([(r.get('resources') or {}).get('peak_memory_bytes') for r in rows]),
            counters={event:dict(Counter(audit.prior.perf_status(r.get('resources') or {},event) for r in rows))
                      for event in ['instructions:u','cycles:u','task-clock']})
    pairs = {}
    for method in methods:
        if method == CANDIDATE:
            continue
        gains = [c-o for c,o in zip(solved_sets[CANDIDATE], solved_sets[method])]
        losses = [o-c for c,o in zip(solved_sets[CANDIDATE], solved_sets[method])]
        common = stable[CANDIDATE] & stable[method]
        solver_ratios, total_ratios = [], []
        for q in sorted(common):
            ours = statistics.median(cases[b][q,CANDIDATE]['wall_seconds'] for b in blocks)
            theirs = statistics.median(cases[b][q,method]['wall_seconds'] for b in blocks)
            ours_total = statistics.median(cases[b][q,CANDIDATE]['wall_seconds']+validation_time(cases[b][q,CANDIDATE]) for b in blocks)
            theirs_total = statistics.median(cases[b][q,method]['wall_seconds']+validation_time(cases[b][q,method]) for b in blocks)
            assert min(ours,theirs,ours_total,theirs_total)>0
            solver_ratios.append(theirs/ours)
            total_ratios.append(theirs_total/ours_total)
        pairs[method] = dict(gains_by_repeat=[sorted(x) for x in gains], losses_by_repeat=[sorted(x) for x in losses],
                            stable_gains=sorted(set.intersection(*gains)), stable_losses=sorted(set.intersection(*losses)),
                            common_solved=dict(denominator=len(common), queries=sorted(common),
                                geometric_mean_competitor_over_candidate_solver=geomean(solver_ratios),
                                geometric_mean_competitor_over_candidate_with_recorded_validation=geomean(total_ratios),
                                scope='Both methods solve in both repeats; per-query medians. External answers have no independent checking cost.'))
    jointly_unsolved = names - set.union(*ever.values())
    exclusive = {m:sorted(stable[m] - set.union(*(ever[n] for n in methods if n!=m))) for m in methods}
    return dict(denominator=len(names), methods=metrics, pairs=pairs, never_solved_by_any_method=sorted(jointly_unsolved),
                stable_method_exclusive=exclusive)


def report_text(report):
    lines = ['# Current four-tool Linux comparison — contended pilot','',
             '**Host contention materially limits this pilot.** '+report['host_contention']['caveat'],'',
             '**Provenance amendment:** The frozen audit failed because `vendor/venv/bin/z3` was omitted from its enforced pins. The saved pre-launch capability chain and both block environments record the same executable hash. [The amended audit](audit-v2.json) accepts only this documented omission; the [original failed audit](audit.json) remains unchanged. Matching observations do not establish continuous pin enforcement.','',report['scope'],'',
             'Each method receives one five-second original-property invocation on CPU 8 with enforced 2 GiB process-tree memory. '
             'All 2,944 invocations remain in the record. Native answers are independently checked; external answers are tool-reported.','',
             '| Method | Solved repeat 1 /368 | Solved repeat 2 /368 | Both /368 | Representatives repeat 1 /366 | Representatives repeat 2 /366 |',
             '|---|---:|---:|---:|---:|---:|']
    full = report['views']['pooled']['all_properties']
    reps = report['views']['pooled']['representatives']
    methods = report['methods']
    for m in methods:
        v,r=full['methods'][m],reps['methods'][m]
        lines.append(f"| {m} | {v['solved_by_repeat'][0]} | {v['solved_by_repeat'][1]} | {v['stable']} | {r['solved_by_repeat'][0]} | {r['solved_by_repeat'][1]} |")
    lines += ['', '| Competitor | Candidate gains/losses, repeat 1 | Repeat 2 | Gains/losses in both |', '|---|---:|---:|---:|']
    for m,p in full['pairs'].items():
        count=lambda i:f"{len(p['gains_by_repeat'][i])}/{len(p['losses_by_repeat'][i])}"
        lines.append(f"| {m} | {count(0)} | {count(1)} | {len(p['stable_gains'])}/{len(p['stable_losses'])} |")
    lines += ['', 'Pairs compare the candidate against each competitor in the same block. The summary retains exact queries and the representative view. '
                   'Intersections and unions across repeats describe repeatability; they are not measured portfolios.','',
              '| Cohort | Slots | ' + ' | '.join(methods) + ' |', '|---|---:|'+'---:|'*len(methods)]
    for label in ['existing176','expansion192',*report['families']]:
        v=report['views'][label]['all_properties']
        counts=[' / '.join(map(str,v['methods'][m]['solved_by_repeat'])) for m in methods]
        lines.append(f"| {label} | {v['denominator']} | " + ' | '.join(counts) + ' |')
    lines += ['', 'Entries show repeat 1 / repeat 2 solved counts. All properties and all twelve families remain represented.','',
              '| Method | Solver total | Validation total | Solver + recorded validation | Mean solver PAR-2 |', '|---|---:|---:|---:|---:|']
    for m,v in full['methods'].items():
        lines.append(f"| {m} | {v['solver_wall_total_seconds']:.3f} s | {v['validation_wall_total_seconds']:.3f} s | {v['solver_plus_recorded_validation_seconds']:.3f} s | {v['solver_par2_mean_seconds']:.3f} s |")
    lines += ['', 'Totals cover both repetitions. PAR-2 charges every unsolved invocation ten seconds. '
                   'External totals contain no equivalent independent proof-checking cost.','',
              '| Competitor | Common solved in both repeats | Competitor/candidate solver ratio | Ratio including recorded checking |', '|---|---:|---:|---:|']
    for m,p in full['pairs'].items():
        c=p['common_solved'];fmt=lambda x:'unavailable' if x is None else f'{x:.3f}'
        lines.append(f"| {m} | {c['denominator']} | {fmt(c['geometric_mean_competitor_over_candidate_solver'])} | {fmt(c['geometric_mean_competitor_over_candidate_with_recorded_validation'])} |")
    lines += ['', 'Ratios are geometric means of per-query median ratios, conditioned on both methods solving in both repeats. '
                   'Values above one favor the candidate on that selected subset. Checking remains asymmetric.','',
              '| Method | Failure flags repeat 1 | Failure flags repeat 2 |', '|---|---|---|']
    for m,v in full['methods'].items():
        fmt=lambda flags:', '.join(f'{k}: {n}' for k,n in sorted(flags.items())) or 'none'
        lines.append(f"| {m} | {fmt(v['failure_flags_by_repeat'][0])} | {fmt(v['failure_flags_by_repeat'][1])} |")
    lines += ['', 'Failure flags overlap. Raw reported answers rejected after failure remain available. Unknown is not an unreachability answer.','',
              f"Never solved by any method in either repeat: {len(full['never_solved_by_any_method'])} original properties. Exact queries, per-query variation, admission failures and resource availability are in [summary.json](summary.json).",'',
              'All new expansion arcs have unit weights; the corpus does not establish weighted-arc breadth. Development-family selection and earlier tuning limit generalization. '
              'Reserved evaluation families remain untouched. CPU affinity does not imply exclusive host isolation. '
              'Two repetitions do not establish precise timing uncertainty, novelty or general competitive superiority.','',
              f"Plan SHA-256: `{report['plan_sha256']}`.",f"Candidate binary SHA-256: `{report['candidate_binary_sha256']}`.",
              'ITS runtime used: ' + report['its_runtime']['runtime'] + '; product ' + report['its_runtime']['product_application'] + '. ' + report['its_runtime']['native_source_correspondence'] + ' Qualification attempts and their failures are separate from competitive rows.',
              'ITS qualification retains documented timeout, unsupported-input and auxiliary-error limitations; those outcomes remain unknown in this comparison. Exact competitor/runtime/source identities and commands are in [plan.json](plan.json). '
              'The [protocol](protocol.json), [amended audit](audit-v2.json), [provenance amendment](analysis-amendment-v2.json), [analysis source hashes](analysis-v2-sha256.json), block terminal receipts and raw artifacts preserve all inputs, outcomes and checking evidence.','']
    return '\n'.join(lines)


def main():
    plan = json.loads((F/'plan.json').read_text())
    checked = json.loads((F/'audit-v2.json').read_text())
    assert checked['status']=='passed-with-provenance-amendment' and not checked['issues']
    assert checked['source_sha256']==sha(F/'audit.py')
    for name,digest in checked['artifact_sha256'].items():
        assert sha(ROOT/name)==digest, name
    manifest=json.loads((ROOT/plan['corpus']/'manifest.json').read_text())
    queries={q['name']:q for q in manifest['queries']}
    representatives={g[0] for g in audit.corpus_groups(manifest)}
    cases={}
    for block in plan['blocks']:
        rows=[json.loads(s) for s in (ROOT/block['output']/'runs.jsonl').read_text().splitlines()]
        assert len(rows)==1472
        cases[block['name']]={(r['query'],r['method']):r for r in rows}
        assert len(cases[block['name']])==1472
    families=sorted({q['family'] for q in queries.values()})
    cohorts={'pooled':set(queries)}
    cohorts.update({name:{q for q,v in queries.items() if v['source_corpus']==name} for name in ['existing176','expansion192']})
    cohorts.update({name:{q for q,v in queries.items() if v['family']==name} for name in families})
    views={cohort:{label:summarize_view(selected,plan['methods'],cases)
                   for label,selected in [('all_properties',names),('representatives',names&representatives)]}
           for cohort,names in cohorts.items()}
    per_query={q:{m:dict(solved_frequency=sum(solved(cases[b][q,m]) for b in cases),
                        observed_wall_seconds=[cases[b][q,m]['wall_seconds'] for b in cases],
                        validation_wall_seconds=[validation_time(cases[b][q,m]) for b in cases],
                        verdicts=[cases[b][q,m]['verdict'] for b in cases]) for m in plan['methods']} for q in sorted(queries)}
    result=dict(status='two-complete-repeats-with-provenance-amendment',plan_sha256=sha(F/'plan.json'),audit_sha256=sha(F/'audit-v2.json'),
                summary_source_sha256=sha(Path(__file__)), candidate_binary_sha256=plan['candidate_binary_sha256'],
                rows=2944, methods=plan['methods'],families=families,views=views,per_query=per_query, its_runtime=plan['its_runtime'],
                scope='Contended five-second Linux pilot with two complete development repetitions and a documented provenance amendment. Native results independently checked; external answers tool-reported. No idle-host, held-out or novelty claim.',
                provenance_amendment=checked['amendment'],original_failed_audit_sha256=checked['original_audit_sha256'],
                host_contention=checked['host_contention'],analysis_v2_manifest_sha256=sha(F/'analysis-v2-sha256.json'))
    with (F/'summary.json').open('x') as out:
        json.dump(result,out,indent=2)
        out.write('\n')
    with (F/'REPORT.md').open('x') as out:
        out.write(report_text(result))
    print(json.dumps(dict(status=result['status'],rows=result['rows'],solved={m:v['solved_by_repeat'] for m,v in views['pooled']['all_properties']['methods'].items()})))


if __name__=='__main__':
    main()
