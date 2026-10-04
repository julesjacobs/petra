"""Freeze unused MCC development groups from index/selection metadata only."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SEED = 'pvass-general-development-v3:'
N_GROUPS = 6
SOURCE = 'https://yanntm.github.io/pnmcc-models-2021/'
INPUTS = ['vendor/mcc2021/index.html',
          'benchmarks/application-expansion-v1-selection.json',
          'benchmarks/application-parameter-ladders-v2-selection.json',
          'benchmarks/mcc-selection.json', 'benchmarks/publication-selection.json',
          'benchmarks/stress-selection.json']


def group(name):
    # Conservative exclusions for potentially related generators, not a theorem
    # that these names share a generator or all other groups are independent.
    if name.startswith('RERS'):
        return 'RERS'
    if name.startswith('IBM'):
        return 'IBM'
    if name.startswith('DLC'):
        return 'DLC'
    if 'ProductionCell' in name:
        return 'ProductionCell'
    if 'GPU' in name:
        return 'GPU'
    return name


def main():
    raw = {name:(ROOT/name).read_bytes() for name in INPUTS}
    expansion = json.loads(raw[INPUTS[1]])
    ladder = json.loads(raw[INPUTS[2]])
    reserved = set(ladder['reserved_families_excluded'])
    assert len(reserved) == 22
    used = set(expansion['recorded_used_mcc_families'])
    for name in INPUTS[1:]:
        used.update(m['family'] for m in json.loads(raw[name]).get('models', []))
    reserved_groups = {group(f) for f in reserved}
    used_groups = {group(f) for f in used}
    names = list(dict.fromkeys(re.findall(r'INPUTS/([^"<>/]+-PT-[^"<>/]+)\.tgz',raw[INPUTS[0]].decode())))
    families = defaultdict(list)
    for name in names:
        families[name.split('-PT-')[0]].append(name)
    eligible = [f for f in families if group(f) not in used_groups | reserved_groups]
    ranked = sorted(eligible, key=lambda f:(hashlib.sha256((SEED+f).encode()).hexdigest(),f))
    selected = []
    selected_groups = set()
    for family in ranked:
        g = group(family)
        if g not in selected_groups and len(selected) < N_GROUPS:
            selected.append(family);selected_groups.add(g)
    assert len(selected) == N_GROUPS and not selected_groups & (reserved_groups | used_groups)
    models = []
    for family in selected:
        instances = families[family]
        for ordinal in sorted({(len(instances)+1)//2,len(instances)}):
            name=instances[ordinal-1]
            models.append(dict(family=family,family_group=group(family),name=name,
                published_ordinal=ordinal,split='stress-development',
                url=SOURCE+'INPUTS/'+name+'.tgz',expected_properties=16,
                property_class='ReachabilityCardinality'))
    decisions=[]
    for family,instances in families.items():
        g=group(family)
        decision=('reserved-group' if g in reserved_groups else
                  'previously-used-group' if g in used_groups else
                  'selected' if family in selected else 'eligible-not-selected')
        decisions.append(dict(family=family,family_group=g,indexed_instances=len(instances),
            decision=decision,rank_sha256=hashlib.sha256((SEED+family).encode()).hexdigest(),
            selected_ordinals=[m['published_ordinal'] for m in models if m['family']==family]))
    result=dict(format='mcc-stress-selection-v1',status='selection-only; no acquisition or solver run',
        selection='Exclude every reserved and previously used family group using named selection metadata. Rank remaining families by SHA256(pvass-general-development-v3:+family), take first six distinct groups, and select median-rounded-up plus final indexed PT instance per family (deduplicate coincident ordinals). Retain all16ReachabilityCardinality slots. No model/property payload, solver outcome, polarity, input size or collection success enters selection. Development only; not held-out or established hardness.',
        source=SOURCE,index_path=INPUTS[0],index_sha256=hashlib.sha256(raw[INPUTS[0]]).hexdigest(),
        expected_models=len(models),expected_properties=16*len(models),property_slots=list(range(16)),
        models=models,family_decisions=decisions,eligible_ranked=ranked,
        reserved_families_excluded=sorted(reserved),reserved_groups_excluded=sorted(reserved_groups),
        recorded_used_families=sorted(used),recorded_used_groups=sorted(used_groups),
        group_policy='RERS*,IBM*,DLC* grouped by prefix; any ProductionCell or GPU names grouped conservatively; all others exact family names. This avoids obvious potential relatives, not a verified generator-independence claim.',
        input_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()},
        selector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        collector=dict(seconds=120,memory_mib=2048,archive_mib=256,expanded_mib=1024,artifact_mib=1024),
        acquisition_gate='Wait for local34053authoritative terminal. No acquisition, imports, builds, extra solvers or exports during local measurements. Linux31728gate remains independent.',
        archive_identity='Index freezes URLs/names only; acquire and hash original archive bytes later. Audit import semantics and exact/canonical duplicates before timing.',
        reporting='Retain full slot denominator and failures. Compare strongest current frozen native, matched predecessor, VerifyPN and full portable SMPT with matched5s/single-core/2GiB and separate native checking. Qualify all joint survivors at declared longer budgets without discarding parent rows. No superiority from selected subset or one repeat.')
    output=ROOT/'benchmarks/general-development-v3-selection.json'
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':'frozen-selection','models':len(models),'slots':16*len(models),'families':selected,'selection_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':main()
