"""Install a pinned private MiniZinc bundle and record dependency/SMPT CP smoke evidence."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile

ROOT = Path('/home/jules/experiments/pvass-publication')
INSTALL = ROOT/'vendor/minizinc-linux-v1'
ARTIFACT = ROOT/'research/smpt-minizinc-repair-v1'
NAME = 'MiniZincIDE-2.10.1-x86_64-linux-gnu'
URL = 'https://github.com/MiniZinc/MiniZincIDE/releases/download/2.10.1/'+NAME+'.tgz'
ARCHIVE_SHA = 'b63dd88491d47b05d0eb0ff4aa1112d1e6f77292c023800b20b98851458ce01c'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(test, message):
    if not test:
        raise RuntimeError(message)


require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'Expected Linux x86_64')
ARTIFACT.mkdir(exist_ok=False)
INSTALL.mkdir(exist_ok=True)
archive = INSTALL/(NAME+'.tgz')
if not archive.exists():
    subprocess.run(['curl', '-fL', '--retry', '2', '--max-time', '300', URL, '-o', str(archive)], check=True)
require(digest(archive) == ARCHIVE_SHA, 'Archive hash mismatch')
bundle = INSTALL/NAME
if not bundle.exists():
    with tarfile.open(archive) as stream:
        stream.extractall(INSTALL, filter='data')
records = {}


def run(label, command, environment=None, seconds=30):
    result = subprocess.run(list(map(str, command)), cwd=ROOT, env=environment,
                            capture_output=True, text=True, timeout=seconds)
    (ARTIFACT/(label+'.stdout')).write_text(result.stdout)
    (ARTIFACT/(label+'.stderr')).write_text(result.stderr)
    records[label] = dict(command=list(map(str, command)), exit_code=result.returncode,
                          stdout_sha256=digest(ARTIFACT/(label+'.stdout')),
                          stderr_sha256=digest(ARTIFACT/(label+'.stderr')))
    require(result.returncode == 0, label+' failed: '+result.stderr[-2000:])
    return result.stdout


env = os.environ.copy()
env['PATH'] = ':'.join(map(str, [bundle/'bin', ROOT/'vendor/venv/bin',
                                ROOT/'vendor/tina-linux/tina-4.0.0/bin',
                                ROOT/'vendor/4ti2-install/bin']))+':'+env['PATH']
env['PYTHONPATH'] = str(ROOT/'vendor/SMPT-portable')
for key in ('MZN_SOLVER_PATH','MZN_STDLIB_DIR','MZN_CONFIG_FILE'):
    require(not env.get(key), 'Unexpected inherited '+key)
minizinc = bundle/'bin/minizinc'
version = run('version', [minizinc, '--version'], env)
solvers = run('solvers', [minizinc, '--solvers'], env)
configs = json.loads(run('config-dirs', [minizinc, '--config-dirs'], env))
require('Gecode 6.4.0 (org.gecode.gecode, default solver' in solvers, 'Wrong default backend')
for label, constraint in [('sat', 'x = 1'), ('unsat', 'x = 2')]:
    model = ARTIFACT/(label+'.mzn')
    model.write_text('var 0..1: x;\nconstraint '+constraint+';\nsolve satisfy;\n')
    output = run(label, [minizinc, model], env)
    require(('x = 1;' in output and '----------' in output) if label=='sat' else '=====UNSATISFIABLE=====' in output, 'Unexpected '+label+' output')
net = ARTIFACT/'model.net'
net.write_text('net {cp_smoke}\npl {p} (1)\npl {q} (0)\ntr {move} {p} -> {q}\n')
for label, bound in [('smpt-cp-sat', 1), ('smpt-cp-unsat', 2)]:
    xml = ARTIFACT/(label+'.xml')
    xml.write_text('<property-set><property><id>'+label+'</id><description>MiniZinc CP smoke</description><formula><exists-path><finally><integer-le><integer-constant>'+str(bound)+'</integer-constant><tokens-count><place>q</place></tokens-count></integer-le></finally></exists-path></formula></property></property-set>\n')
    output = run(label, [ROOT/'vendor/venv/bin/python', '-m', 'smpt', '--net', net,
                        '--xml', xml, '--auto-reduce', '--methods', 'CP', '--timeout', '10',
                        '--show-techniques', '--show-model', '--debug'], env)
    expected = 'TRUE' if label.endswith('-sat') else 'FALSE'
    require('FORMULA '+label+' '+expected in output, 'Wrong SMPT verdict:'+label)
    require('CONSTRAINT_PROGRAMMING' in output and 'solve satisfy;' in output, 'CP capability not exercised:'+label)

bundle_files = {str(p.relative_to(bundle)):digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()}
(ARTIFACT/'bundle-files-sha256.json').write_text(json.dumps(bundle_files, indent=2)+'\n')
dependencies = {}
for executable in (minizinc, bundle/'bin/fzn-gecode'):
    output = run('ldd-'+executable.name, ['ldd', executable])
    require('not found' not in output, 'Missing shared library')
    for line in output.splitlines():
        match = re.search(r'(?:=> )?(/[^ ]+) \(', line)
        if match:
            path = Path(match.group(1))
            dependencies[str(path)] = dict(resolved=str(path.resolve()),sha256=digest(path))
configuration_files = {}
for path in (Path(configs['globalConfigFile']), Path(configs['userConfigFile'])):
    configuration_files[str(path)] = dict(exists=path.exists(),sha256=digest(path) if path.is_file() else None)
for folder in (Path(configs['userSolverConfigDir']),Path('/usr/local/share/minizinc/solvers'),Path('/usr/share/minizinc/solvers'),Path('/home/linuxbrew/.linuxbrew/share/minizinc/solvers')):
    configuration_files[str(folder)] = dict(exists=folder.exists(),files={str(p):digest(p) for p in sorted(folder.rglob('*')) if p.is_file()} if folder.exists() else {})
smpt_sources = {str(p.relative_to(ROOT/'vendor/SMPT-portable')):digest(p) for p in sorted((ROOT/'vendor/SMPT-portable/smpt').rglob('*.py'))}
metadata = dict(status='smoke-verified',scope='Dependency capability repair only; no benchmark measurements or changes to old frozen experiments.',
                host=platform.node(),platform=platform.platform(),install=str(INSTALL),bundle=str(bundle),
                upstream_url=URL,archive_sha256=ARCHIVE_SHA,version=version.strip(),
                default_solver='org.gecode.gecode',default_solver_version='6.4.0',
                recommended_tool_bin=str(bundle/'bin'),configuration_files=configuration_files,
                inherited_minizinc_overrides={k:env.get(k) for k in ('MZN_SOLVER_PATH','MZN_STDLIB_DIR','MZN_CONFIG_FILE')},
                shared_libraries=dependencies,smpt_sources=smpt_sources,
                tool_identities={str(p):digest(p) for p in (minizinc,bundle/'bin/fzn-gecode',ROOT/'vendor/venv/bin/python',ROOT/'vendor/tina-linux/tina-4.0.0/bin/reduce')},
                records=records,bundle_manifest_sha256=digest(ARTIFACT/'bundle-files-sha256.json'),
                script_sha256=digest(__file__),
                smoke_inputs={str(p.relative_to(ARTIFACT)):digest(p) for p in sorted(ARTIFACT.iterdir()) if p.suffix in ('.mzn','.net','.xml')})
(ARTIFACT/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(dict(status=metadata['status'],default_solver=metadata['default_solver'],smoke_records=list(records),bundle_files=len(bundle_files)),indent=2))
