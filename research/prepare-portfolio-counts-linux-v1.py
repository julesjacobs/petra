"""Register the complete harder cohort and five matched configurations before execution."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-counts-linux-v1'
D='results/linux-solver-portfolio-counts-v1';REMOTE='/home/jules/experiments/pvass-publication/'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=ROOT/'research/general-development-v3-linux-v1/plan.json'
plan=json.loads(parent.read_text());build=json.loads((ROOT/D/'build-receipt-v2.json').read_text())
assert build['exit_code']==build['tests_exit_code']==0
assert build['rustc']==json.loads((ROOT/'results/linux-solver-walk-sparse-v2/provenance.json').read_text())['rustc']
assert sha(ROOT/D/'vass-reach')==build['binary_sha256']
methods=['native-counts','native-walk','native-frozen','verifypn-default','smpt-mcc-portable']
plan['native_tools']={k:v for k,v in plan['native_tools'].items() if k in methods}
plan['native_tools']={'native-counts':dict(engine='portfolio-walk-counts',binary=REMOTE+D+'/vass-reach',binary_sha256=build['binary_sha256']),**plan['native_tools']}
plan.update(format='portfolio-counts-linux-development-v1',status='prepared-not-launched',output='results/linux-portfolio-counts-v1',expected_rows=880,expected_solver_invocations=880,methods={k:('walk plus bounded remaining-state count stage' if k=='native-counts' else plan['methods'][k]) for k in methods},buffer_agglomeration_methods=['native-counts','native-walk','native-frozen'],capability_preflight=dict(status='pending',receipt='research/portfolio-counts-linux-v1/capability.json'),scope='Same complete176 development properties/175 exact representatives as prior qualification. Five matched configurations at5s each, CPU8/enforced2GiB, frozen original inputs. Reserved families untouched.',reporting='Retain all880 rows and failures; native answers independently checked, external answers tool-reported. One repeat; no stable speed or superiority claim.',competitor_selection='VerifyPN default and whole-cohort strongest SMPT MCC portable selected by completed prior176-property qualification, not per-instance oracle.',count_stage=dict(walk='unchanged',count_seconds='min(remaining/5,0.250)',eligibility='existing sparse construction guard',fallback='unchanged relevant/causal/batched',cap='remaining expanded-trace states minus final acceptance check'))
for field in ['smpt_configurations','smpt_scheduling']:
 plan[field]={k:v for k,v in plan[field].items() if k in methods}
required=plan['required_file_sha256']
required[D+'/vass-reach']=build['binary_sha256']
for name,digest in json.loads((ROOT/D/'source-files-sha256.json').read_text()).items():required[D+'/source/'+name]=digest
extra=['research/prepare-portfolio-counts-linux-v1.py','research/run-portfolio-counts-linux-v1.py','research/preflight-portfolio-counts-linux-v1.py','research/preflight-portfolio-counts-components-v1.py','research/build-portfolio-counts-linux-v2.py',D+'/source-files-sha256.json',D+'/build-receipt-v2.json',D+'/build-v2.log',D+'/tests-v2.log']
plan['preflight_file_sha256'].update({n:sha(ROOT/n) for n in extra})
plan['selection_evidence'].update({str(parent.relative_to(ROOT)):sha(parent),'research/general-development-v3-linux-v1/summary.json':sha(ROOT/'research/general-development-v3-linux-v1/summary.json'),'research/portfolio-counts-development-v1/audit.json':sha(ROOT/'research/portfolio-counts-development-v1/audit.json')})
plan['preflight_file_sha256'].update(plan['selection_evidence'])
with (F/'plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps(dict(plan_sha256=sha(F/'plan.json'),rows=880,methods=methods)))
