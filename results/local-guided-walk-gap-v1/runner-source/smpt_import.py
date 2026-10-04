#!/usr/bin/env python3
"""Import unreduced SMPT PNML nets and EF/AG integer properties into solver JSON."""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]


def xml_tree(path):
    root = ET.parse(path).getroot()
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    return root


def require(condition, message):
    if not condition:
        raise ValueError(message)


def only(node):
    require(len(node) == 1, f'Expected one child in {node.tag}')
    return node[0]


def number(node, child, default):
    values = node.findall(child)
    require(len(values) <= 1, f'Duplicate {child}')
    if not values:
        return default
    texts = values[0].findall('text')
    require(len(texts) == 1 and all(n.tag in ('text', 'graphics') for n in values[0]), f'Expected text in {child}')
    value = texts[0]
    result = int(value.text.strip())
    require(0 <= result < 2**64, f'{child} outside u64 range')
    return result


def pnml(path):
    root = xml_tree(path)
    require(root.tag == 'pnml' and len(root.findall('net')) == 1, 'Expected one PNML net')
    net = root.find('net')
    require(net.get('type', '').endswith('/ptnet'), 'Only ordinary P/T nets are supported')
    for parent in list(net.iter()):
        for child in list(parent):
            if child.tag == 'toolspecific' and child.get('tool') == 'nupn':
                parent.remove(child)
            elif child.tag == 'toolspecific' and child.get('tool') == 'Tina' and all(
                    n.tag in ('size', 'color') and not len(n) for n in child):
                parent.remove(child)
    allowed = {
        'net': {'name', 'page'}, 'page': {'name', 'page', 'place', 'transition', 'arc', 'graphics'},
        'place': {'name', 'initialMarking', 'graphics'},
        'transition': {'name', 'graphics'}, 'arc': {'name', 'inscription', 'graphics'},
    }
    for node in net.iter():
        if node.tag in allowed:
            require(all(c.tag in allowed[node.tag] for c in node), f'Unsupported {node.tag} extension')
            require(not (set(node.attrib) - {'id', 'type', 'source', 'target'}), 'Unsupported PNML attributes')
            if node.tag == 'arc':
                require('type' not in node.attrib, 'Typed arcs are unsupported')
    places = list(net.iter('place'))
    transitions = list(net.iter('transition'))
    identifiers = [n.attrib['id'] for n in places+transitions]
    require(len(set(identifiers)) == len(identifiers), 'Duplicate PNML node ID')
    pids = {n.attrib['id']: i for i, n in enumerate(places)}
    tids = {n.attrib['id']: i for i, n in enumerate(transitions)}
    arcs = [[collections.Counter(), collections.Counter()] for _ in transitions]
    for arc in net.iter('arc'):
        source, target = arc.attrib['source'], arc.attrib['target']
        weight = number(arc, 'inscription', 1)
        require(weight > 0, 'Arc weight must be positive')
        if source in pids and target in tids:
            bucket, place = arcs[tids[target]][0], pids[source]
        elif source in tids and target in pids:
            bucket, place = arcs[tids[source]][1], pids[target]
        else:
            raise ValueError(f'Non-bipartite or unknown arc endpoints: {source}, {target}')
        bucket[place] += weight
        require(bucket[place] < 2**64, 'Arc weight overflow')
    return dict(places=list(pids), initial=[number(n, 'initialMarking', 0) for n in places],
                transitions=[dict(name=n.attrib['id'], pre=sorted(pre.items()), post=sorted(post.items()))
                             for n, (pre, post) in zip(transitions, arcs)], target=[])


def expression(node, ids):
    if node.tag == 'integer-constant':
        require(len(node) == 0, 'Malformed integer constant')
        return [0]*len(ids), int(node.text.strip())
    if node.tag == 'tokens-count':
        require(len(node) > 0 and all(n.tag == 'place' and len(n) == 0 for n in node), 'Malformed tokens-count')
        coefficients = [0]*len(ids)
        for place in node:
            coefficients[ids[place.text.strip()]] += 1
        return coefficients, 0
    if node.tag in ('integer-sum', 'integer-add'):
        coefficients, constant = [0]*len(ids), 0
        for child in node:
            cs, k = expression(child, ids)
            coefficients = [a+b for a, b in zip(coefficients, cs)]
            constant += k
        return coefficients, constant
    raise ValueError(f'Unsupported integer expression: {node.tag}')


