"""Audit saved direct-method diagnostic evidence without solver execution."""
from collections import Counter, defaultdict
import hashlib,json,math,random,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];F=Path(__file__).resolve().parent;OUT=ROOT/'results/coverage-final-screen-20261004'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((F/'diagnostic-plan.json').read_text());terminal=json.loads((F/'diagnostic-terminal.json').read_text());execution=json.loads((F/'diagnostic-execution.json').read_text())
assert terminal['plan_sha256']==execution['plan_sha256']==sha(F/'diagnostic-plan.json')
assert terminal['completed'] is True and terminal['rows']==31 and terminal['issues']==[]
for path,h in plan['pins'].items():assert sha(ROOT/path)==h,path
assert {str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file()}==set(terminal['artifacts'])
for path,h in terminal['artifacts'].items():assert sha(ROOT/path)==h,path
frozen_script=F/'diagnostic-snapshot/research/coverage-final-screen-20261004/diagnostic.py'
assert sha(frozen_script)==sha(F/'diagnostic.py')
old_rows=[json.loads(l) for l in (ROOT/'results/grouped-excess-20261004/full/runs.jsonl').read_text().splitlines()]
selected=[dict(corpus=r['corpus'],query=r['query']) for r in old_rows if r['method']=='candidate' and r['verdict']=='unknown']
assert len(selected)==31
random.Random(2026100403).shuffle(selected)
schedule=[]
for i,q in enumerate(selected):
 methods=['portfolio-excess']
 methods=methods
 schedule.extend(dict(q,method=m) for m in methods)
assert schedule==plan['schedule']
rows=[json.loads(l) for l in (OUT/'runs.jsonl').read_text().splitlines()]
assert [{k:r[k] for k in ('corpus','query','method')} for r in rows]==schedule
sys.path.insert(0,str(F/'diagnostic-snapshot/scripts'))
from analyze_application_expansion import failure_flags,native_checked
queries={c:{q['name']:q for q in json.loads((ROOT/p/'manifest.json').read_text())['queries']} for c,p in plan['corpora'].items()}
solved=defaultdict(set);answers=defaultdict(set);raw_status=defaultdict(Counter);overhead=defaultdict(list)
checks=0;native_witnesses=0
for r in rows:
 q=queries[r['corpus']][r['query']];corpus=ROOT/plan['corpora'][r['corpus']]
 assert q['status']=='imported' and r['family']==q['family']
 assert r['command']==[str(ROOT/plan['binary']),'--pnml',str(corpus/q['pnml']),'--xml',str(corpus/q['xml']),'--property-id',q['property_id'],'--method',r['method'],'--seconds','5.0','--max-states','2000000']+(['--buffer-agglomeration'] if r['method']=='portfolio-excess' else [])
 assert r['input_mode']=='rust-original-v1'
 assert type(r['wall_seconds']) in (int,float) and math.isfinite(r['wall_seconds']) and r['wall_seconds']>=0
 assert r['resources']['memory_limit_bytes']==2**31
 log=OUT/r['corpus']/f"{r['query']}.{r['method']}.0.rust-original.json"
 try:raw=json.loads(log.read_text());raw_status[r['method']]['complete_json']+=1
 except ValueError:raw=None;raw_status[r['method']]['incomplete_or_empty_json']+=1
 if raw:
  if r['outer_timeout'] and raw.get('verdict') in ('reachable','unreachable'):
   raw_status[r['method']]['definitive_json_rejected_as_late']+=1
  if all(type(raw.get(k)) in (int,float) and math.isfinite(raw[k]) for k in ('parse_seconds','solve_seconds')):
   overhead[r['method']].append(r['wall_seconds']-raw['parse_seconds']-raw['solve_seconds'])
 if 'validation' in r:
  v=r['validation'];assert type(v['wall_seconds']) in (int,float) and math.isfinite(v['wall_seconds']) and v['wall_seconds']>=0
  assert v['seconds_limit']==60 and v['memory_limit_bytes']==2**31 and v['response_limit_bytes']==64*1024**2 and v['dag_check_max_work']==200000000 and v['included_in_solver_timing'] is False
  request=json.loads(Path(str(log)+'.validation-request.json').read_text())
  assert request==dict(query=q,corpus=str(corpus),artifacts=str(OUT/r['corpus']),log=str(log),mode='rust-original-v1',outer_timeout=False,exit_code=r['exit_code'],memory_bytes=2**31,response_bytes=64*1024**2,dag_check_max_work=200000000)
  response_path=Path(str(log)+'.validation-response.json')
  if v['exit_code']==0 and not v['outer_timeout']:
   response=json.loads(response_path.read_text())
   assert all(r[k]==value for k,value in response.items()),r['query']
  checks+=1
 if r['verdict'] in ('reachable','unreachable'):
  assert not failure_flags(r) and native_checked(r,q)
  assert r['wall_seconds']<=5 and r['outer_timeout'] is False and r['exit_code']==0
  expected_truth=(r['verdict']=='reachable')==(q['kind']=='EF')
  assert r['property_truth'] is expected_truth
  assert raw['verdict']==r['verdict'] and raw['property_truth'] is expected_truth and raw['deadline_exceeded'] is False
  assert raw['property_id']==q['property_id'] and raw['property_kind']==q['kind'] and raw['branch_count']==len(q['branches'])
  solved[r['method']].add((r['corpus'],r['query']));answers[r['corpus'],r['query']].add(expected_truth)
  native_witnesses+=1
 else:assert r['property_truth'] is None
