"""Summarize the complete audited original-input Linux screen."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-counts-linux-v1'
a=json.loads((F/'audit.json').read_text());assert a['status']=='passed' and not a['audit_issues']
rows=a['full_rows'];methods=list(a['classification']['full']['definitive_by_method'])
solved={m:{r['query'] for r in rows if r['method']==m and r.get('property_truth') is not None} for m in methods}
report=dict(status='audited-screen',properties=a['properties'],representatives=a['exact_ordered_branch_representatives'],methods={},pairs={},warnings=a['warnings'],native_only=[],competitor_only=[],all_unresolved=a['classification']['selections']['all_unresolved'])
for m in methods:
 selected=[r for r in rows if r['method']==m]
 assert len(selected)==176
 report['methods'][m]=dict(verdicts=dict(Counter(r['verdict'] for r in selected)),solved=len(solved[m]),outer_timeouts=sum(bool(r.get('outer_timeout')) for r in selected))
for m in ['native-frozen','verifypn-default','smpt-mcc-portable','native-walk']:
 report['pairs']['native-counts/'+m]=dict(gains=sorted(solved['native-counts']-solved[m]),losses=sorted(solved[m]-solved['native-counts']))
for case in a['classification']['cases']:
 for label in ['native_only','competitor_only']:
  if case[label]:report[label].append(dict(query=case['query'],methods=case['definitive_methods']))
report['evidence']={name:hashlib.sha256((F/name).read_bytes()).hexdigest() for name in ['plan.json','audit.json','collection.json','execution.json','terminal.json']}
report['scope']='One five-second original-input development screen; native answers independently checked during collection, external answers tool-reported. No stable speed or superiority claim. Unresolved means no answer at this budget, not proved hard.'
(F/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['properties','representatives','methods','pairs','native_only','competitor_only']}))