def dnf(node, ids, negate=False, limit=1024):
    if node.tag == 'negation':
        return dnf(only(node), ids, not negate, limit)
    if node.tag in ('true', 'false'):
        return [[]] if (node.tag == 'true') != negate else []
    if node.tag in ('conjunction', 'disjunction'):
        conjunction = (node.tag == 'conjunction') != negate
        result = [[]] if conjunction else []
        for child in node:
            terms = dnf(child, ids, negate, limit)
            size = len(result)*len(terms) if conjunction else len(result)+len(terms)
            require(size <= limit, 'Boolean target exceeds branch limit')
            result = [a+b for a, b in itertools.product(result, terms)] if conjunction else result+terms
        return result
    require(node.tag == 'integer-le' and len(node) == 2, f'Unsupported predicate: {node.tag}')
    left, lconst = expression(node[0], ids)
    right, rconst = expression(node[1], ids)
    coefficients = [a-b for a, b in zip(left, right)] if negate else [b-a for a, b in zip(left, right)]
    bound = rconst-lconst+1 if negate else lconst-rconst
    require(all(-2**63 <= x < 2**63 for x in coefficients+[bound]), 'Target exceeds i64 range')
    return [[dict(coefficients=coefficients, bound=bound, equality=False)]]


def properties(path, problem):
    root = xml_tree(path)
    require(root.tag == 'property-set', 'Expected property-set')
    ids = {name: i for i, name in enumerate(problem['places'])}
    result = []
    for prop in root:
        require(prop.tag == 'property', 'Expected property')
        formula = only(prop.find('formula'))
        temporal = only(formula)
        kind = (formula.tag, temporal.tag)
        require(kind in [('exists-path', 'finally'), ('all-paths', 'globally')], 'Only EF and AG supported')
        invariant = kind[0] == 'all-paths'
        result.append(dict(property_id=prop.findtext('id'), kind='AG' if invariant else 'EF',
                           targets=dnf(only(temporal), ids, invariant)))
    return result


def tina(problem):
    # Use generated IDs; source PNML IDs remain in the JSON and mapping manifest.
    def arcs(values):
        return ' '.join(f'p{i}*{w}' for i, w in values)
    lines = ['net imported']+[f'pl p{i} ({m})' for i, m in enumerate(problem['initial'])]
    lines += [f'tr t{i} {arcs(t["pre"])} -> {arcs(t["post"])}' for i, t in enumerate(problem['transitions'])]
    return '\n'.join(lines)+'\n'


def translated_xml(path, places):
    root = xml_tree(path)
    mapping = {p: f'p{i}' for i, p in enumerate(places)}
    for count in root.iter('tokens-count'):
        for place in count:
            place.text = mapping[place.text.strip()]
    return ET.tostring(root, encoding='unicode')+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=pathlib.Path, default=ROOT/'vendor/smpt-benchmarks/tacas2022/Artifact')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'benchmarks/smpt-classic')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    license_path = args.source.parent/'License.txt'
    if license_path.exists():
        (args.output/'LICENSE.upstream.txt').write_bytes(license_path.read_bytes())
    records = []
    for suite in ('Performance', 'Expressiveness', 'Certificates'):
        for instance in (args.source/suite/'instances').read_text().splitlines():
            if not instance.strip():
                continue
            stem = args.source/suite/'nets'/instance
            net = stem.with_suffix('.pnml') if suite == 'Performance' else stem/'model.pnml'
            xml = stem.with_name(stem.name+'_.xml') if suite == 'Performance' else stem/'ReachabilityCardinality.xml'
            name = suite+'__'+instance.replace('/', '__')
            record = dict(name=name, suite=suite, instance=instance,
                          pnml=str(net.resolve()), xml=str(xml.resolve()),
                          pnml_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),
                          xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest())
            try:
                problem = pnml(net)
                props = properties(xml, problem)
                require(len(props) == 1, 'Expected one property per published instance')
                prop = props[0]
                directory = args.output/name
                directory.mkdir(exist_ok=True)
                branches = []
                for i, target in enumerate(prop.pop('targets')):
                    branch = directory/f'branch-{i}.json'
                    branch.write_text(json.dumps(dict(problem, target=target), separators=(',', ':'))+'\n')
                    branches.append(dict(path=str(branch.relative_to(args.output)), sha256=hashlib.sha256(branch.read_bytes()).hexdigest()))
                net_path, xml_path = directory/'model.net', directory/'property.xml'
                net_path.write_text(tina(problem))
                xml_path.write_text(translated_xml(xml, problem['places']))
                record.update(prop, status='imported', branches=branches, places=len(problem['places']),
                              transitions=len(problem['transitions']),
                              net=str(net_path.relative_to(args.output)), property=str(xml_path.relative_to(args.output)),
                              net_sha256=hashlib.sha256(net_path.read_bytes()).hexdigest(),
                              property_sha256=hashlib.sha256(xml_path.read_bytes()).hexdigest())
            except (ValueError, KeyError, TypeError, AttributeError) as error:
                record.update(status='unsupported', error=str(error))
            records.append(record)
    manifest = dict(format='smpt-classic-v1', source='https://doi.org/10.5281/zenodo.5863379',
                    importer_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                    queries=records)
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(collections.Counter(r['status'] for r in records))


if __name__ == '__main__':
    main()
