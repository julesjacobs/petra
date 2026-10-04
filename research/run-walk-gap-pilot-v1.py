"""Register three fixed seeds and a matched native baseline on all nine gaps."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from process_runner import workspace_workloads


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


assert not workspace_workloads(ROOT)
binary = ROOT/'results/solver-walk-v1/vass-reach'
provenance = json.loads(binary.with_name('provenance.json').read_text())
assert sha(binary) == provenance['binary_sha256']
assert sha(binary.with_name('source.tar.gz')) == provenance['source_sha256']
gaps = json.loads((ROOT/'research/application-positive-gaps-v1.json').read_text())
cases = [case['query'] for case in gaps['cases']]
assert len(cases) == len(set(cases)) == 9
base = ROOT/'research/walk-gap-pilot-v1'
base.mkdir()
wrappers = {}
for seed in [0, 1, 2]:
    path = base/f'walk-seed-{seed}'
    path.write_text('#!/bin/sh\nexec '+shlex.quote(str(binary))+' --walk-seed '+str(seed)+' --walk-restart-steps 10000 "$@"\n')
    path.chmod(0o755)
    wrappers[f'native-walk-{seed}'] = path
output = ROOT/'results/local-walk-gap-pilot-v1'
assert not output.exists()
methods = ['native-batched', *wrappers]
command = [sys.executable,'scripts/benchmark_smpt_classic.py','--corpus','benchmarks/application-portfolio-comparison-v1',
           '--binary',str(binary),'--native-tool','native-batched','portfolio-batched',str(binary)]
for name,path in wrappers.items():command += ['--native-tool',name,'walk',str(path)]
command += ['--methods',*methods,'--buffer-agglomeration-method','native-batched',
            '--rust-original','--bounded-validation','--validation-seconds','60',
            '--validation-memory-mib','2048','--validation-response-mib','64','--validation-dag-work','200000000',
            '--track-resources','--memory-mib','2048','--max-states','2000000','--outer-grace','0',
            '--seconds','5','--repeat','1','--order-seed','2026092809',
            '--filter','^('+ '|'.join(map(re.escape,cases))+')$','--output',str(output)]
donor=json.loads((ROOT/'results/local-tokenring-positive-diagnostic-v1/environment.json').read_text())
paths=[ROOT/'scripts'/name for name in donor['script_sha256']]
paths += list(wrappers.values())+[Path(__file__),binary,binary.with_name('provenance.json'),ROOT/'research/application-positive-gaps-v1.json']
manifest_path=ROOT/'benchmarks/application-portfolio-comparison-v1/manifest.json'
manifest=json.loads(manifest_path.read_text());paths.append(manifest_path)
for query in manifest['queries']:
    if query['name'] in cases:
        paths += [manifest_path.parent/query[key] for key in ['pnml','xml','net','property']]
        paths += [manifest_path.parent/branch['path'] for branch in query['branches']]
pins={str(path.relative_to(ROOT)):sha(path) for path in paths}
plan=dict(format='walk-gap-pilot-v1',cases=cases,rows=36,methods=methods,seeds=[0,1,2],restart_steps=10000,
          command=command,file_sha256=pins,binary_sha256=provenance['binary_sha256'],source_sha256=provenance['source_sha256'],
          scope='All nine competitor-only positive gaps from the640-import/656-slot parent. Fixed seeds before outcomes; report each seed, no best-seed replacement. Same frozen binary for walk and baseline; hashed seed wrappers additionally execute the pinned underlying binary.5s original-input solver budget, separate60s independent original-input check,2GiB,2Mstates or total attempted firings, one repeat. Local mechanism diagnostic, not Linux competitor timing or held-out evidence.')
with (base/'plan.json').open('x') as stream:json.dump(plan,stream,indent=2);stream.write('\n')
assert all(sha(ROOT/name)==digest for name,digest in pins.items())
env=dict(os.environ)
for name in ['VASS_PORTFOLIO_PROFILE','VASS_RELAXED_PROFILE']:env.pop(name,None)
sys.exit(subprocess.run(command,cwd=ROOT,env=env).returncode)
