#!/usr/bin/env python3
"""Collect a preselected, family-separated MCC 2021 corpus without net reductions."""
import concurrent.futures
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import tarfile
import xml.etree.ElementTree as ET

from smpt_import import ROOT, pnml, properties, tina, translated_xml, xml_tree


def download(row):
    archive = ROOT/'vendor/mcc2021/archives'/f'{row["name"]}.tgz'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        temporary = archive.with_suffix('.part')
        subprocess.run(['curl', '-L', '--fail', '--max-time', '120', '--retry', '2', '-s',
                        row['url'], '-o', str(temporary)], check=True)
        temporary.replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if 'sha256' in row and digest != row['sha256']:
        raise ValueError(f'Archive hash mismatch: {archive}')
    row['sha256'] = digest
    destination = ROOT/'vendor/mcc2021/inputs'
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            path = pathlib.PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not member.isfile():
                continue
            target = destination/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=pathlib.Path, default=ROOT/'benchmarks/mcc-selection.json')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'benchmarks/mcc2021')
    args = parser.parse_args()
    selection_path = args.selection.resolve()
    selection = json.loads(selection_path.read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        selection['models'] = list(executor.map(download, selection['models']))
    selection_path.write_text(json.dumps(selection, indent=2)+'\n')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for row in selection['models']:
        source = ROOT/'vendor/mcc2021/inputs'/row['name']
        xml = source/'ReachabilityCardinality.xml'
        try:
            root = xml_tree(xml)
            model = pnml(source/'model.pnml')
        except (ValueError, OSError) as error:
            records.append(dict(name=row['name'], status='unsupported', error=str(error), suite=row['split']))
            continue
        for i, node in enumerate(root):
            name = f'{row["name"]}__RC{i:02}'
            directory = output/name
            directory.mkdir(exist_ok=True)
            single = ET.Element('property-set')
            single.append(node)
            single_path = directory/'original-property.xml'
            single_path.write_text(ET.tostring(single, encoding='unicode')+'\n')
            record = dict(name=name, suite=row['split'], family=row['family'], instance=row['name'],
                          family_group=row.get('family_group', row['family']),
                          pnml=os.path.relpath(source/'model.pnml', output),
                          xml=str(single_path.relative_to(output)),
                          pnml_sha256=hashlib.sha256((source/'model.pnml').read_bytes()).hexdigest(),
                          xml_sha256=hashlib.sha256(single_path.read_bytes()).hexdigest())
            try:
                prop = properties(single_path, model)[0]
                branches = []
                for j, target in enumerate(prop.pop('targets')):
                    path = directory/f'branch-{j}.json'
                    path.write_text(json.dumps(dict(model, target=target), separators=(',', ':'))+'\n')
                    branches.append(dict(path=str(path.relative_to(output)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                net_path, prop_path = directory/'model.net', directory/'property.xml'
                net_path.write_text(tina(model))
                prop_path.write_text(translated_xml(single_path, model['places']))
                record.update(prop, status='imported', branches=branches, places=len(model['places']),
                              transitions=len(model['transitions']), net=str(net_path.relative_to(output)),
                              property=str(prop_path.relative_to(output)),
                              net_sha256=hashlib.sha256(net_path.read_bytes()).hexdigest(),
                              property_sha256=hashlib.sha256(prop_path.read_bytes()).hexdigest())
            except (ValueError, KeyError) as error:
                record.update(status='unsupported', error=str(error))
            records.append(record)
        print(row['name'], row['split'], len(model['places']), len(model['transitions']), flush=True)
    manifest = dict(format='smpt-classic-v1', source='https://yanntm.github.io/pnmcc-models-2021/',
                    selection_sha256=hashlib.sha256(selection_path.read_bytes()).hexdigest(), queries=records)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    for split in ('development', 'evaluation'):
        folder = output.with_name(f'{output.name}-{split}')
        folder.mkdir(exist_ok=True)
        selected = []
        for record in records:
            if record['suite'] != split:
                continue
            q = dict(record)
            if q['status'] == 'imported':
                q['branches'] = [dict(b, path=f'../{output.name}/'+b['path']) for b in q['branches']]
                for key in ('net', 'property', 'pnml', 'xml'):
                    q[key] = f'../{output.name}/'+q[key]
            selected.append(q)
        (folder/'manifest.json').write_text(json.dumps(dict(manifest, queries=selected), indent=2)+'\n')
    print('Imported', sum(r['status'] == 'imported' for r in records), '/', len(records))


if __name__ == '__main__':
    main()
