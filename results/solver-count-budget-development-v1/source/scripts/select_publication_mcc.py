#!/usr/bin/env python3
"""Freeze new MCC families using source order and a result-independent hash rule."""
import collections
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def select(index, previous):
    families = collections.defaultdict(list)
    for name in dict.fromkeys(re.findall(r'INPUTS/([^"/]+-PT-[^"/]+)\.tgz', index)):
        families[name.split('-PT-')[0]].append(name)
    # RERS numbered problems share a generator; keep them in the same split.
    group = lambda family: 'RERS' if family.startswith('RERS') else family
    old = {group(row['family']) for row in previous['models']}
    eligible = collections.defaultdict(list)
    for family, instances in families.items():
        if len(instances) >= 5 and group(family) not in old:
            eligible[group(family)].append(family)
    rank = lambda key: hashlib.sha256(('pvass-publication-v1:'+key).encode()).hexdigest()
    groups = sorted(eligible, key=rank)[:16]
    models = []
    for i, key in enumerate(groups):
        family = sorted(eligible[key])[0]
        for tier in (2, 4):
            name = families[family][tier]
            models.append(dict(family=family, family_group=key, name=name,
                               published_ordinal=tier+1,
                               split='development' if i < 8 else 'evaluation',
                               url='https://yanntm.github.io/pnmcc-models-2021/INPUTS/'+name+'.tgz'))
    return dict(selection='Exclude previously used family groups. Group all RERS families together. Among groups with at least five published PT instances, rank by SHA256(pvass-publication-v1:group), select first sixteen groups, choose lexicographically first eligible family per group and its third and fifth published instances. First eight groups develop, next eight evaluate. Keep all original ReachabilityCardinality properties, including trivial or unsupported ones. Fixed before any solver runs on these inputs.',
                index_sha256=hashlib.sha256(index.encode()).hexdigest(), models=models)


if __name__ == '__main__':
    path = ROOT/'benchmarks/publication-selection.json'
    if path.exists():
        raise SystemExit('Selection already frozen; refusing to replace it')
    source = ROOT/'vendor/mcc2021/index.html'
    result = select(source.read_text(), json.loads((ROOT/'benchmarks/mcc-selection.json').read_text()))
    path.write_text(json.dumps(result, indent=2)+'\n')
    print('Frozen',len(result['models']),'models')
