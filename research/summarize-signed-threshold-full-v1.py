"""Summarize audited threshold coverage, paired costs and historical complementarity."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'results/local-signed-threshold-full-v1'
BASELINE = ROOT / 'results/linux-application-walk-full-v1'
METHODS = ['native-threshold', 'native-unary']
DEFINITIVE = {'reachable', 'unreachable'}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def distribution(values):
    return dict(count=len(values), total=sum(values), median=median(values) if values else None,
                maximum=max(values) if values else None)


def main():
    assert read(ROOT / 'research/signed-threshold-full-v1-terminal.json')['exit_code'] == 0
    audit_path = ROOT / 'research/signed-threshold-full-v1-audit.json'
    baseline_audit_path = ROOT / 'research/application-walk-full-v1/audit.json'
    audit, baseline_audit = read(audit_path), read(baseline_audit_path)
    assert audit['status'] == baseline_audit['status'] == 'passed'
    for folder, report in [(LOCAL, audit), (BASELINE, baseline_audit)]:
        for filename in ['runs.jsonl', 'environment.json']:
            path = folder / filename
            assert sha(path) == report['artifact_sha256'][str(path.relative_to(ROOT))]
    local_environment, baseline_environment = read(LOCAL / 'environment.json'), read(BASELINE / 'environment.json')
    assert local_environment['manifest_sha256'] == baseline_environment['manifest_sha256']
    manifest_path = ROOT / 'benchmarks/application-portfolio-comparison-v1/manifest.json'
    assert sha(manifest_path) == local_environment['manifest_sha256']
    queries = {q['name']: q for q in read(manifest_path)['queries']}
    rows = [json.loads(line) for line in (LOCAL / 'runs.jsonl').read_text().splitlines()]
    historical = [json.loads(line) for line in (BASELINE / 'runs.jsonl').read_text().splitlines()]
    baseline = {r['query']: r for r in historical if r['method'] == 'native-walk'}
    by_method = {m: {r['query']: r for r in rows if r['method'] == m} for m in METHODS}
    assert all(set(rs) == set(queries) for rs in [baseline, *by_method.values()])
    assert len(rows) == 1312 and len(queries) == 656
    solved = {m: {name for name, row in rs.items() if row['verdict'] in DEFINITIVE}
              for m, rs in by_method.items()}
    baseline_solved = {name for name, row in baseline.items() if row['verdict'] in DEFINITIVE}
    disagreements = []
    for method in METHODS:
        for name in solved[method] & baseline_solved:
            if by_method[method][name]['property_truth'] != baseline[name]['property_truth']:
                disagreements.append(dict(query=name, method=method))
    assert not disagreements, disagreements
    paired = sorted(solved[METHODS[0]] & solved[METHODS[1]])
    costs = {}
    for method, rs in by_method.items():
        definitive = [rs[name] for name in solved[method]]
        costs[method] = dict(
            solver_seconds_on_checked_answers=distribution([r['wall_seconds'] for r in definitive]),
            checker_seconds_on_checked_answers=distribution([r['validation']['wall_seconds'] for r in definitive]),
            end_to_end_seconds_on_checked_answers=distribution([
                r['wall_seconds'] + r['validation']['wall_seconds'] for r in definitive]),
            all_imported_solver_seconds=distribution([
                r['wall_seconds'] for name, r in rs.items() if queries[name]['status'] == 'imported']),
            failures=dict(Counter(r.get('failure_stage') or 'none' for r in rs.values())),
            validation_failures=dict(Counter(r.get('validation_failure') or 'none' for r in rs.values())),
            outer_timeouts=sum(bool(r.get('outer_timeout')) for r in rs.values()),
            solver_memory_failures=sum(bool((r.get('resources') or {}).get('memory_limit_exceeded')) for r in rs.values()),
        )
    report = dict(
        status='passed', source_slots=656, imported_slots=640, unavailable_slots=16,
        rows=len(rows), coverage=audit['coverage'], costs=costs,
        binary_only=sorted(solved[METHODS[0]] - solved[METHODS[1]]),
        unary_only=sorted(solved[METHODS[1]] - solved[METHODS[0]]),
        paired_costs=dict(queries=paired,
            binary_over_unary_solver_ratio=distribution([
                by_method[METHODS[0]][name]['wall_seconds'] / by_method[METHODS[1]][name]['wall_seconds']
                for name in paired]),
            scope='Conditional on both methods returning checked answers in the same local screen; one repeat.'),
        historical_complementarity=dict(
            baseline='native-walk, completed single-core Linux 5s screen',
            baseline_definitive=len(baseline_solved),
            baseline_unknown=sorted(set(queries) - baseline_solved - {
                name for name, q in queries.items() if q['status'] != 'imported'}),
            newly_checked={m: sorted(solved[m] - baseline_solved) for m in METHODS},
            scope='Same query identities across different machines; diagnostic capability comparison only. '
                  'No cross-machine cost ratio or measured integrated-portfolio gain.'),
        families={family: {
            m: dict(Counter(row['verdict'] for name, row in rs.items() if queries[name]['family'] == family))
            for m, rs in by_method.items()}
            for family in sorted({q['family'] for q in queries.values()})},
        evidence_sha256={str(path.relative_to(ROOT)): sha(path) for path in [
            audit_path, baseline_audit_path, manifest_path, Path(__file__).resolve()]},
        scope='Standalone negative-only engines; all source slots retained. Costs include process '
              'startup/parsing; checking reported separately. Local memory limit is sampled. '
              'No stable speed, novelty, general superiority or publication-readiness claim.')
    output = ROOT / 'research/signed-threshold-full-v1-summary.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ['coverage', 'binary_only', 'unary_only', 'historical_complementarity']}, indent=2))


if __name__ == '__main__':
    main()