assert all(len(v)==1 for v in answers.values())
methods=['portfolio-excess'];union=set.union(*(solved[m] for m in methods));intersection=set.intersection(*(solved[m] for m in methods))
all_queries={(q['corpus'],q['query']) for q in selected}
summary={}
for m in methods:
 rs=[r for r in rows if r['method']==m]
 summary[m]=dict(solved=len(solved[m]),queries=sorted(solved[m]),verdicts=dict(Counter(r['verdict'] for r in rs)),failure_flags=dict(Counter(f for r in rs for f in failure_flags(r))),
  solver_wall_total=sum(r['wall_seconds'] for r in rs),validation_wall_total=sum(r.get('validation',{}).get('wall_seconds',0) for r in rs),
  raw_output=dict(raw_status[m]),observed_wall_minus_reported_parse_solve_median=statistics.median(overhead[m]) if overhead[m] else None)
report=dict(status='passed',plan_sha256=sha(F/'diagnostic-plan.json'),terminal_sha256=sha(F/'diagnostic-terminal.json'),auditor_sha256=sha(Path(__file__)),
 pinned_files=len(plan['pins']),result_artifacts=len(terminal['artifacts']),rows=31,properties=31,methods=summary,union=sorted(union),intersection=sorted(intersection),
 method_only={m:sorted(solved[m]-set().union(*(solved[o] for o in methods if o!=m))) for m in methods},unresolved=sorted(all_queries-union),
 validations_recorded=checks,accepted_witnesses=native_witnesses,scope='Read-only artifact/provenance/acceptance audit. No solver or certificate replay. Saved bounded independent original-input proof/witness checks verified against request/response evidence. One selected diagnostic, not an overall or repeated comparison.')
(F/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Integrated portfolio survivor screen','',f"Artifact audit passes: 31 rows, all 31 survivors, exact frozen binary/source/input pins, terminal hashes and bounded independent original-input validation. All {native_witnesses} definitive answers passed their saved independent checks.",'',
 '| Method | Solved /31 | Exclusive among these methods | Unknown |','|---|---:|---:|---:|']
for m in methods:lines.append(f"| {m} | {len(solved[m])} | {len(report['method_only'][m])} | {summary[m]['verdicts'].get('unknown',0)} |")
lines+=['',f"The integrated portfolio solves {len(union)}/31; {len(all_queries-union)} remain unresolved. Each property uses one shared five-second invocation. This selected survivor screen does not establish whole-cohort coverage.",'',
 'Each invocation used the same frozen binary and original PNML/XML with a strict five-second whole-property deadline. Only `portfolio-excess` used buffer agglomeration. Validation ran separately with a 60-second limit and sampled 2 GiB. All 31 original slots and all unsuccessful outcomes remain in the denominator.','',
 '## Checked successes and costs','',
 '| Query | Method | Verdict | Solver seconds | Validator seconds | Parse seconds | Solve seconds |','|---|---|---|---:|---:|---:|---:|']
for r in sorted(rows,key=lambda r:(r['query'],r['method'])):
 if r['verdict'] in ('reachable','unreachable'):
  lines.append(f"| {r['query']} | {r['method']} | {r['verdict']} | {r['wall_seconds']:.3f} | {r['validation']['wall_seconds']:.3f} | {r['rust_parse_seconds']:.3f} | {r['rust_solve_seconds']:.3f} |")
lines+=['','## Failures and deadlines','',
 '| Method | Failure flags | Complete JSON /31 | Empty/incomplete JSON | Late definitive JSON |','|---|---|---:|---:|---:|']
for m in methods:
 s=summary[m];lines.append(f"| {m} | "+(', '.join(f'{k}: {v}' for k,v in sorted(s['failure_flags'].items())) or 'none')+f" | {s['raw_output'].get('complete_json',0)} | {s['raw_output'].get('incomplete_or_empty_json',0)} | {s['raw_output'].get('definitive_json_rejected_as_late',0)} |")
lines+=['','Saved-output completeness does not reveal unpublished search progress. Failed or late runs remain unknown. The full query sets and timings are in `audit.json`. This selected diagnostic does not establish overall coverage or stable speed; integrated scheduling must be measured on the complete 368-property cohort.','']
report['accepted_timings']=[{k:r.get(k) for k in ['corpus','query','method','verdict','wall_seconds','rust_parse_seconds','rust_solve_seconds','validation']} for r in rows if r['verdict'] in ('reachable','unreachable')]
(F/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
(F/'RESULTS.md').write_text('\n'.join(lines))
print(json.dumps(dict(status='passed',rows=31,solved={m:len(solved[m]) for m in methods},union=len(union),intersection=len(intersection))))
