"""Bounded Rust/Python importer agreement check for the complete acquired cohort."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import run, workspace_workloads

CORPUS = ROOT / 'benchmarks/general-development-v3'
OUT = ROOT / 'research/general-development-v3-imports'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert not workspace_workloads(ROOT)
    assert json.loads((ROOT / 'research/general-development-v3-collection-terminal.json').read_text())['exit_code'] == 0
    audit_path = ROOT / 'research/general-development-v3-collection-audit.json'
    audit = json.loads(audit_path.read_text())
    assert audit['status'] == 'passed'
    manifest_path = CORPUS / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert sha(manifest_path) == audit['manifest_sha256']
    assert len(manifest['queries']) == 176
    inputs = {}
    for query in manifest['queries']:
        if query['status'] != 'imported':
            continue
        for relative, digest in [(query[k], query[k + '_sha256']) for k in ['pnml', 'xml']] + [
                (b['path'], b['sha256']) for b in query['branches']]:
            path = (CORPUS / relative).resolve()
            assert path.is_relative_to(CORPUS)
            if path not in inputs:
                inputs[path] = sha(path)
            assert inputs[path] == digest
    OUT.mkdir()
    helper = OUT / 'check_original_import'
    shutil.copyfile(ROOT / 'target/release/examples/check_original_import', helper)
    helper.chmod(0o755)
    sources = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock',
               ROOT / 'examples/check_original_import.rs', Path(__file__).resolve(),
               ROOT / 'scripts/process_runner.py', *sorted((ROOT / 'src').glob('*.rs'))]
    plan = dict(queries=[q['name'] for q in manifest['queries']], planned_slots=176,
                seconds=60, memory_bytes=2048 * 1024**2, helper_sha256=sha(helper),
                manifest_sha256=sha(manifest_path), collection_audit_sha256=sha(audit_path),
                source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
                input_sha256={str(p.relative_to(ROOT)): h for p, h in inputs.items()},
                scope='Complete Rust original-input parser versus collected Python canonical branches; '
                      'strict field/order equality, all branches and polarity. No solver, reduction or '
                      'difficulty measurement. Per-query process-tree wall and sampled local memory limits.')
    save(OUT / 'plan.json', plan)
    records = []
    with (OUT / 'runs.jsonl').open('x') as stream:
        for query in manifest['queries']:
            record = dict(query=query['name'], collection_status=query['status'])
            if query['status'] != 'imported':
                record.update(status='unavailable', error=query.get('error'))
            else:
                assert not workspace_workloads(ROOT)
                assert sha(helper) == plan['helper_sha256']
                log = OUT / (query['name'] + '.json')
                command = [str(helper), str(CORPUS), query['name']]
                wall, code, expired, resources = run(command, ROOT, plan['seconds'], log, plan['memory_bytes'])
                record.update(command=command, exit_code=code, outer_timeout=expired,
                              wall_seconds=wall, resources=resources, status='error')
                if resources.get('memory_limit_exceeded'):
                    record['status'] = 'memory-limit'
                elif expired:
                    record['status'] = 'timeout'
                elif code == 0:
                    answer = json.loads(log.read_text())
                    if answer == dict(status='matched', query=query['name'], property_id=query['property_id'],
                                      kind=query['kind'], branches=len(query['branches'])):
                        record.update(status='matched', branches=answer['branches'])
                record['log_sha256'] = sha(log)
            stream.write(json.dumps(record) + '\n')
            stream.flush()
            records.append(record)
            print(query['name'], record['status'], flush=True)
    unchanged = all(sha(path) == digest for path, digest in inputs.items())
    matched = sum(r['status'] == 'matched' for r in records)
    passed = unchanged and all(r['status'] in ['matched', 'unavailable'] for r in records)
    save(OUT / 'summary.json', dict(status='passed' if passed else 'failed', planned_slots=176,
         imported=sum(q['status'] == 'imported' for q in manifest['queries']), matched=matched,
         inputs_unchanged=unchanged, failures=[r for r in records if r['status'] != 'matched'],
         plan_sha256=sha(OUT / 'plan.json'), rows_sha256=sha(OUT / 'runs.jsonl'), scope=plan['scope']))
    return int(not passed)


if __name__ == '__main__':
    sys.exit(main())
