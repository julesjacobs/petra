"""Fetch historical-survivor results after both active measurements terminate."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / 'research/hard-survivors-current-v2'
FOLDER = 'results/linux-hard-survivors-current-v2'


def main():
    terminal = json.loads((EXPERIMENT / 'terminal.json').read_text())
    if terminal['exit_code'] != 0:
        observation_path = ROOT / terminal['observation']
        assert hashlib.sha256(observation_path.read_bytes()).hexdigest() == terminal['observation_sha256']
        observation = json.loads(observation_path.read_text())
        assert terminal['remote_stopped'] and not any(observation[k] for k in ['drivers', 'workloads', 'benchmark_units'])
    assert json.loads((ROOT / 'research/signed-threshold-full-v1-terminal.json').read_text())['exit_code'] == 0
    sys.path.insert(0, str(ROOT / 'scripts'))
    from process_runner import workspace_workloads
    assert not workspace_workloads(ROOT)
    plan_path = EXPERIMENT / 'plan.json'
    plan = json.loads(plan_path.read_text())
    receipt = json.loads((EXPERIMENT / 'execution.json').read_text())
    assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == receipt['plan_sha256']
    assert plan['output'] == FOLDER and plan['expected_rows'] == 40
    archive = EXPERIMENT / 'results.tar.gz'
    assert not archive.exists() and not (ROOT / FOLDER).exists()
    code = '''import sys, tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    archive.add('results/linux-hard-survivors-current-v2', arcname='results/linux-hard-survivors-current-v2')
'''
    command = ['tailscale', 'ssh', 'jules@jules-b650-aorus-elite-ax-v2',
               'cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c ' + shlex.quote(code)]
    with archive.open('xb') as output:
        subprocess.run(command, stdout=output, check=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert member.isdir() or member.isfile()
            assert path == Path(FOLDER) or path.is_relative_to(FOLDER)
        source.extractall(ROOT, filter='data')
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    collection = dict(status='collected', archive=str(archive.relative_to(ROOT)),
                      sha256=digest, bytes=archive.stat().st_size,
                      files=sum(p.is_file() for p in (ROOT / FOLDER).rglob('*')),
                      rows=len((ROOT / FOLDER / 'runs.jsonl').read_text().splitlines()),
                      scope='Transfer complete; full artifact audit still required.')
    (EXPERIMENT / 'collection.json').write_text(json.dumps(collection, indent=2) + '\n')
    print(json.dumps(collection))


if __name__ == '__main__':
    main()
