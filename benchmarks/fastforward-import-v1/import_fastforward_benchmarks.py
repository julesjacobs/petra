#!/usr/bin/env python3
"""Convert pinned unpruned LoLA pairs to checked, common PNML/XML/JSON inputs.

Source conversion is offline and must not be described as timed original-LoLA
frontend processing. All source queries remain in the manifest denominator.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from audit_fastforward_benchmarks import parse_net, parse_formula
from smpt_import import pnml, properties, tina, translated_xml


def pnml_text(net):
    root = ET.Element('pnml', xmlns='http://www.pnml.org/version-2009/grammar/pnml')
    document = ET.SubElement(root, 'net', id='fastforward_import', type='http://www.pnml.org/version-2009/grammar/ptnet')
    page = ET.SubElement(document, 'page', id='page')
    for i, count in enumerate(net['initial']):
        place = ET.SubElement(page, 'place', id=f'p{i}')
        ET.SubElement(ET.SubElement(place, 'name'), 'text').text = f'p{i}'
        ET.SubElement(ET.SubElement(place, 'initialMarking'), 'text').text = str(count)
    for i, transition in enumerate(net['transitions']):
        node = ET.SubElement(page, 'transition', id=f't{i}')
        ET.SubElement(ET.SubElement(node, 'name'), 'text').text = f't{i}'
        for direction, arcs in (('pre', transition['pre']), ('post', transition['post'])):
            for place, weight in arcs:
                source, target = (f'p{place}', f't{i}') if direction == 'pre' else (f't{i}', f'p{place}')
                arc = ET.SubElement(page, 'arc', id=f'a_{i}_{direction}_{place}', source=source, target=target)
                ET.SubElement(ET.SubElement(arc, 'inscription'), 'text').text = str(weight)
    return ET.tostring(root, encoding='unicode') + '\n'


def inequalities(predicates):
    result = []
    for branch in predicates:
        terms = []
        for place, bound, equality in branch:
            if bound:
                terms.append((place, 1, bound))
            if equality:
                terms.append((place, -1, -bound))
        result.append(terms)
    return result


def property_text(branches):
    root = ET.Element('property-set')
    prop = ET.SubElement(root, 'property')
    ET.SubElement(prop, 'id').text = 'reachability'
    ET.SubElement(prop, 'description').text = 'Exact import of an unpruned FastForward repository query'
    formula = ET.SubElement(prop, 'formula')
    finally_node = ET.SubElement(ET.SubElement(formula, 'exists-path'), 'finally')
    disjunction = ET.SubElement(finally_node, 'disjunction') if len(branches) != 1 else finally_node
    for branch in branches:
        conjunction = ET.SubElement(disjunction, 'conjunction') if len(branch) > 1 else disjunction
        if not branch:
            ET.SubElement(conjunction, 'true')
        for place, sign, bound in branch:
            predicate = ET.SubElement(conjunction, 'integer-le')
            if sign == 1:
                ET.SubElement(predicate, 'integer-constant').text = str(bound)
                ET.SubElement(ET.SubElement(predicate, 'tokens-count'), 'place').text = f'p{place}'
            else:
                ET.SubElement(ET.SubElement(predicate, 'tokens-count'), 'place').text = f'p{place}'
                ET.SubElement(predicate, 'integer-constant').text = str(-bound)
    return ET.tostring(root, encoding='unicode') + '\n'


def source_semantics(net, targets):
    return {'initial': net['initial'],
            'transitions': [{'pre': t['pre'], 'post': t['post']} for t in net['transitions']],
            'targets': targets}


def write_json(path, value):
    with path.open('w') as stream:
        json.dump(value, stream, separators=(',', ':'))
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('benchmarks/fastforward-repository-v1'))
    parser.add_argument('--output', type=Path, default=Path('benchmarks/fastforward-import-v1'))
    parser.add_argument('--max-coefficient-entries', type=int, default=20_000_000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source_manifest = json.loads((args.source / 'acquisition.json').read_text())
    files = {entry['path']: entry for entry in source_manifest['files']}
    records = []
    semantic_hashes = defaultdict(list)
    for source, entry in files.items():
        if not source.endswith('.lola'):
            continue
        suite = source.split('/')[3]
        local_name = source.removeprefix(f'artifact/benchmark/nets/{suite}/').removesuffix('.lola')
        name = 'ff_' + suite + '_' + re.sub('[^A-Za-z0-9_]', '_', local_name)[:100] + '_' + hashlib.sha256(source.encode()).hexdigest()[:8]
        row = {'name': name, 'suite': 'fastforward-repository-' + suite, 'instance': local_name,
               'source_lola': source, 'source_lola_sha256': entry['sha256'],
               'source_formula': source[:-5] + '.formula', 'kind': 'EF', 'property_id': 'reachability',
               'expected_reachable': None, 'upstream_expectation': 'positive; not independently verified'}
        records.append(row)
        try:
            contents = []
            for path in (source, row['source_formula']):
                data = (args.source / 'upstream' / path).read_bytes()
                if hashlib.sha256(data).hexdigest() != files[path]['sha256']:
                    raise ValueError('source checksum mismatch')
                contents.append(data.decode())
            row['source_formula_sha256'] = files[row['source_formula']]['sha256']
            net = parse_net(contents[0])
            predicates = parse_formula(contents[1], net['places'])
            branches = inequalities(predicates)
            entries = len(net['places']) * sum(map(len, branches))
            row.update(places=len(net['places']), transitions=len(net['transitions']),
                       dense_coefficient_entries=entries,
                       explicit_equality_zeros=sum(equality and bound == 0 for branch in predicates for _, bound, equality in branch))
            if entries > args.max_coefficient_entries:
                row.update(status='representation-limit', error='dense coefficient entry limit')
                continue
            semantic = hashlib.sha256(json.dumps(source_semantics(net, branches), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            row['indexed_semantics_sha256'] = semantic
            semantic_hashes[semantic].append(name)
            folder = args.output / name
            folder.mkdir()
            (folder / 'model.pnml').write_text(pnml_text(net))
            (folder / 'original-property.xml').write_text(property_text(branches))
            write_json(folder / 'source-mapping.json', {'places': net['places'], 'transitions': [t['name'] for t in net['transitions']]})
            imported = pnml(folder / 'model.pnml')
            expected_net = {'places': [f'p{i}' for i in range(len(net['places']))], 'initial': net['initial'],
                            'transitions': [{'name': f't{i}', 'pre': [tuple(a) for a in t['pre']], 'post': [tuple(a) for a in t['post']]} for i, t in enumerate(net['transitions'])],
                            'target': []}
            if imported != expected_net:
                raise ValueError('independent PNML roundtrip mismatch')
            prop = properties(folder / 'original-property.xml', imported)[0]
            targets = prop.pop('targets')
            if len(targets) != len(branches):
                raise ValueError('independent XML branch count mismatch')
            branch_records = []
            for i, (target, expected) in enumerate(zip(targets, branches)):
                if len(target) != len(expected):
                    raise ValueError('independent XML constraint count mismatch')
                for constraint, (place, sign, bound) in zip(target, expected):
                    if constraint['equality'] or constraint['bound'] != bound or any(a != (sign if j == place else 0) for j, a in enumerate(constraint['coefficients'])):
                        raise ValueError('independent XML predicate mismatch')
                imported['target'] = target
                filename = f'branch-{i}.json'
                write_json(folder / filename, imported)
                branch_records.append({'path': f'{name}/{filename}', 'sha256': hashlib.sha256((folder / filename).read_bytes()).hexdigest()})
            (folder / 'model.net').write_text(tina(imported))
            (folder / 'property.xml').write_text(translated_xml(folder / 'original-property.xml', imported['places']))
            row.update(status='imported', branches=branch_records, translation_check='strict-lola-parser-plus-independent-pnml-xml-roundtrip')
            for key, filename in [('pnml', 'model.pnml'), ('xml', 'original-property.xml'), ('net', 'model.net'), ('property', 'property.xml'), ('source_mapping', 'source-mapping.json')]:
                row[key] = f'{name}/{filename}'
                row[key + '_sha256'] = hashlib.sha256((folder / filename).read_bytes()).hexdigest()
        except (ValueError, KeyError, UnicodeError) as error:
            row.update(status='unsupported', error=str(error))
        if len(records) % 20 == 0:
            print('processed', len(records), 'queries', flush=True)
    manifest = {'format': 'smpt-classic-v1', 'source': source_manifest['repository'], 'commit': source_manifest['commit'],
                'acquisition_manifest': str(args.source / 'acquisition.json'),
                'acquisition_sha256': hashlib.sha256((args.source / 'acquisition.json').read_bytes()).hexdigest(),
                'expected_properties': len(records), 'max_coefficient_entries': args.max_coefficient_entries,
                'scope': 'Unpruned repository development suite, all pairs retained in denominator. PNML/XML is generated offline from original LoLA. Solver timing on generated inputs excludes source conversion; not an original-LoLA end-to-end comparison or archived artifact reproduction.',
                'normalizations': ['Discard zero-weight arcs and zero lower bounds (tautologies)', 'Encode each equality as both inequalities, retaining exact zeros', 'Rename places/transitions bijectively, preserve mappings'],
                'queries': records,
                'duplicate_scope': 'Exact indexed semantics, excluding labels; preserves place and transition order and target-constraint order. Does not test graph isomorphism or arbitrary renaming.',
                'duplicate_groups': [names for names in semantic_hashes.values() if len(names) > 1]}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (args.output / 'LICENSE.upstream.txt').write_bytes((args.source / 'upstream/LICENSE.txt').read_bytes())
    snapshots = {}
    for script in (Path(__file__), Path(__file__).with_name('audit_fastforward_benchmarks.py'), Path(__file__).with_name('smpt_import.py')):
        data = script.read_bytes()
        (args.output / script.name).write_bytes(data)
        snapshots[script.name] = hashlib.sha256(data).hexdigest()
    (args.output / 'scripts.json').write_text(json.dumps(snapshots, indent=2) + '\n')
    print(json.dumps(dict(Counter(row['status'] for row in records))), flush=True)

if __name__ == '__main__':
    main()
