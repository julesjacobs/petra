"""Aggregate only complete audited blocks under the registered analysis rules."""
import hashlib
import importlib.util
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'research/repeated-comparison-linux-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def solved(row):
    return row.get('property_truth') is not None and row.get('verdict') in ('reachable','unreachable')

def finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0

def stats(values):
    values=[x for x in values if finite(x)]
    return dict(observations=len(values),median=statistics.median(values),minimum=min(values),maximum=max(values)) if values else dict(observations=0,median=None,minimum=None,maximum=None)

def par2(row,budget):
    if not solved(row):return 2*budget
    value=row['wall_seconds']
    assert finite(value)
    return value

def markdown_report(report):
    assert report['status']=='complete-audited-repeated-comparison'
    lines=['# Repeated original-input development comparison','',report['scope'],'',
           'Primary results use 175 distinct ordered-branch representatives. The secondary view retains all 176 original properties. '
           'Each budget has three separately ordered blocks. PAR-2 charges accepted definitive answers their wall time and every other outcome twice the budget. '
           'An all-three intersection or any-repeat union is descriptive; neither is a separately measured portfolio.','']
    methods=list(report['budgets']['5']['methods'])
    for seconds in ['5','30']:
        data=report['budgets'][seconds]
        blocks=[b for b in report['blocks'] if b['name'] in data['blocks']]
        assert len(blocks)==3
        lines += [f'## {seconds}-second budget','',
                  '| Method | Solved in block order /175 | All three /175 | Any repeat /175 | PAR-2 seconds /175 | Solved in block order /176 | PAR-2 seconds /176 |',
                  '|---|---|---:|---:|---:|---|---:|']
        for method in methods:
            counts=lambda view:', '.join(str(b['views'][view]['methods'][method]['solved']) for b in blocks)
            metrics=data['methods'][method]
            lines.append(f"| {method} | {counts('representatives')} | {len(data['representative_solved_intersection'][method])} | "
                         f"{len(data['representative_solved_union'][method])} | {metrics['representative_par2_mean_seconds']:.6f} | "
                         f"{counts('all_properties')} | {metrics['all_property_par2_mean_seconds']:.6f} |")
        lines += ['', 'Block order: '+', '.join(data['blocks'])+'.','',
                  '### Paired coverage','',
                  'Gains and losses compare the native-reduced candidate with each baseline in the same block, using distinct representatives.','',
                  '| Block | Baseline | Candidate gains | Candidate losses |','|---|---|---:|---:|']
        for block in blocks:
            for method,pair in block['views']['representatives']['pairs'].items():
                lines.append(f"| {block['name']} | {method} | {len(pair['gains'])} | {len(pair['losses'])} |")
        lines += ['', '### Common-solved timings','',
                  'These ratios include only queries solved by both methods in all three repeats. '
                  'They are geometric means of baseline/candidate ratios of per-query median wall times. '
                  'A value above 1 favors the candidate on this selected subset; it is not a full-cohort speed claim.','',
                  '| Baseline | Common-solved queries | Baseline/candidate ratio |','|---|---:|---:|']
        for method,timing in data['common_solved_timings'].items():
            value=timing['geometric_mean_baseline_over_candidate']
            ratio='unavailable' if value is None else f'{value:.6f}'
            lines.append(f"| {method} | {timing['common_solved_in_all_three_blocks']} | {ratio} |")
        lines += ['', '### Counter availability','',
                  'Counts below retain all 176 properties × three repeats per method, including unsuccessful runs. '
                  'Full and multiplexed measurements remain separate. Missing measurements are not zero.','',
                  '| Method | Counter | Status counts |','|---|---|---|']
        for method in methods:
            for counter in ['instructions:u','cycles:u','task-clock']:
                statuses=Counter(status for query in data['per_query'].values()
                                 for status in query[method]['counters'][counter]['statuses'])
                counts=', '.join(f'{status}: {count}' for status,count in sorted(statuses.items()))
                lines.append(f'| {method} | {counter} | {counts} |')
        lines += ['', '### Failures and audit warnings','',
                  'Failure flags may overlap. Counts retain all original properties in each block.','']
        for block in blocks:
            lines.append(f"- {block['name']}: {len(block['warnings'])} audit warnings.")
            for warning in block['warnings']:
                lines.append('  - '+json.dumps(warning,ensure_ascii=False))
            for method in methods:
                flags=block['views']['all_properties']['methods'][method]['failure_flags']
                lines.append(f"  - {method}: "+(', '.join(f'{key}={value}' for key,value in sorted(flags.items())) or 'no recorded failure flags')+'.')
        lines.append('')
    lines += ['## Query-level evidence','',
              'See summary.json for exact paired gain/loss query names, solved frequencies, all-three intersections, any-repeat unions, '
              'per-query wall-time medians and ranges, peak memory, separate validation time, counters and their coverage. '
              'Compare the two budgets before interpreting a coverage lead. Three repeats assess repeatability on this development cohort; '
              'they do not establish generalization or precise population-level uncertainty.','',
              f"Suite SHA-256: `{report['suite_sha256']}`.",
              f"Summary source SHA-256: `{report['source_sha256']}`.",'']
    return '\n'.join(lines)

