#!/usr/bin/env python3
"""Independently replay every native positive from a complete FastForward run."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from analyze_original_comparison import analyze


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = (args.corpus / 'manifest.json', args.results / 'environment.json',
             args.results / 'runs.jsonl')
    manifest, environment = [json.loads(path.read_text()) for path in paths[:2]]
    rows = [json.loads(line) for line in paths[2].read_text().splitlines()]
    if digest(paths[0]) != environment['manifest_sha256']:
        raise ValueError('Measured corpus manifest changed')
    analyze(manifest, environment, rows, group_by='suite')
    positives = [row for row in rows if row['method'] in environment['native_tools']
                 and row['verdict'] == 'reachable']
    if any(row.get('input_mode') != 'rust-original-v1' for row in positives):
        raise ValueError('Source replay expects saved Rust original-input outputs')
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = args.output / 'scripts'
    snapshot.mkdir()
    checker_sources = {}
    for name in ('replay_fastforward_results.py', 'analyze_original_comparison.py',
                 'check_fastforward_source.py', 'fastforward_source_checker.py', 'process_runner.py'):
        path = Path(__file__).with_name(name)
        checker_sources[name] = digest(path)
        shutil.copyfile(path, snapshot / name)
    provenance = dict(
        scope='Additional original-LoLA positive-witness validation only; no solver timings or '
              'negative certification. All native positives in the complete measured matrix are selected.',
        expected_positives=len(positives),
        sources={str(p): digest(p) for p in paths}, checker_sources=checker_sources)
    (args.output / 'plan.json').write_text(json.dumps(provenance, indent=2) + '\n')
    counts = Counter()
    with (args.output / 'runs.jsonl').open('w') as records:
        for row in positives:
            stem = f'{row["query"]}.{row["method"]}.{row["repeat"]}'
            # Filenames come from the measured matrix; reject path components.
            if Path(stem).name != stem:
                raise ValueError('Invalid artifact identity')
            answer = (args.results / (stem + '.rust-original.json')).resolve()
            request = dict(corpus=str(args.corpus.resolve()), source=str(args.source.resolve()),
                           query=row['query'], answer=str(answer),
                           seconds=30, memory_mib=2048, manifest_sha256=environment['manifest_sha256'])
            request_path = args.output / (stem + '.request.json')
            response_path = args.output / (stem + '.response.json')
            request_path.write_text(json.dumps(request) + '\n')
            command = [sys.executable, str(Path(__file__).with_name('check_fastforward_source.py')),
                       '--request', str(request_path), '--response', str(response_path)]
            with (args.output / (stem + '.driver.log')).open('w') as log:
                completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            if completed.returncode or not response_path.exists():
                result = dict(verdict='error', validation_failure='source-replay-driver-failure')
            else:
                result = json.loads(response_path.read_text())
            accepted = (result.get('verdict') == 'reachable'
                        and result.get('independent_check') == 'python-original-lola-witness')
            status = 'verified' if accepted else 'unknown' if result.get('verdict') == 'unknown' else 'error'
            counts[status] += 1
            record = dict(query=row['query'], method=row['method'], repeat=row['repeat'],
                          status=status, response=str(response_path),
                          answer_sha256=digest(answer) if answer.is_file() else None)
            records.write(json.dumps(record) + '\n')
            records.flush()
            print(stem, status, flush=True)
    (args.output / 'report.json').write_text(json.dumps(
        dict(provenance, completed=sum(counts.values()), counts=dict(counts)), indent=2) + '\n')
    if counts['unknown'] or counts['error']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
