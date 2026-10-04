"""Freeze the combined solver's six-configuration original-input Linux comparison."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-reduced-linux-v1'
D='results/linux-solver-portfolio-reduced-v1';REMOTE='/home/jules/experiments/pvass-publication/'
RUNNER='results/runner-smpt-single-core-v3';OLD='results/runner-smpt-single-core-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=ROOT/'research/portfolio-counts-linux-v1/plan.json'
plan=json.loads(parent.read_text());build=json.loads((ROOT/D/'build-receipt.json').read_text())
assert build['exit_code']==build['tests_exit_code']==0
assert build['rustc']==json.loads((ROOT/'results/linux-solver-walk-sparse-v2/provenance.json').read_text())['rustc']
assert sha(ROOT/D/'vass-reach')==build['binary_sha256']
assert json.loads((ROOT/'research/portfolio-counts-linux-v1/audit.json').read_text())['status']=='passed'
assert json.loads((ROOT/'research/portfolio-reduced-development-v1/audit.json').read_text())['status']=='passed'
methods=['native-reduced','native-counts','native-walk','native-frozen','verifypn-default','smpt-mcc-portable']
plan['native_tools']={'native-reduced':dict(engine='portfolio-reduced',binary=REMOTE+D+'/vass-reach',binary_sha256=build['binary_sha256']),**plan['native_tools']}
plan.update(format='portfolio-reduced-linux-development-v1',status='prepared-not-launched',output='results/linux-portfolio-reduced-v1',expected_rows=1056,expected_solver_invocations=1056,methods={k:(plan['native_tools'][k]['engine'] if k in plan['native_tools'] else plan['methods'][k]) for k in methods},buffer_agglomeration_methods=list(plan['native_tools']),capability_preflight=dict(status='pending',receipt='research/portfolio-reduced-linux-v1/capability.json'),scope='Complete176 development properties/175 exact representatives, six matched configurations at5s, CPU8/enforced2GiB. Original PNML/XML; reserved families untouched.',reporting='Retain all1056 rows and failures. Native answers independently checked, external verdicts tool-reported. One repeat, no stable timing or superiority claim.',reduced_bfs_stage=dict(seconds='min(remaining/3,1)',state_limit=200000,proof='nested checked reductions plus re-explored finite-closure-v1',fallback='unchanged'),runner_source=RUNNER+'/source',runner_archive_sha256=sha(ROOT/RUNNER/'runner.tar.gz'),runner_vendor_symlink=dict(path=RUNNER+'/source/vendor',target='../../../vendor'))
assert all(plan['methods'][k]==v['engine'] for k,v in plan['native_tools'].items())
required={name.replace(OLD+'/source/',RUNNER+'/source/'):digest for name,digest in plan['required_file_sha256'].items()}
for name,digest in json.loads((ROOT/RUNNER/'files-sha256.json').read_text()).items():required[RUNNER+'/source/'+name]=digest
required[D+'/vass-reach']=build['binary_sha256']
for name,digest in json.loads((ROOT/D/'source-files-sha256.json').read_text()).items():required[D+'/source/'+name]=digest
plan['required_file_sha256']=required
extra=['research/prepare-portfolio-reduced-linux-v1.py','research/run-portfolio-reduced-linux-v1.py','research/preflight-portfolio-reduced-linux-v1.py','research/preflight-portfolio-reduced-components-v1.py','research/build-portfolio-reduced-linux-v1.py',D+'/source-files-sha256.json',D+'/build-receipt.json',D+'/build.log',D+'/tests.log']
extra += [RUNNER+'/'+n for n in ['files-sha256.json','provenance.json','runner.tar.gz']]
plan['preflight_file_sha256'].update({n:sha(ROOT/n) for n in extra})
plan['selection_evidence'].update({str(parent.relative_to(ROOT)):sha(parent),'research/portfolio-counts-linux-v1/summary.json':sha(ROOT/'research/portfolio-counts-linux-v1/summary.json'),'research/portfolio-reduced-development-v1/audit.json':sha(ROOT/'research/portfolio-reduced-development-v1/audit.json')})
plan['preflight_file_sha256'].update(plan['selection_evidence'])
with (F/'plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps(dict(plan_sha256=sha(F/'plan.json'),rows=1056,methods=methods)))
