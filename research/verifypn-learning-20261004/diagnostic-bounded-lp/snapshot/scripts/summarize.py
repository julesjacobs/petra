#!/usr/bin/env python3
import argparse, collections, csv, json, math, pathlib, statistics
ROOT = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('directory', nargs='?', default='results/comparison')
a = p.parse_args()
directory = ROOT/a.directory
runs = [json.loads(l) for l in (directory/'runs.jsonl').read_text().splitlines()]
groups = collections.defaultdict(list)
for r in runs: groups[r['query'],r['method']].append(r)
rows = []
for query in sorted({r['query'] for r in runs}):
    problem = json.loads((directory/(query+'.json')).read_text())
    constant_false = any(not any(c['coefficients']) and (c['bound'] != 0 if c['equality'] else c['bound'] > 0) for c in problem['target'])
    row = dict(query=query,constant_false=constant_false,places=len(problem['places']),transitions=len(problem['transitions']))
    for method in sorted({r['method'] for r in runs}):
        rs = groups.get((query,method),[])
        verdicts = {r['verdict'] for r in rs}
        row[method+'_verdict'] = next(iter(verdicts)) if len(verdicts)==1 else 'unstable' if rs else 'missing'
        row[method+'_wall_seconds'] = statistics.median(r['wall_seconds'] for r in rs) if rs else ''
        row[method+'_solver_seconds'] = statistics.median(r.get('solve_seconds',r.get('reported_seconds',r['wall_seconds'])) for r in rs) if rs else ''
        row[method+'_repeats'] = len(rs)
    rows.append(row)
with (directory/'summary.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
methods = sorted({r['method'] for r in runs})
environment = json.loads((directory/'environment.json').read_text())
lines = ['# Backend algorithm comparison','',f'{len(rows)} exported queries; {environment["seconds"]}-second budget; {environment["repeat"]} repetition(s), median cold-process wall times.','', '| Method | Reachable | Unreachable | Unknown | Error/unstable |','|---|---:|---:|---:|---:|']
for method in methods:
    counts=collections.Counter(r[method+'_verdict'] for r in rows)
    lines.append(f"| {method} | {counts['reachable']} | {counts['unreachable']} | {counts['unknown']} | {sum(v for k,v in counts.items() if k not in ('reachable','unreachable','unknown'))} |")
all_conflicts = [r['query'] for r in rows if len({r[m+'_verdict'] for m in methods} & {'reachable','unreachable'}) > 1]
lines += ['', f'Definitive verdict disagreements across all methods: {len(all_conflicts)}.']
if all_conflicts: lines += [', '.join(all_conflicts)]
if {'portfolio','smpt'} <= set(methods):
    conflicts = [r['query'] for r in rows if r['portfolio_verdict'] in ('reachable','unreachable') and r['smpt_verdict'] in ('reachable','unreachable') and r['portfolio_verdict'] != r['smpt_verdict']]
    lines += ['',f'Definitive verdict disagreements: {len(conflicts)}.']
    for name, subset in [('All queries',rows),('Excluding syntactically false targets',[r for r in rows if not r['constant_false']])]:
        both=[r for r in subset if r['portfolio_verdict'] in ('reachable','unreachable') and r['portfolio_verdict']==r['smpt_verdict']]
        ratios=[r['smpt_wall_seconds']/r['portfolio_wall_seconds'] for r in both]
        if ratios:
            lines += ['',f'{name}: {len(subset)} queries, {len(both)} solved by both. Native median speedup over SMPT on commonly solved queries: {statistics.median(ratios):.2f}x; geometric mean: {math.exp(statistics.mean(map(math.log,ratios))):.2f}x.']
    for method,other in [('portfolio','smpt'),('smpt','portfolio')]:
        exclusive=[r['query'] for r in rows if r[method+'_verdict'] in ('reachable','unreachable') and r[other+'_verdict']=='unknown']
        lines += ['',f"Solved only by {method}: {', '.join(exclusive) or 'none'}."]
if 'portfolio-next' in methods:
    for baseline in ['portfolio', 'smpt']:
        if baseline not in methods: continue
        common = [r for r in rows if r['portfolio-next_verdict'] in ('reachable','unreachable') and r['portfolio-next_verdict'] == r[baseline+'_verdict']]
        ratios = [r[baseline+'_wall_seconds']/r['portfolio-next_wall_seconds'] for r in common]
        extra = [r['query'] for r in rows if r['portfolio-next_verdict'] in ('reachable','unreachable') and r[baseline+'_verdict']=='unknown']
        lost = [r['query'] for r in rows if r[baseline+'_verdict'] in ('reachable','unreachable') and r['portfolio-next_verdict']=='unknown']
        if ratios: lines += ['', f'portfolio-next versus {baseline}: {len(common)} commonly solved; median wall-time speedup {statistics.median(ratios):.2f}x; geometric mean {math.exp(statistics.mean(map(math.log,ratios))):.2f}x.']
        lines += [f"Additional solves: {', '.join(extra) or 'none'}. Lost solves: {', '.join(lost) or 'none'}."]
if 'kosaraju' in methods or any(r.get('engine') == 'kosaraju' for r in runs):
    lines += ['', 'Native kosaraju implements complete generalized-VASS decomposition. This run imposes resource budgets, so unresolved cases return unknown. Negative Kosaraju results do not yet export independently checkable decomposition proofs.']
if 'cegar' in methods or 'portfolio-cegar' in methods:
    lines += ['', 'CEGAR uses explicit finite threshold abstraction and counterexample-driven threshold refinement. Positive traces and negative threshold-closure certificates are independently checked in Python. This prototype has no decision-diagram representation, residue predicates or relational predicate learning. portfolio-cegar replaces the default acceleration stage with CEGAR while preserving the earlier arithmetic, structural and BFS stages.']
if 'kreach' in methods:
    lines += ['', 'KReach is an unverified external adapted build. Direct read-arc and multi-state smoke tests failed; this run uses the larger single-state pure-VAS encoding. Its reported verdicts are not independently certified.']
lines += ['', 'Other compiler workloads were active on the host; these wall timings are exploratory rather than isolated-machine measurements.', '', 'These are backend-only measurements, including process startup and input parsing. SMPT uses the artifact configuration (STATE-EQUATION + BMC) and exports proofs. Native search replays witnesses; arithmetic and structural refutations carry Farkas, integer-cut, marked-trap or empty-siphon certificates. An independent Python checker verifies those artifacts outside the timed backend run. Finite-state exhaustion does not export a certificate; the Python checker independently reconstructs finite closure up to 200,000 states. KReach uses a pure-VASS encoding of the target reduction, with conversion outside its timed process; its verdicts have no exported certificate.', '', 'The collection attempted all 47 source benchmarks with a 20-second SMPT limit and 40-second frontend limit. It preserves queries emitted before a counterexample, timeout, or completion. It is not an exhaustive export of every disjunct, and these results do not establish an end-to-end serializability speedup.', '', 'Each method receives the same solver time limit; a portfolio shares that limit among its stages. klm-schemes is bounded repeated-word search, not a complete KLMST implementation. The portfolio-old schedule uses the current improved rational engine; results/comparison preserves the original implementation measurements.']
(directory/'REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
