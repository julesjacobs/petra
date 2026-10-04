"""Advance using a corrected postprocessing-helper audit, preserving the v1 failure."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/application-ladder-qualification-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


plan = read(BASE / 'plan-60.json')
receipt_path = ROOT / 'research/qualification-60-completion.json'
receipt = read(receipt_path)
assert receipt['terminal'] is True and receipt['session_id'] == '13213' and receipt['exit_code'] == 0
for name, digest in receipt['sha256'].items():
    assert sha(ROOT / receipt['output'] / name) == digest
for name in ['research/prepare-application-ladder-qualification-v1.py',
             'research/run-application-ladder-qualification-v1.py',
             'research/audit-linux-application-expansion-v1.py',
             'scripts/analyze_application_expansion.py']:
    assert sha(ROOT / name) == plan['required_file_sha256'][name]
old = (ROOT / 'research/audit-linux-application-expansion-v1.py').read_text()
new = (ROOT / 'research/audit-linux-application-expansion-v2.py').read_text()
needle = "        if path.startswith('scripts/'):\n            identity(results/'runner-source'/Path(path).name, expected_hash, 'fetched runner bytes')"
replacement = """        if path == 'scripts/analyze_application_expansion.py':
            identity(root/path, expected_hash, 'registered postprocessing helper; analysis recomputed in this audit')
        elif path.startswith('scripts/'):
            identity(results/'runner-source'/Path(path).name, expected_hash, 'fetched runner bytes')"""
assert old.count(needle) == 1 and new == old.replace(needle, replacement)
failed = read(BASE / 'stage-60-audit.json')
assert failed['status'] == 'failed' and len(failed['audit_issues']) == 2
assert all('analyze_application_expansion.py' in issue for issue in failed['audit_issues'])
report = read(BASE / 'stage-60-audit-v2.json')
assert report['status'] == 'passed' and not report['audit_issues']
assert report['classification']['validity'] == 'complete_consistent_screen'
for name, digest in report['artifact_sha256'].items():
    assert sha(ROOT / name) == digest, name
assert report['classification'] == failed['classification']
names = report['classification']['selections']['all_unresolved']
assert set(names) <= set(read(BASE / 'selection.json')['names'])
erratum = dict(reason='v1 incorrectly treated every registered scripts/ path as a runtime runner snapshot. The analyzer is postprocessing code and was never imported by the measured runner. v2 checks its registered local hash and recomputes classification with that helper; every runtime snapshot check is unchanged.',
               original_failed_audit='research/application-ladder-qualification-v1/stage-60-audit.json',
               corrected_audit='research/application-ladder-qualification-v1/stage-60-audit-v2.json',
               expected_helper_sha256=plan['required_file_sha256']['scripts/analyze_application_expansion.py'],
               original_plans_results_unchanged=True, selection_rule_unchanged=True,
               original_and_recomputed_classifications_equal=True, rows=52, selected=13,
               joint_survivors=names, future_auditor='research/audit-linux-application-expansion-v2.py')
with (BASE / 'audit-role-erratum.json').open('x') as stream:
    json.dump(erratum, stream, indent=2); stream.write('\n')
spec = importlib.util.spec_from_file_location('registration', ROOT / 'research/prepare-application-ladder-qualification-v1.py')
registration = importlib.util.module_from_spec(spec); spec.loader.exec_module(registration)
paths = [BASE/'plan-60.json', BASE/'stage-60-audit.json', BASE/'stage-60-audit-v2.json',
         BASE/'audit-role-erratum.json', receipt_path, Path(__file__),
         ROOT/'research/audit-linux-application-expansion-v2.py',
         ROOT/receipt['output']/'environment.json', ROOT/receipt['output']/'runs.jsonl']
evidence = {str(path.relative_to(ROOT)): sha(path) for path in paths}
print(json.dumps(registration.register(300, names, evidence)))
state_path = BASE / 'execution-60.json'
state = read(state_path)
state.update(status='complete-audited',audit='research/application-ladder-qualification-v1/stage-60-audit-v2.json',
             audit_status='passed',erratum='research/application-ladder-qualification-v1/audit-role-erratum.json')
state_path.write_text(json.dumps(state,indent=2)+'\n')