def main():
    suite=json.loads((F/'suite.json').read_text())
    terminal=json.loads((F/'terminal.json').read_text())
    assert terminal['suite_sha256']==sha(F/'suite.json') and terminal['exit_code']==0
    assert terminal['completed']==[b['name'] for b in suite['blocks']]
    collection=json.loads((F/'collection.json').read_text())
    assert collection['suite_sha256']==sha(F/'suite.json')
    spec=importlib.util.spec_from_file_location('artifact_audit',ROOT/'research/audit-general-development-v3-linux-v1.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    from analyze_application_expansion import failure_flags
    methods=suite['methods'];candidate='native-reduced'
    blocks=[];evidence={};truths={};normalized_verdicts={};representatives=None;queries=None;cases={}
    for b in suite['blocks']:
        folder=F/b['name'];assert sha(folder/'plan.json')==b['plan_sha256']
        plan=json.loads((folder/'plan.json').read_text())
        audit=json.loads((folder/'audit.json').read_text())
        assert audit['status']=='passed' and not audit['audit_issues'] and not audit['invalid_rows']
        raw=ROOT/plan['output']/'runs.jsonl'
        assert collection['files_sha256'][str(raw.relative_to(ROOT))]==sha(raw)
        assert audit['artifact_sha256'][str(raw.relative_to(ROOT))]==sha(raw)
        assert audit['artifact_sha256'][str((folder/'plan.json').relative_to(ROOT))]==sha(folder/'plan.json')
        rows=[json.loads(x) for x in raw.read_text().splitlines()]
        assert rows==audit['full_rows'] and len(rows)==704
        groups=audit['classification']['cases']
        current_queries={c['query'] for c in groups}
        current_reps={c['representative'] for c in groups}
        representative_for={c['query']:c['representative'] for c in groups}
        if representatives is None:representatives=current_reps;queries=current_queries
        assert current_reps==representatives and current_queries==queries
        assert len(queries)==176 and len(representatives)==175
        indexed={(r['query'],r['method']):r for r in rows}
        assert len(indexed)==704 and set(indexed)=={(q,m) for q in queries for m in methods}
        for r in rows:
            if solved(r):
                truths.setdefault(r['query'],set()).add(r['property_truth'])
                normalized_verdicts.setdefault(representative_for[r['query']],set()).add(r['verdict'])
        view={}
        for label,selected in [('representatives',representatives),('all_properties',queries)]:
            solved_sets={m:{q for q in selected if solved(indexed[q,m])} for m in methods}
            view[label]=dict(denominator=len(selected),methods={m:dict(
                solved=len(solved_sets[m]),verdicts=dict(Counter(indexed[q,m]['verdict'] for q in selected)),
                par2_mean_seconds=statistics.mean(par2(indexed[q,m],b['seconds']) for q in selected),
                failure_flags=dict(Counter(flag for q in selected for flag in failure_flags(indexed[q,m])))) for m in methods},
                pairs={m:dict(gains=sorted(solved_sets[candidate]-solved_sets[m]),losses=sorted(solved_sets[m]-solved_sets[candidate])) for m in methods if m!=candidate})
        blocks.append(dict(name=b['name'],seconds=b['seconds'],views=view,warnings=audit['warnings']))
        cases[b['name']]=indexed
        evidence[b['name']]={n:sha(folder/n) for n in ['plan.json','audit.json','execution.json','terminal.json','capability.json']}
    assert all(len(values)==1 for values in truths.values()),'Cross-block answer disagreement'
    assert all(len(values)==1 for values in normalized_verdicts.values()),'Cross-block duplicate disagreement'
    budgets={}
    for budget in [5,30]:
        selected_blocks=[b['name'] for b in suite['blocks'] if b['seconds']==budget]
        assert len(selected_blocks)==3
        per_query={}
        stable={m:set() for m in methods};ever={m:set() for m in methods}
        for query in sorted(queries):
            per_query[query]={}
            for method in methods:
                rows=[cases[b][query,method] for b in selected_blocks]
                count=sum(solved(r) for r in rows)
                if count==3:stable[method].add(query)
                if count:ever[method].add(query)
                counters={}
                for counter in ['instructions:u','cycles:u','task-clock']:
                    statuses=[auditor.perf_status(r['resources'],counter) for r in rows]
                    values=[r['resources']['perf_counters'][counter]['value'] for r,status in zip(rows,statuses) if status in ['full-coverage','multiplexed']]
                    counters[counter]=dict(statuses=statuses,values=stats(values))
                per_query[query][method]=dict(solved_frequency=count,observed_wall_seconds=stats([r['wall_seconds'] for r in rows]),
                    solved_wall_seconds=stats([r['wall_seconds'] for r in rows if solved(r)]),
                    peak_memory_bytes=stats([r['resources'].get('peak_memory_bytes') for r in rows]),
                    validation_wall_seconds=stats([(r.get('validation') or {}).get('wall_seconds') for r in rows]),
                    counters=counters,par2_mean_seconds=statistics.mean(par2(r,budget) for r in rows))
        timings={}
        for method in methods:
            if method==candidate:continue
            common=stable[candidate]&stable[method]&representatives
            ratios=[]
            for query in sorted(common):
                ours=per_query[query][candidate]['solved_wall_seconds']['median']
                theirs=per_query[query][method]['solved_wall_seconds']['median']
                assert ours>0 and theirs>0
                ratios.append(theirs/ours)
            timings[method]=dict(common_solved_in_all_three_blocks=len(common),queries=sorted(common),
                geometric_mean_baseline_over_candidate=math.exp(statistics.mean(math.log(r) for r in ratios)) if ratios else None,
                scope='Conditioned on both methods solving the query in all three blocks; not a full-cohort speed claim')
        budgets[str(budget)]=dict(blocks=selected_blocks,per_query=per_query,
            methods={m:dict(
                representative_par2_mean_seconds=statistics.mean(par2(cases[b][query,m],budget) for b in selected_blocks for query in representatives),
                all_property_par2_mean_seconds=statistics.mean(par2(cases[b][query,m],budget) for b in selected_blocks for query in queries),
                representative_solved_frequency=dict(Counter(per_query[query][m]['solved_frequency'] for query in representatives))) for m in methods},
            representative_solved_intersection={m:sorted(stable[m]&representatives) for m in methods},
            representative_solved_union={m:sorted(ever[m]&representatives) for m in methods},
            common_solved_timings=timings)
    report=dict(status='complete-audited-repeated-comparison',suite_sha256=sha(F/'suite.json'),
                evidence=evidence,blocks=blocks,budgets=budgets,source_sha256=sha(Path(__file__)),
                scope='Development evidence; native answers independently checked during runs, external verdicts tool-reported. Missing counters omitted with explicit coverage; no imputation. No held-out or novelty claim.')
    (F/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (F/'report.md').write_text(markdown_report(report))
    print(json.dumps(dict(status=report['status'],blocks=len(blocks),rows=4224)))

if __name__=='__main__':main()
