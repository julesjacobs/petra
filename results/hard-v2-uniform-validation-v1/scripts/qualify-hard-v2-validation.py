"""Recheck every recorded native validation failure without changing measured rows."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_original_comparison import analyze
from bounded_validation import run_validation
from process_runner import workspace_workloads


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def main():
    plan_path = ROOT / 'research/hard-v2-uniform-validation-plan.json'
    plan = json.loads(plan_path.read_text())
    measured = ROOT / plan['source_run']
    corpus = ROOT / plan['corpus']
    source_paths = [corpus / 'manifest.json', measured / 'environment.json', measured / 'runs.jsonl']
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in source_paths}
    manifest, environment = [json.loads(path.read_text()) for path in source_paths[:2]]
    rows = [json.loads(line) for line in source_paths[2].read_text().splitlines()]
    if len(rows) != plan['expected_source_rows'] or len(environment['property_order']) != plan['expected_source_properties']:
        raise ValueError('Source run is incomplete')
    if source_hashes[str(source_paths[0].relative_to(ROOT))] != plan['manifest_sha256'] or environment['manifest_sha256'] != plan['manifest_sha256']:
        raise ValueError('Measured manifest identity differs')
    analyze(manifest, environment, rows, 'suite')
    if not set(plan['native_methods']) <= set(environment['native_tools']):
        raise ValueError('Native method identities differ')
    if workspace_workloads(ROOT):
        raise RuntimeError('Wait for other local workloads to finish')
    selected = [row for row in rows if row['method'] in plan['native_methods']
                and (row.get('failure_stage') == 'validation' or row.get('validation_failure'))]
    if any(row.get('input_mode') != 'rust-original-v1' for row in selected):
        raise ValueError('Only original-input Rust answers can be qualified here')
    queries = {query['name']: query for query in manifest['queries']}
    output = ROOT / plan['output']
    output.mkdir(exist_ok=False)
    shutil.copyfile(plan_path, output / 'plan.json')
    snapshot = output / 'scripts'
    snapshot.mkdir()
    sources = {}
    for name in environment['script_sha256']:
        path = ROOT / 'scripts' / name
        if not path.exists():
            path = ROOT / name
        sources[name] = digest(path)
        shutil.copyfile(path, snapshot / name)
    shutil.copyfile(__file__, snapshot / Path(__file__).name)
    sources[Path(__file__).name] = digest(Path(__file__))
    provenance = dict(source_hashes=source_hashes, checker_source_sha256=sources,
                      selected=[dict(query=r['query'], method=r['method'], repeat=r['repeat']) for r in selected],
                      selected_rows=len(selected), original_rows=len(rows), original_results_unchanged=True,
                      scope=plan['reporting'])
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    limits = plan['limits']
    args = argparse.Namespace(native_python=ROOT / 'vendor/venv/bin/python',
                              validation_seconds=limits['seconds'],
                              validation_memory_mib=limits['memory_mib'],
                              validation_response_mib=limits['response_mib'],
                              validation_dag_work=limits['dag_max_work'])
    results = []
    with (output / 'runs.jsonl').open('w') as records:
        for row in selected:
            stem = f'{row["query"]}.{row["method"]}.{row["repeat"]}'
            if Path(stem).name != stem:
                raise ValueError('Invalid artifact name')
            original_answer = measured / (stem + '.rust-original.json')
            answer = output / original_answer.name
            result = dict(query=row['query'], method=row['method'], repeat=row['repeat'],
                          original_verdict=row['verdict'], original_validation=row.get('validation'),
                          original_error=row.get('error'), original_validation_failure=row.get('validation_failure'))
            if not original_answer.is_file():
                result.update(verdict='unknown', validation_failure='missing-saved-answer')
            else:
                before = digest(original_answer)
                shutil.copyfile(original_answer, answer)
                if digest(answer) != before or digest(original_answer) != before:
                    raise ValueError('Answer changed while copying')
                result['answer_sha256'] = before
                result['answer_bytes'] = answer.stat().st_size
                qualified = run_validation(queries[row['query']], corpus, output, answer,
                                           row['exit_code'], args, mode='rust-original-v1',
                                           outer_timeout=row['outer_timeout'])
                result.update(qualified)
                other_verdicts = {other['verdict'] for other in rows
                                  if other['query'] == row['query']
                                  and other['verdict'] in {'reachable', 'unreachable'}}
                result['disagrees_with_measured_definitive'] = bool(
                    result['verdict'] in {'reachable', 'unreachable'}
                    and other_verdicts - {result['verdict']})
            results.append(result)
            records.write(json.dumps(result) + '\n')
            records.flush()
            print(stem, result['verdict'], result.get('validation_failure', ''), flush=True)
    for path, expected in source_hashes.items():
        if digest(ROOT / path) != expected:
            raise ValueError('Original source metadata/results changed')
    report = dict(provenance, completed=len(results),
                  qualified_definitive=sum(r['verdict'] in {'reachable', 'unreachable'} for r in results),
                  unresolved=[r for r in results if r['verdict'] not in {'reachable', 'unreachable'}],
                  disagreements=[r for r in results if r.get('disagrees_with_measured_definitive')])
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    if report['disagreements']:
        raise SystemExit('Qualified answer disagrees with a measured definitive result; investigate')


if __name__ == '__main__':
    main()
