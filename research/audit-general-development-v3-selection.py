"""Check the immutable metadata-only selection without reading model payloads."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'benchmarks/general-development-v3-selection.json'
plan=json.loads(path.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in plan['input_sha256'].items():assert sha(ROOT/name)==digest,name
assert sha(ROOT/'research/select-general-development-v3.py')==plan['selector_sha256']
assert len(plan['reserved_families_excluded'])==22
assert len(plan['models'])==plan['expected_models']==11
assert plan['expected_properties']==16*len(plan['models'])==176
assert plan['property_slots']==list(range(16))
models=plan['models'];assert len({m['name'] for m in models})==len(models)
index=(ROOT/plan['index_path']).read_text()
indexed=list(dict.fromkeys(re.findall(r'INPUTS/([^"<>/]+-PT-[^"<>/]+)\.tgz',index)))
decisions={d['family']:d for d in plan['family_decisions']}
assert {n.split('-PT-')[0] for n in indexed}==set(decisions)
reserved=set(plan['reserved_groups_excluded']);used=set(plan['recorded_used_groups'])
eligible={f for f,d in decisions.items() if d['family_group'] not in reserved|used}
ranked=sorted(eligible,key=lambda f:(hashlib.sha256(('pvass-general-development-v3:'+f).encode()).hexdigest(),f))
assert ranked==plan['eligible_ranked']
selected=[];groups=set()
for family in ranked:
 g=decisions[family]['family_group']
 if g not in groups and len(selected)<6:selected.append(family);groups.add(g)
assert set(selected)=={m['family'] for m in models} and len(groups)==6
assert not groups & (reserved|used)
for family,d in decisions.items():
 names=[n for n in indexed if n.split('-PT-')[0]==family]
 assert len(names)==d['indexed_instances']
 chosen=[m for m in models if m['family']==family]
 expected=sorted({(len(names)+1)//2,len(names)}) if family in selected else []
 assert [m['published_ordinal'] for m in chosen]==expected==d['selected_ordinals']
 for m in chosen:
  assert names[m['published_ordinal']-1]==m['name']
  assert m['family_group']==d['family_group']
  assert m['url']==plan['source']+'INPUTS/'+m['name']+'.tgz'
  assert urlparse(m['url']).hostname=='yanntm.github.io'
  assert m['expected_properties']==16 and m['property_class']=='ReachabilityCardinality'
  assert m['family'] not in plan['reserved_families_excluded']
report=dict(status='passed',models=len(models),slots=plan['expected_properties'],groups=sorted(groups),
 selection_sha256=sha(path),auditor_sha256=sha(Path(__file__)),
 input_sha256=plan['input_sha256'],
 scope='Selection/index metadata only. No reserved model/property/result or candidate payload read; no collector or solver executed. Name/group exclusions are conservative metadata rules, not semantic independence or hardness evidence.')
(ROOT/'research/general-development-v3-selection-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
