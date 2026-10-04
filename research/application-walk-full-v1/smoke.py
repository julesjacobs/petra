"""Explicit bounded remote capability smoke or read-only audit of fetched evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
BINARY = 'results/linux-solver-walk-sparse-v2/vass-reach'
OUTPUT = 'results/linux-application-walk-full-v1-smoke'
METHODS = {'native-walk':'portfolio-walk', 'native-batched':'portfolio-batched'}
QUERIES = ['CircadianClock-PT-100000__RC12', 'NoC3x3-PT-8B__RC12',
           'IOTPpurchase-PT-C05M04P03D02__RC13', 'TokenRing-PT-020__RC09']
CORPUS = 'benchmarks/application-portfolio-comparison-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def remote(command, **kwargs):
    return subprocess.run(['tailscale','ssh',HOST,f'cd {REMOTE} && '+command], check=True, **kwargs)


def run():
    required = json.loads((ROOT/'results/runner-repeated-search-v2/files-sha256.json').read_text())
    required[BINARY] = sha(ROOT/BINARY)
    required[CORPUS+'/manifest.json'] = sha(ROOT/CORPUS/'manifest.json')
    manifest = json.loads((ROOT/CORPUS/'manifest.json').read_text())
    selected = [q for q in manifest['queries'] if q['name'] in QUERIES]
    assert len(selected)==4
    for q in selected:
        for key in ['pnml','xml','net','property']:
            path=(ROOT/CORPUS/q[key]).resolve()
            assert sha(path)==q[key+'_sha256']
            required[str(path.relative_to(ROOT))]=q[key+'_sha256']
        for b in q['branches']:
            path=(ROOT/CORPUS/b['path']).resolve()
            assert sha(path)==b['sha256']
            required[str(path.relative_to(ROOT))]=b['sha256']
    command=['vendor/venv/bin/python','-u','scripts/benchmark_smpt_classic.py',
             '--corpus',CORPUS,'--binary',BINARY]
    for label,engine in METHODS.items():
        command+=['--native-tool',label,engine,BINARY]
    command+=['--methods',*METHODS]
    for label in METHODS:command+=['--buffer-agglomeration-method',label]
    command+=['--rust-original','--smpt-original','--bounded-validation',
              '--validation-seconds','60','--validation-memory-mib','2048',
              '--validation-response-mib','64','--validation-dag-work','200000000',
              '--linux-cpus','8','--perf','--memory-mib','2048','--max-states','2000000',
              '--outer-grace','0','--seconds','5','--repeat','1','--order-seed','20261115',
              '--filter','^('+'|'.join(QUERIES)+')$','--output',OUTPUT]
    plan=dict(command=command,queries=QUERIES,methods=METHODS,expected_rows=8,
              required_file_sha256=required,binary_sha256=required[BINARY],
              scope='Bounded capability smoke, not competitive timings. Full cohort not launched.')
    with (HERE/'smoke-plan.json').open('x') as stream:
        json.dump(plan,stream,indent=2);stream.write('\n')
    code=f'''
import hashlib
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
assert not Path({OUTPUT!r}).exists()
for name,expected in {required!r}.items():
    with Path(name).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print('Frozen candidate,22runner files and4original queries verified',flush=True)
'''
    remote('vendor/venv/bin/python -c '+shlex.quote(code))
    with (HERE/'smoke-run.log').open('w') as stream:
        completed=remote('unset VASS_PORTFOLIO_PROFILE VASS_RELAXED_PROFILE VASS_RAW_PHASE_DIAGNOSTICS VASS_RAW_NEGATIVE_DIAGNOSTICS && '+shlex.join(command),stdout=stream,stderr=subprocess.STDOUT)
    (HERE/'smoke-completion.json').write_text(json.dumps(dict(terminal=True,exit_code=completed.returncode,output=OUTPUT),indent=2)+'\n')
    archive=HERE/'smoke-artifacts.tar.gz'
    with archive.open('wb') as stream:
        remote('tar -czf - '+shlex.quote(OUTPUT),stdout=stream)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            path=Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts and path.is_relative_to(OUTPUT)
            assert member.isfile() or member.isdir()
            assert not (ROOT/path).exists()
        tar.extractall(ROOT,filter='data')
    print(json.dumps(dict(terminal=True,rows_expected=8,retrieved=str(archive),sha256=sha(archive))))


def audit():
    out=ROOT/OUTPUT
    plan=json.loads((HERE/'smoke-plan.json').read_text())
    env=json.loads((out/'environment.json').read_text())
    rows=[json.loads(line) for line in (out/'runs.jsonl').read_text().splitlines()]
    assert json.loads((HERE/'smoke-completion.json').read_text())['terminal'] is True
    assert Counter((r['query'],r['method'],r['repeat']) for r in rows)==Counter((q,m,0) for q in QUERIES for m in METHODS)
    assert env['methods']==list(METHODS) and env['buffer_agglomeration_methods']==list(METHODS)
    assert env['seconds']==5 and env['linux_cpus']==[8] and env['memory_mib']==2048 and env['perf']
    assert env['outer_grace']==0 and env['repeat']==1 and env['max_states']==2000000
    assert env['rust_original'] and env['bounded_validation']['included_in_solver_timing'] is False
    assert env['bounded_validation']['seconds']==60 and env['bounded_validation']['response_mib']==64
    runner=json.loads((ROOT/'results/runner-repeated-search-v2/files-sha256.json').read_text())
    runtime={n:h for n,h in runner.items() if n!='scripts/verifypn_runner.py'}
    assert set(env['script_sha256'])=={Path(n).name for n in runtime}
    for name,digest in runtime.items():
        assert sha(out/'runner-source'/Path(name).name)==env['script_sha256'][Path(name).name]==digest
    checks=[]
    for row in rows:
        tool=env['native_tools'][row['method']]
        assert tool==dict(engine=METHODS[row['method']],binary=REMOTE+'/'+BINARY,binary_sha256=plan['binary_sha256'])
        assert row['command'][0]==tool['binary'] and '--buffer-agglomeration' in row['command']
        assert row['resources']['cpus']==[8] and row['resources']['memory_limit_bytes']==2048*1024**2
        assert row['resources']['perf_enabled'] and row['resources']['runner']=='linux-systemd-user'
        if row['verdict'] in ['reachable','unreachable']:
            assert row['exit_code']==0 and not row['outer_timeout'] and row['wall_seconds']<=5
            assert not row['resources']['memory_limit_exceeded']
            response=json.loads((out/f"{row['query']}.{row['method']}.0.rust-original.json.validation-response.json").read_text())
            for key in ['verdict','property_truth','branches','independent_checks','translation_check']:
                assert response[key]==row[key]
            assert row['validation']['exit_code']==0 and not row['validation']['outer_timeout']
            assert not row['validation']['resources']['memory_limit_exceeded']
            assert row['independent_checks'] and all(c.startswith('python-') for c in row['independent_checks'])
            checks+=row['independent_checks']
    matrix={(r['query'],r['method']):r for r in rows}
    for method in METHODS:
        assert matrix[('NoC3x3-PT-8B__RC12',method)]['verdict']=='reachable'
        assert matrix[('IOTPpurchase-PT-C05M04P03D02__RC13',method)]['verdict']=='unreachable'
        assert matrix[('IOTPpurchase-PT-C05M04P03D02__RC13',method)]['independent_checks']==['python-buffer-agglomeration']
    assert matrix[('TokenRing-PT-020__RC09','native-walk')]['verdict']=='reachable'
    report=dict(status='passed',binary_sha256=plan['binary_sha256'],rows=8,
                saved_native_check_counts=dict(Counter(checks)),preflight_runner_files=22,snapshotted_runtime_files=21,
                solved_by_method={m:sum(r['method']==m and r['verdict'] in ['reachable','unreachable'] for r in rows) for m in METHODS},
                artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                plan_sha256=sha(HERE/'smoke-plan.json'),
                scope='Saved bounded original-input capability evidence reconciled; no proof checker rerun in this audit. Not competitive timing.')
    (HERE/'smoke-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='artifact_sha256'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['run','audit'])
    args=parser.parse_args()
    run() if args.action=='run' else audit()
