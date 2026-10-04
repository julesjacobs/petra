"""Audit all selected bytes, exact duplicates, structural scale and independent imports."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];F=Path(__file__).resolve().parent;C=ROOT/'benchmarks/development-expansion-v4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selection=json.loads((F/'selection.json').read_text());receipt=json.loads((F/'freeze-receipt.json').read_text());manifest=json.loads((C/'manifest.json').read_text())
assert sha(F/'selection.json')==receipt['selection_sha256']==manifest['selection_sha256']==sha(C/'selection.json')
assert sha(F/'freeze-selection.py')==selection['selector_sha256']
assert all(sha(ROOT/p)==h for p,h in selection['input_sha256'].items())
assert len(selection['models'])==12 and selection['expected_properties']==192
assert manifest['collection_complete'] and len(manifest['queries'])==192
reserved=set(selection['reserved_families_excluded'])
assert not {m['family'] for m in selection['models']}&reserved
expected={(m['name'],i) for m in selection['models'] for i in range(16)}
assert Counter((q['instance'],q['property_slot']) for q in manifest['queries'])==Counter({key:1 for key in expected})
assert len({q['name'] for q in manifest['queries']})==192
pins={};original=defaultdict(list);canonical=defaultdict(list);outcomes=json.loads((C/'collection-outcomes.json').read_text())
assert len(outcomes)==12 and all(o['success'] for o in outcomes)
for record in json.loads((C/'archive-checksums.json').read_text())['archives']:
 p=C/'archives'/(record['model']+'.tgz');assert sha(p)==record['sha256'] and p.stat().st_size==record['bytes'];pins[str(p.relative_to(ROOT))]=record['sha256']
provenance=json.loads((C/'collector-provenance.json').read_text())
for name,h in provenance['sources'].items():assert sha(C/'collector-source'/name)==h
assert manifest['collector_sha256']==provenance['sources']['collect_stress_mcc.py'] and manifest['importer_sha256']==provenance['sources']['smpt_import.py']
models={}
for q in manifest['queries']:
 if q['status']!='imported':continue
 for path,h in [(q[k],q[k+'_sha256']) for k in ['pnml','xml','net','property']]+[(b['path'],b['sha256']) for b in q['branches']]:
  p=C/path;assert not p.is_symlink() and p.resolve().is_relative_to(C.resolve())
  key=str(p.relative_to(ROOT))
  if key not in pins:pins[key]=sha(p)
  assert pins[key]==h
 original[(q['pnml_sha256'],q['xml_sha256'])].append(q['name'])
 canonical[tuple(b['sha256'] for b in q['branches'])].append(q['name'])
 if q['instance'] not in models:
  b=json.loads((C/q['branches'][0]['path']).read_text());weights=[w for t in b['transitions'] for side in ['pre','post'] for _,w in t[side]]
  models[q['instance']]=dict(family=q['family'],places=len(b['places']),transitions=len(b['transitions']),arcs=len(weights),weighted_arcs=sum(w>1 for w in weights),max_arc_weight=max(weights,default=0),max_initial_marking=max(b['initial'],default=0),initial_tokens=sum(b['initial']))
prior=json.loads((ROOT/'benchmarks/general-development-v3/manifest.json').read_text())
prior_groups=defaultdict(list)
for q in prior['queries']:
 if q['status']=='imported':prior_groups[tuple(b['sha256'] for b in q['branches'])].append(q['name'])
overlaps=[dict(new=names,prior=prior_groups[key]) for key,names in canonical.items() if key in prior_groups]
assert not overlaps
helper=F/'check_original_import'
if not helper.exists():shutil.copyfile(ROOT/'target/release/examples/check_original_import',helper);helper.chmod(0o755)
helper_hash=sha(helper);checks=[];logs=F/'import-checks';logs.mkdir(exist_ok=True)
for q in manifest['queries']:
 if q['status']!='imported':checks.append(dict(query=q['name'],status='unavailable'));continue
 assert sha(helper)==helper_hash
 result=subprocess.run([str(helper),str(C),q['name']],capture_output=True,text=True,timeout=60)
 path=logs/(q['name']+'.json');path.write_text(result.stdout+result.stderr)
 answer=json.loads(result.stdout) if result.returncode==0 else None
 expected_answer=dict(status='matched',query=q['name'],property_id=q['property_id'],kind=q['kind'],branches=len(q['branches']))
 assert result.returncode==0 and answer==expected_answer,(q['name'],result.returncode,result.stderr)
 checks.append(dict(query=q['name'],status='matched',log_sha256=sha(path)))
assert all(sha(ROOT/p)==h for p,h in pins.items())
report=dict(status='passed',completed_utc=datetime.now(timezone.utc).isoformat(),selection_sha256=receipt['selection_sha256'],manifest_sha256=sha(C/'manifest.json'),auditor_sha256=sha(Path(__file__)),planned_properties=192,imported_properties=sum(q['status']=='imported' for q in manifest['queries']),
 exact_original_representatives=len(original),ordered_branch_representatives=len(canonical),exact_original_duplicates=[v for v in original.values() if len(v)>1],ordered_branch_duplicates=[v for v in canonical.values() if len(v)>1],prior176_ordered_branch_overlaps=overlaps,property_kinds=dict(Counter(q.get('kind','unavailable') for q in manifest['queries'])),models=models,files_sha256=pins,independent_import_checks=checks,helper_sha256=helper_hash,
 scope='All original slots retained. Rust original-input parser agrees exactly with independently collected Python canonical branches, including polarity and every branch. Original archive/payload/canonical bytes rehashed. No solver was run; property truth and hardness are unknown. EF/AG syntax is not truth polarity. Related family exclusions use names, not a proof of generator independence.')
(F/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Development expansion v4','',f"192 original properties from six new MCC family groups and two instances each; all 192 import and independently match. {len(canonical)} distinct ordered-branch representatives; {len(original)} exact original-input representatives. No canonical overlap with the previous 176 properties.",'',
 'Selection was frozen before acquisition and solver runs. All reserved evaluation families are excluded. The existing 176 properties remain part of the regression cohort, giving 368 original slots. This is development data; neither hardness nor positive/negative truth balance is established before solver measurement.','',
 '| Instance | Places | Transitions | Weighted arcs | Max initial marking |','|---|---:|---:|---:|---:|']
for name,m in models.items():lines.append(f"| {name} | {m['places']} | {m['transitions']} | {m['weighted_arcs']} | {m['max_initial_marking']} |")
lines+=['','Original PNML, single-property XML, canonical branches, archive checksums, collector provenance and all collection outcomes are in `benchmarks/development-expansion-v4`. The frozen selection, byte audit, exact duplicate groups and independent import evidence are in this directory.','', 'Retain all 192 rows in reporting. Use ordered-branch representatives for the secondary deduplicated comparison; report failures and each family/instance separately. EF and AG describe formula syntax, not positive/negative reachability.','', 'Selection SHA-256: `'+receipt['selection_sha256']+'`.','']
(F/'README.md').write_text('\n'.join(lines))
print(json.dumps({k:report[k] for k in ['status','planned_properties','imported_properties','exact_original_representatives','ordered_branch_representatives','property_kinds']}))
