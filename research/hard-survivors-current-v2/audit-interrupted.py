"""Audit retained interrupted rows without altering the frozen full-matrix auditor."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PIN = '97537ae48199a6d419bea14810050c55e581ead9bbe9b129a2b51d97fdca0651'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    plan_path = HERE / 'plan.json'
    plan = read(plan_path)
    results = ROOT / plan['output']
    helper = ROOT / 'research/audit-linux-application-expansion-v2.py'
    spec = importlib.util.spec_from_file_location('full_matrix_auditor', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    full = module.safe_audit(ROOT, plan_path, results)
    (HERE / 'interrupted-full-auditor-report.json').write_text(json.dumps(full, indent=2) + '\n')
    issues = []
    def check(value, message):
        if not value:
            issues.append(message)
    check(sha(plan_path) == PIN, 'Frozen plan identity differs')
    terminal, stopped, collection = [read(HERE / (name + '.json')) for name in ('terminal', 'stopped-observation', 'collection')]
    check(terminal['exit_code'] == 255 and terminal['remote_stopped'] is True,
          'Missing recorded transport termination and stopped observation')
    check(not stopped['drivers'] and not stopped['workloads'] and not stopped['benchmark_units'],
          'Stopped observation contains live work')
    check(sha(HERE / 'stopped-observation.json') == terminal['observation_sha256'], 'Stopped observation identity differs')
    check(sha(ROOT / collection['archive']) == collection['sha256'], 'Fetched archive identity differs')
    env = read(results / 'environment.json')
    manifest = read(ROOT / plan['corpus'] / 'manifest.json')
    order = [q['name'] for q in manifest['queries']]
    random.Random(plan['order_seed']).shuffle(order)
    check(order == env['property_order'], 'Environment property order differs from frozen schedule')
    check(env['methods'] == list(plan['methods']), 'Environment method order differs from frozen plan')
    schedule = []
    for index, name in enumerate(order):
        methods = list(plan['methods'])
        for repeat in range(plan['repeat']):
            rotated = methods if repeat % 2 == 0 else methods[::-1]
            offset = (index + repeat) % len(rotated)
            schedule += [(name, method, repeat) for method in rotated[offset:] + rotated[:offset]]
    rows = full['full_rows']
    observed = [(r['query'], r['method'], r['repeat']) for r in rows]
    check(len(observed) == len(set(observed)) == 27, 'Expected 27 distinct retained rows')
    check(observed == schedule[:27], 'Retained rows are not the first 27 frozen scheduling cells')
    check(len(schedule) == plan['expected_rows'] == 40, 'Frozen denominator differs')
    check(terminal['rows'] == collection['rows'] == stopped['rows'] == len(rows), 'Receipts disagree on retained rows')
    expected_incomplete = {
        'Registered row denominator differs',
        'Incomplete, duplicated or unexpected query/method/repeat matrix',
        'Recorded row order differs from frozen scheduling',
        'Complete difficulty analysis unavailable: Incomplete or unexpected matrix: 13 missing, 0 extra',
    }
    ordinary = full.get('audit_issues', [])
    unexpected = [issue for issue in ordinary if issue not in expected_incomplete]
    issues.extend(unexpected)
    check(full.get('status') == 'failed', 'Original full auditor must reject incomplete matrix')
    check(len(full.get('row_audits', [])) == len(rows), 'Not every retained row was audited')
    inventory, uncommitted = [], []
    for path in sorted(results.rglob('*')):
        if not path.is_file():
            continue
        item = dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=path.stat().st_size)
        inventory.append(item)
        if any(path.name.startswith(f'{name}.{method}.{repeat}.') for name, method, repeat in schedule[27:]):
            uncommitted.append(item)
    check(len(inventory) == collection['files'], 'Fetched file denominator differs')
    inventory_by_name = {item['path']: item for item in inventory}
    archive_names = []
    with tarfile.open(ROOT / collection['archive'], 'r:gz') as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            check(member.isfile() and member.name in inventory_by_name, 'Unexpected archive member: ' + member.name)
            if not member.isfile() or member.name not in inventory_by_name:
                continue
            archive_names.append(member.name)
            with archive.extractfile(member) as stream:
                observed_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            check(observed_sha == inventory_by_name[member.name]['sha256'], 'Archive/fetched bytes differ: ' + member.name)
    check(len(archive_names) == len(set(archive_names)) and set(archive_names) == set(inventory_by_name),
          'Archive and retained file inventories differ')
    history = read(ROOT / 'research/hard-survivors-current-v1/history.json')
    check((history['parent_properties'], history['screening_properties'], history['selected_properties']) == (620, 69, 8),
          'Historical parent denominators differ')
    check(set(history['original_names']) == set(order), 'Historical survivor names differ')
    report = dict(status='incomplete', available_row_audit='failed' if issues else 'passed', issues=issues,
                  observed_rows=len(rows), expected_rows=40, missing_rows=13,
                  frozen_plan_sha256=PIN, parent_denominators=[620, 69, 8],
                  original_full_auditor_status=full['status'], original_full_auditor_issues=ordinary,
                  expected_incomplete_issues=[i for i in ordinary if i in expected_incomplete],
                  warnings=full.get('warnings', []), full_rows=rows,
                  scheduled_cells=[dict(sequence=i+1, query=n, method=m, repeat=r) for i,(n,m,r) in enumerate(schedule)],
                  missing_cells=[dict(sequence=i+1, query=n, method=m, repeat=r) for i,(n,m,r) in enumerate(schedule) if (n,m,r) not in observed],
                  uncommitted_missing_cell_artifacts=uncommitted, retained_file_inventory=inventory,
                  parent_plan_metadata_caveats={key:plan[key] for key in ('expected_solver_invocations','kind_preserving_representatives','reporting')},
                  scope='Overall experiment remains incomplete. Available rows retain original resource/command/proof-response checks from unchanged full auditor. Proof checkers are not rerun; no recorded definitive verdict currently needs proof revalidation. Missing cells are unmeasured, never Unknown. Environment-reported competitor binary identities are not independently fetched. Preserve original 620/69/8 parent denominators; three inherited ordinary-cohort plan fields are stale and are retained verbatim. No uninterrupted-run equivalence or superiority claim.',
                  verdict_counts_by_method={m:dict(Counter(r['verdict'] for r in rows if r['method']==m)) for m in plan['methods']},
                  audit_source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__), helper)},
                  evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in (HERE/'terminal.json',HERE/'stopped-observation.json',HERE/'collection.json',results/'runs.jsonl')})
    (HERE / 'interrupted-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:report[k] for k in ('status','available_row_audit','issues','observed_rows','missing_rows','uncommitted_missing_cell_artifacts','verdict_counts_by_method')}))
    return 0 if not issues else 1


if __name__ == '__main__':
    raise SystemExit(main())
