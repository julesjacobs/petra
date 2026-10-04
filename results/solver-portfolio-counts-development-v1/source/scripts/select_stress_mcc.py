#!/usr/bin/env python3
"""Freeze larger published instances of publication-development MCC families."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://yanntm.github.io/pnmcc-models-2021/'
RULE = ('Use only families in publication-selection with split=development. In each family, '
        'preserve the source index published PT instance order, deduplicating names at first occurrence. '
        'Choose the last three instances with ordinal greater than the largest previously selected '
        'development ordinal, or all qualifying instances if fewer than three. Keep all 16 '
        'ReachabilityCardinality property slots per model, including failed imports. '
        'Selection uses no solver outcomes. This is stress-development, not independent held-out evaluation.')


def select(index_bytes, previous_bytes):
    previous = json.loads(previous_bytes)
    families = defaultdict(list)
    for name in dict.fromkeys(re.findall(r'INPUTS/([^"/]+-PT-[^"/]+)\.tgz', index_bytes.decode())):
        families[name.split('-PT-')[0]].append(name)
    prior = defaultdict(list)
    for row in previous['models']:
        if row['split'] == 'development':
            prior[row['family']].append(row)
    models, decisions = [], []
    for family, rows in prior.items():
        names = families[family]
        for row in rows:
            ordinal = row['published_ordinal']
            if ordinal < 1 or ordinal > len(names) or names[ordinal - 1] != row['name']:
                raise ValueError(f'Prior ordinal disagrees with source index: {row["name"]}')
        maximum = max(row['published_ordinal'] for row in rows)
        chosen = list(enumerate(names, 1))[maximum:][-3:]
        decisions.append(dict(family=family, previous_max_ordinal=maximum,
                              published_instances=len(names), eligible_instances=len(names)-maximum,
                              selected_ordinals=[ordinal for ordinal, _ in chosen]))
        for ordinal, name in chosen:
            models.append(dict(family=family, family_group=rows[0].get('family_group', family),
                               name=name, published_ordinal=ordinal, split='stress-development',
                               url=SOURCE+'INPUTS/'+name+'.tgz', expected_properties=16,
                               property_class='ReachabilityCardinality'))
    return dict(format='mcc-stress-selection-v1', selection=RULE, source=SOURCE,
                index_sha256=hashlib.sha256(index_bytes).hexdigest(),
                prior_selection_sha256=hashlib.sha256(previous_bytes).hexdigest(),
                expected_models=len(models), expected_properties=16*len(models),
                family_decisions=decisions, models=models)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=ROOT/'vendor/mcc2021/index.html')
    parser.add_argument('--previous', type=Path, default=ROOT/'benchmarks/publication-selection.json')
    parser.add_argument('--output', type=Path, default=ROOT/'benchmarks/stress-selection.json')
    args = parser.parse_args()
    result = select(args.index.read_bytes(), args.previous.read_bytes())
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    print(f'Frozen {result["expected_models"]} models, {result["expected_properties"]} planned properties')


if __name__ == '__main__':
    main()
