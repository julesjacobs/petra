"""Audit a single documented descriptive-field correction against the unchanged execution plan."""
import copy,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-counts-linux-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((F/'plan.json').read_text());analysis=json.loads((F/'analysis-plan.json').read_text());amend=json.loads((F/'analysis-plan-amendment.json').read_text())
assert amend['original_plan_sha256']==sha(F/'plan.json') and amend['analysis_plan_sha256']==sha(F/'analysis-plan.json')
expected=copy.deepcopy(original)
assert expected['methods']['native-counts']=='walk plus bounded remaining-state count stage'
assert expected['native_tools']['native-counts']['engine']=='portfolio-walk-counts'
expected['methods']['native-counts']=expected['native_tools']['native-counts']['engine']
assert analysis==expected,'Only one redundant descriptive field may differ'
for name in ['execution.json','terminal.json']:
 r=json.loads((F/name).read_text());assert r['plan_sha256']==sha(F/'plan.json')
terminal=json.loads((F/'terminal.json').read_text());assert terminal['exit_code']==0
execution=json.loads((F/'execution.json').read_text());cap=json.loads((F/'capability.json').read_text())
assert sha(F/'capability.json')==execution['capability_receipt_sha256']
assert cap['status']=='passed' and cap['plan_sha256']==sha(F/'plan.json')
assert cap['methods']==list(original['methods'])
spec=importlib.util.spec_from_file_location('base_auditor',ROOT/'research/audit-general-development-v3-linux-v1.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
report=base.safe_audit(ROOT,F/'analysis-plan.json',ROOT/'results/linux-portfolio-counts-v1')
report['plan_interpretation']=amend
for p in [F/'plan.json',F/'analysis-plan.json',F/'analysis-plan-amendment.json',Path(__file__)]:report['artifact_sha256'][str(p.relative_to(ROOT))]=sha(p)
(F/'audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(F/'audit.md').write_text(f"# Linux count portfolio audit: {report['status']}\n\nOriginal execution/capability identities checked against plan.json.\nAnalysis-only normalization of methods.native-counts checked against the original\nnative_tools engine, with all other fields identical. See analysis-plan-amendment.json.\n\nIssues: {len(report['audit_issues'])}; warnings: {len(report['warnings'])}.\n")
print(json.dumps(dict(status=report['status'],issues=report['audit_issues'],warnings=report['warnings'])))
assert report['status']=='passed' and not report['audit_issues']
