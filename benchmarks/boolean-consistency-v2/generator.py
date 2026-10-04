#!/usr/bin/env python3
"""Generate a frozen development ladder of Boolean-consistency Petri nets.

The control token chooses each variable once and then visits every clause.
Literal tests are ordinary consume/produce self-loops. No inhibitor arcs,
capacities, preprocessing, oracle labels, or planted assignments are supplied
to the reachability solvers.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET

from smpt_import import pnml, properties, tina, translated_xml

ROOT = Path(__file__).resolve().parents[1]


def random_cnf(variables, clauses, seed):
    if variables < 3 or not 0 <= clauses <= 8 * math.comb(variables, 3):
        raise ValueError('Invalid count of distinct 3-clauses')
    rng = random.Random(seed)
    result = set()
    while len(result) < clauses:
        clause = tuple(sorted((v if rng.getrandbits(1) else -v)
                              for v in rng.sample(range(1, variables + 1), 3)))
        result.add(clause)
    return sorted(result)


def pigeonhole(pigeons, holes):
    def var(pigeon, hole):
        return pigeon * holes + hole + 1
    clauses = [[var(p, h) for h in range(holes)] for p in range(pigeons)]
    clauses += [[-var(p, h), -var(q, h)] for h in range(holes)
                for p in range(pigeons) for q in range(p + 1, pigeons)]
    return clauses


def cases():
    for variables in (24, 48, 72, 96):
        for numerator in (380, 426, 480):
            for seed in (2026092701, 2026092702):
                count = (variables * numerator + 50) // 100
                yield dict(name=f'random3_n{variables}_r{numerator}_s{seed}',
                           family='random-3sat', parameters=dict(variables=variables,
                           clauses=count, ratio_hundredths=numerator, seed=seed),
                           variables=variables, clauses=random_cnf(variables, count, seed),
                           expected_reachable=None, expectation_basis='Unlabelled random formula.')
    for holes in (4, 6, 8, 10, 12):
        for extra in (0, 1):
            pigeons = holes + extra
            yield dict(name=f'pigeonhole_p{pigeons}_h{holes}', family='pigeonhole',
                       parameters=dict(pigeons=pigeons, holes=holes),
                       variables=pigeons * holes, clauses=pigeonhole(pigeons, holes),
                       expected_reachable=not extra,
                       expectation_basis='Injective placement exists iff pigeons <= holes; '
                       'each pigeon must occupy a hole and no pair may share a hole.')


def encode(variables, clauses):
    if variables < 1 or any(not c or any(not 1 <= abs(v) <= variables for v in c) for c in clauses):
        raise ValueError('Expected nonempty clauses over declared variables')
    places = [f'choose_{i}' for i in range(variables)]
    places += [f'clause_{i}' for i in range(len(clauses) + 1)]
    places += [f'v{i}_{value}' for i in range(1, variables + 1) for value in (0, 1)]
    ids = {p: i for i, p in enumerate(places)}
    transitions = []

    def transition(name, pre, post):
        transitions.append(dict(name=name, pre=sorted((ids[p], 1) for p in pre),
                                post=sorted((ids[p], 1) for p in post)))

    for i in range(variables):
        successor = f'choose_{i + 1}' if i + 1 < variables else 'clause_0'
        for value in (0, 1):
            transition(f'assign_{i + 1}_{value}', [f'choose_{i}'],
                       [successor, f'v{i + 1}_{value}'])
    for i, clause in enumerate(clauses):
        for j, literal in enumerate(clause):
            place = f'v{abs(literal)}_{int(literal > 0)}'
            transition(f'check_{i}_{j}', [f'clause_{i}', place], [f'clause_{i + 1}', place])
    initial = [int(i == 0) for i in range(len(places))]
    coefficients = [int(p == f'clause_{len(clauses)}') for p in places]
    return dict(places=places, initial=initial, transitions=transitions,
                target=[dict(coefficients=coefficients, bound=1, equality=False)])


def pnml_text(model):
    root = ET.Element('pnml')
    net = ET.SubElement(root, 'net', id='boolean_consistency',
                        type='http://www.pnml.org/version-2009/grammar/ptnet')
    page = ET.SubElement(net, 'page', id='page')
    for name, count in zip(model['places'], model['initial']):
        place = ET.SubElement(page, 'place', id=name)
        ET.SubElement(ET.SubElement(place, 'initialMarking'), 'text').text = str(count)
    serial = 0
    for t in model['transitions']:
        ET.SubElement(page, 'transition', id=t['name'])
        for field in ('pre', 'post'):
            for p, weight in t[field]:
                ends = (model['places'][p], t['name']) if field == 'pre' else (t['name'], model['places'][p])
                arc = ET.SubElement(page, 'arc', id=f'a{serial}', source=ends[0], target=ends[1])
                ET.SubElement(ET.SubElement(arc, 'inscription'), 'text').text = str(weight)
                serial += 1
    return ET.tostring(root, encoding='unicode') + '\n'


def property_text(clauses):
    return ('<property-set><property><id>accepting</id><description>Accepting control place</description>'
            '<formula><exists-path><finally>'
            '<integer-le><integer-constant>1</integer-constant><tokens-count>'
            f'<place>clause_{clauses}</place></tokens-count></integer-le>'
            '</finally></exists-path></formula></property></property-set>\n')


def generate(output):
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in cases():
        folder = output / case['name']
        folder.mkdir()
        model = encode(case['variables'], case['clauses'])
        (folder / 'model.pnml').write_text(pnml_text(model))
        (folder / 'original-property.xml').write_text(property_text(len(case['clauses'])))
        # Fail collection if the independent PNML reader disagrees with the encoder.
        imported = pnml(folder / 'model.pnml')
        prop = properties(folder / 'original-property.xml', imported)[0]
        imported['target'] = prop.pop('targets')[0]
        if imported != model:
            raise ValueError(f'Encoding roundtrip mismatch: {case["name"]}')
        (folder / 'branch-0.json').write_text(json.dumps(model, separators=(',', ':')) + '\n')
        (folder / 'model.net').write_text(tina(model))
        (folder / 'property.xml').write_text(translated_xml(folder / 'original-property.xml', model['places']))
        formula = f'p cnf {case["variables"]} {len(case["clauses"])}\n'
        formula += ''.join(' '.join(map(str, clause)) + ' 0\n' for clause in case['clauses'])
        (folder / 'source.cnf').write_text(formula)

        def digest(name):
            return hashlib.sha256((folder / name).read_bytes()).hexdigest()

        record = {k: v for k, v in case.items() if k != 'clauses'}
        record.update(prop, suite='synthetic-development', instance=case['name'], status='imported',
                      places=len(model['places']), transitions=len(model['transitions']),
                      branches=[dict(path=f'{case["name"]}/branch-0.json', sha256=digest('branch-0.json'))],
                      source_cnf=f'{case["name"]}/source.cnf', source_cnf_sha256=digest('source.cnf'))
        for key, filename in [('pnml', 'model.pnml'), ('xml', 'original-property.xml'),
                              ('net', 'model.net'), ('property', 'property.xml')]:
            record[key] = f'{case["name"]}/{filename}'
            record[key + '_sha256'] = digest(filename)
        records.append(record)
    manifest = dict(format='smpt-classic-v1', source='Deterministic generated ordinary 1-safe Petri nets',
                    selection='All 34 preselected cases, no outcome filtering. '
                    'Random 3-CNF at three ratios around the SAT threshold, two fixed seeds, '
                    'four sizes; positive/negative pigeonhole pairs at five sizes.',
                    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    expected_properties=34, scope='Synthetic development only. Difficulty is measured, '
                    'not inferred from size. Complements MCC and raw SER; not held-out evaluation.',
                    queries=records)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'generator.py').write_bytes(Path(__file__).read_bytes())
    print(f'Generated {len(records)} queries at {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks/boolean-consistency-v2')
    generate(parser.parse_args().output)
