#!/usr/bin/env python3
"""Verify the registered local experiment; run only with --execute."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'research/raw-hardness-requalification-v2-plan.json'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def distribution_identity(name):
    dist = importlib.metadata.distribution(name)
    files = {str(f): digest(dist.locate_file(f)) for f in dist.files
             if not str(f).endswith('.pyc') and '__pycache__' not in str(f)}
    return {'version': dist.version, 'files': len(files),
            'tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_pins(plan):
    require(str(ROOT) == plan['workspace'], 'Workspace moved; register a new plan')
    for path, expected in plan['file_sha256'].items():
        require(digest(ROOT / path) == expected, f'Pinned file changed: {path}')
    py = plan['python']
    require(sys.version == py['version'] and str(Path(sys.executable).resolve()) == py['resolved'],
            'Use the registered Python interpreter')
    require(digest(py['resolved']) == py['sha256'], 'Python binary changed')
    require(platform.platform() == plan['platform'], 'Platform changed')
    for name, expected in plan['distributions'].items():
        require(distribution_identity(name) == expected, f'Dependency changed: {name}')


def verify_result(plan, run):
    output = ROOT / run['output']
    cohort = plan['cohorts'][run['cohort']]
    rows = [json.loads(line) for line in (output / 'runs.jsonl').read_text().splitlines()]
    keys = [(r['query'], r['method'], r['repeat']) for r in rows]
    expected = {(s['name'], method, rep) for s in cohort['sources']
                for method in plan['methods'] for rep in range(plan['limits']['repeat'])}
    require(len(keys) == len(expected) and set(keys) == expected, 'Missing/duplicate result rows')
    unavailable = {s['name'] for s in cohort['sources'] if s['export_status'] != 'exported-unvalidated'}
    for row in rows:
        if row['query'] in unavailable:
            require(row['verdict'] == 'not-run' and row['status'] == 'export-unavailable',
                    'Export failure lost from denominator')
    environment = json.loads((output / 'environment.json').read_text())
    require(environment['binary_sha256'] == plan['configurations'][run['configuration']]['binary_sha256'],
            'Frozen result binary mismatch')
    require(environment['selected_sources'] == [s['name'] for s in cohort['sources']], 'Selection changed')
    for name, expected_hash in environment['runner_sha256'].items():
        require(expected_hash == plan['file_sha256']['scripts/' + name], 'Runner snapshot drift')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Run both registered cohorts sequentially')
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    check_pins(plan)
    for run in plan['runs']:
        require(not (ROOT / run['output']).exists(), f"Output already exists: {run['output']}")
    print('Pins verified. 28 source slots; 24 unique programs; 4 bridges; n6 pairlocked export failure retained.', flush=True)
    if not args.execute:
        print('Preflight only; no solver execution. Add --execute to launch when local diagnostics are idle.')
        return
    sys.path.insert(0, str(ROOT / 'scripts'))
    from process_runner import workspace_workloads
    lock = ROOT / 'results/raw-hardness-requalification-v2.lock'
    lock.parent.mkdir(exist_ok=True)
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, (str(os.getpid()) + '\n').encode())
        os.close(fd)
        for run in plan['runs']:
            check_pins(plan)
            require(not workspace_workloads(ROOT), 'Concurrent solver/build workload; retry after it finishes')
            print('Starting ' + run['output'], flush=True)
            subprocess.run(run['command'], cwd=ROOT, check=True)
            check_pins(plan)
            verify_result(plan, run)
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
