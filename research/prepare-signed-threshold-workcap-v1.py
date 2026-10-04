"""Prepare metadata only: no solvers, model imports, or benchmark execution."""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ROOT / 'research/signed-threshold-workcap-v1'
CORPUS = ROOT / 'benchmarks/signed-threshold-workcap-v1'
PARENT = ROOT / 'benchmarks/application-portfolio-comparison-v1'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    summary_path = ROOT / 'research/signed-threshold-full-v1-summary.json'
    audit_path = ROOT / 'research/signed-threshold-full-v1-audit.json'
    parent_plan_path = ROOT / 'research/signed-threshold-full-v1-plan.json'
    summary, audit, parent_plan = map(read, (summary_path, audit_path, parent_plan_path))
    if summary['status'] != 'passed' or audit['status'] != 'passed':
        raise ValueError('Completed parent audit required')
    names = sorted(set(summary['historical_complementarity']['baseline_unknown']) | set(summary['unary_only']))
    assert len(names) == 10
    assert len(summary['historical_complementarity']['baseline_unknown']) == 8
    assert len(summary['unary_only']) == 2
    denominators = dict(source_slots=656, imported_slots=640, unavailable_slots=16)
    for key, expected in denominators.items():
        assert summary[key] == parent_plan[key] == expected
    parent_manifest = read(PARENT / 'manifest.json')
    parent_queries = {q['name']: q for q in parent_manifest['queries']}
    queries = [copy.deepcopy(parent_queries[name]) for name in names]
    assert all(q['status'] == 'imported' for q in queries)
    for q in queries:
        for field in ('net', 'property', 'pnml', 'xml'):
            assert (CORPUS / q[field]).resolve() == (PARENT / q[field]).resolve()
        for branch in q['branches']:
            assert (CORPUS / branch['path']).resolve() == (PARENT / branch['path']).resolve()
    selection = dict(format='signed-threshold-workcap-selection-v1',
        status='outcome-selected-development-diagnostic', parent_denominators=denominators,
        parent_manifest='benchmarks/application-portfolio-comparison-v1/manifest.json',
        parent_manifest_sha256=sha(PARENT / 'manifest.json'),
        evidence_sha256={str(p.relative_to(ROOT)): sha(p) for p in (summary_path, audit_path, parent_plan_path)},
        rule='Exactly the union of historical_complementarity.baseline_unknown and unary_only in the completed full-v1 summary.',
        baseline_unknown=summary['historical_complementarity']['baseline_unknown'],
        unary_only=summary['unary_only'], queries=names,
        scope='Diagnose sensitivity to the logical-work cap. Outcome-selected subset; no full-cohort superiority inference. Historical Mac/Linux costs are not compared as speedups.')
    CORPUS.mkdir()
    selection_path = Path(str(PREFIX) + '-selection.json')
    write_new(selection_path, selection)
    write_new(CORPUS / 'manifest.json', dict(format='signed-threshold-workcap-v1', collection_complete=True,
        expected_properties=10, parent_denominators=denominators, selection_status=selection['status'],
        selection=str(selection_path.relative_to(ROOT)), selection_sha256=sha(selection_path), queries=queries,
        scope=selection['scope']))
    command = list(parent_plan['command'])
    for flag, value in [('--corpus', str(CORPUS)), ('--max-states', '100000000'),
                        ('--output', str(ROOT / 'results/local-signed-threshold-workcap-v1'))]:
        command[command.index(flag) + 1] = value
    pins = {name: digest for name, digest in parent_plan['file_sha256'].items()
            if name.startswith('results/solver-signed-threshold-v1/')
            or name.startswith('results/runner-threshold-v1/')}
    for q in queries:
        for field in ('net', 'property', 'pnml', 'xml'):
            name = str((CORPUS / q[field]).resolve().relative_to(ROOT))
            assert parent_plan['file_sha256'][name] == q[field + '_sha256']
            pins[name] = q[field + '_sha256']
        for branch in q['branches']:
            name = str((CORPUS / branch['path']).resolve().relative_to(ROOT))
            assert parent_plan['file_sha256'][name] == branch['sha256']
            pins[name] = branch['sha256']
    for path in (summary_path, audit_path, parent_plan_path, PARENT / 'manifest.json',
                 CORPUS / 'manifest.json', selection_path, Path(__file__),
                 ROOT / 'research/launch-signed-threshold-workcap-v1.py',
                 ROOT / 'research/audit-signed-threshold-workcap-v1.py',
                 ROOT / 'research/audit-signed-threshold-full-v1.py'):
        pins[str(path.relative_to(ROOT))] = sha(path)
    pins[str(Path(command[0]).relative_to(ROOT))] = sha(Path(command[0]))
    plan = dict(format='signed-threshold-workcap-v1', command=command, rows=20, queries=names,
        source_slots=10, imported_slots=10, unavailable_slots=0, parent_denominators=denominators,
        selection_status=selection['status'], selection_sha256=sha(selection_path),
        parent_logical_work=2000000, logical_work=100000000,
        binary_sha256=parent_plan['binary_sha256'], file_sha256=pins,
        scope=selection['scope'] + ' Same frozen binary and runner, two negative-only engines, 5s solver, sampled 2GiB, separate 60s/2GiB checking, one local repeat. No defaults changed.')
    plan_path = Path(str(PREFIX) + '-plan.json')
    write_new(plan_path, plan)
    print(json.dumps(dict(plan_sha256=sha(plan_path), selection_sha256=sha(selection_path),
                         manifest_sha256=sha(CORPUS / 'manifest.json'), rows=20, launched=False)))


if __name__ == '__main__':
    main()
