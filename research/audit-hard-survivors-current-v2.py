"""Audit the complete current-tool historical-survivor rerun after collection."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / 'research/hard-survivors-current-v2'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    for path in [EXPERIMENT / 'terminal.json',
                 ROOT / 'research/signed-threshold-full-v1-terminal.json']:
        assert read(path)['exit_code'] == 0, path
    plan_path = EXPERIMENT / 'plan.json'
    plan = read(plan_path)
    assert sha(plan_path) == read(EXPERIMENT / 'execution.json')['plan_sha256']
    collection = read(EXPERIMENT / 'collection.json')
    assert sha(ROOT / collection['archive']) == collection['sha256']
    helper = ROOT / 'research/audit-linux-application-expansion-v2.py'
    spec = importlib.util.spec_from_file_location('application_artifact_audit', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.safe_audit(ROOT, plan_path, ROOT / plan['output'])
    history_path = ROOT / 'research/hard-survivors-current-v1/history.json'
    history = read(history_path)
    manifest = read(ROOT / plan['corpus'] / 'manifest.json')
    expected_names = history['original_names']
    checks = [
        (plan['parent_properties'] == history['parent_properties'] == 620, '620-property parent'),
        (plan['source_properties'] == history['screening_properties'] == 69, '69-property screen'),
        (plan['properties'] == history['selected_properties'] == len(expected_names) == 8, 'eight survivors'),
        ({q['name'] for q in manifest['queries']} == set(expected_names), 'unchanged survivor selection'),
        (plan['expected_rows'] == report.get('rows') == collection['rows'] == 40, '40-row matrix'),
        (plan['repeat'] == 1 and len(plan['methods']) == 5, 'five configurations, one repeat'),
        (plan['seconds'] == 300 and plan['linux_cpus'] == [8], '300s single-core comparison'),
        (report.get('exact_ordered_branch_representatives') == 8, 'eight representatives'),
    ]
    for valid, label in checks:
        if not valid:
            report['audit_issues'].append('Historical survivor reconciliation failed: ' + label)
    report['status'] = 'failed' if report['audit_issues'] else 'passed'
    report['parent_denominators'] = dict(parent=620, screening=69, selected=8)
    report['plan_metadata_caveats'] = {
        key: plan[key] for key in ['expected_solver_invocations', 'kind_preserving_representatives', 'reporting']
    }
    report['plan_metadata_caveat_scope'] = (
        'These three inherited fields describe the earlier ordinary cohort. '
        'The actual frozen command and matrix specify eight queries, five configurations, '
        '40 rows, and eight exact representatives. The original plan is preserved unchanged.')
    artifacts = report.setdefault('artifact_sha256', {})
    for path in [Path(__file__).resolve(), history_path, EXPERIMENT / 'execution.json',
                 EXPERIMENT / 'terminal.json', EXPERIMENT / 'collection.json']:
        artifacts[str(path.relative_to(ROOT))] = sha(path)
    (EXPERIMENT / 'audit.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(status=report['status'], rows=report.get('rows'),
                         parent_denominators=report['parent_denominators'],
                         issues=report['audit_issues'], warnings=len(report.get('warnings', [])))))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    sys.exit(main())
