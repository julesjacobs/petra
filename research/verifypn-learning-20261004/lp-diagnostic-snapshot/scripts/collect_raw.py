#!/usr/bin/env python3
"""Collect one untouched reachability question per source, with explicit failures."""
import argparse, hashlib, json, pathlib, shutil, subprocess, tempfile, time
from benchmark import run
ROOT = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--source', default='vendor/SerializabilityChecker/examples')
p.add_argument('--output', default='benchmarks/raw-original')
p.add_argument('--seconds', type=float, default=10)
p.add_argument('--filter', default='')
p.add_argument('--extensions', nargs='+', default=['.ser','.json'])
a=p.parse_args()
import re
source=ROOT/a.source; output=ROOT/a.output;output.mkdir(parents=True,exist_ok=True)
front=ROOT/'vendor/SerializabilityChecker/target/release/ser'
manifest=[]
for path in sorted(source.rglob('*')):
    if path.suffix not in a.extensions or path.name=='manifest.json':continue
    if a.filter and not re.search(a.filter,path.stem):continue
    relative=str(path.relative_to(source)); name=relative.replace('/','__').rsplit('.',1)[0]
    dest=output/name;dest.mkdir(exist_ok=True)
    record=dict(name=name,source=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with tempfile.TemporaryDirectory(prefix='pvass-raw-') as work:
        wall,code,expired=run([str(front),'--export-raw','--no-viz',str(path)],work,a.seconds,dest/'frontend.log')
        emitted=pathlib.Path(work)/'out'/path.stem/'raw-query.json'
        record.update(seconds=wall,exit_code=code,timeout=expired,status='exported' if code==0 and emitted.exists() else 'timeout' if expired else 'error')
        if record['status']=='exported':
            query=json.loads(emitted.read_text());shutil.copyfile(emitted,dest/'query.json')
            shutil.copyfile(emitted.with_name('raw.net'),dest/'raw.net')
            record.update(places=len(query['places']),transitions=len(query['transitions']),components=len(query['target']['excluded_semilinear']),query_sha256=hashlib.sha256(emitted.read_bytes()).hexdigest())
    manifest.append(record)
    (output/'collection.json').write_text(json.dumps(dict(frontend_sha256=hashlib.sha256(front.read_bytes()).hexdigest(),sources=manifest),indent=2))
    print(name,record['status'],record.get('places'),record.get('components'),flush=True)
