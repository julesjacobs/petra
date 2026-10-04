"""Freeze new MCC development families using index and selection metadata only."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
F=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=['vendor/mcc2021/index.html','benchmarks/general-development-v3-selection.json','benchmarks/reserved-evaluation-v2.json','benchmarks/application-parameter-ladders-v2-selection.json','benchmarks/application-expansion-v1-selection.json','benchmarks/mcc-selection.json','benchmarks/publication-selection.json','benchmarks/stress-selection.json']
prior=json.loads((ROOT/inputs[1]).read_text())
reserved=set(prior['reserved_families_excluded'])|set(json.loads((ROOT/inputs[2]).read_text())['reserved_families'])
used=set(prior['recorded_used_families'])|{m['family'] for m in prior['models']}
def group(f):
 for prefix in ['RERS','IBM','DLC','Shield','Philosophers','MAPK']:
  if f.startswith(prefix):return prefix
 for part in ['ProductionCell','GPU','LeafsetExtension','ResAllocation']:
  if part in f:return part
 return f
chosen=['ASLink','MAPK','HouseConstruction','Railroad','NQueens','ClientsAndServers']
assert not {group(f) for f in chosen}&{group(f) for f in reserved|used}
raw=(ROOT/inputs[0]).read_text();names=list(dict.fromkeys(re.findall(r'INPUTS/([^"<>/]+-PT-[^"<>/]+)\.tgz',raw)))
families=defaultdict(list)
for n in names:families[n.split('-PT-')[0]].append(n)
models=[]
for f in chosen:
 for ordinal in sorted({(len(families[f])+1)//2,len(families[f])}):
  name=families[f][ordinal-1]
  models.append(dict(family=f,family_group=group(f),name=name,published_ordinal=ordinal,split='stress-development',url='https://yanntm.github.io/pnmcc-models-2021/INPUTS/'+name+'.tgz',expected_properties=16,property_class='ReachabilityCardinality'))
selection=dict(format='mcc-stress-selection-v1',status='selection-frozen-before-acquisition-and-solver-runs',frozen_utc=datetime.now(timezone.utc).isoformat(),
 selection='Six explicitly chosen previously unused MCC family groups spanning protocol, signaling, workflow, transport, combinatorial, and client/server models. Select median-rounded-up and final indexed PT instances in each; retain all 16 original ReachabilityCardinality slots. No model/property payload, solver result, truth polarity, input size, or collection success inspected before this freeze. Hardness and positive/negative balance remain to be measured; do not discard easy, unavailable, or unsuccessful rows.',
 source='https://yanntm.github.io/pnmcc-models-2021/',index_path=inputs[0],index_sha256=sha(ROOT/inputs[0]),expected_models=12,expected_properties=192,property_slots=list(range(16)),models=models,
 reserved_families_excluded=sorted(reserved),reserved_groups_excluded=sorted({group(f) for f in reserved}),recorded_used_families=sorted(used),
 input_sha256={p:sha(ROOT/p) for p in inputs},selector_sha256=sha(Path(__file__)),
 collector=dict(seconds=120,memory_mib=2048,archive_mib=256,expanded_mib=1024,artifact_mib=1024),
 scope='Development expansion; preserve full prior 176-property cohort in regression. Family labels name generator families, not a proof of independence. Reserved evaluation families remain excluded.',
 exact_duplicates='Report exact original PNML plus single-property XML identity, ordered canonical branch identity, and overlap against prior development cohort; preserve original slots and report representative denominator.',
 archive_identity='URLs/index bytes frozen now; original archive hashes will be recorded by bounded collector after acquisition.')
assert len(models)==12
with (F/'selection.json').open('x') as out:json.dump(selection,out,indent=2);out.write('\n')
receipt=dict(status='frozen',selection_sha256=sha(F/'selection.json'),families=chosen,models=[m['name'] for m in models],properties=192)
(F/'freeze-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
