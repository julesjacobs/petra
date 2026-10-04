"""Freeze six separately ordered matched comparison blocks without launching them."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT/'research/repeated-comparison-linux-v1'
PARENT = ROOT/'research/portfolio-reduced-linux-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
audit = json.loads((PARENT/'audit.json').read_text())
assert audit['status']=='passed' and not audit['audit_issues']
assert not audit['classification']['has_conflicts']
assert json.loads((PARENT/'terminal.json').read_text())['exit_code']==0
assert not F.exists()
F.mkdir()
base = json.loads((PARENT/'plan.json').read_text())
methods = ['native-reduced','native-frozen','verifypn-default','smpt-mcc-portable']
scripts = ['prepare','run','manage']
setup = {f'research/{name}-repeated-comparison-linux-v1.py':sha(ROOT/f'research/{name}-repeated-comparison-linux-v1.py') for name in scripts}
blocks = []
for index,(seconds,seed) in enumerate([(5,2026092807),(30,2026092808),(30,2026092809),(5,2026092810),(5,2026092811),(30,2026092812)]):
    name = f'b{index+1}-{seconds}s'
    folder = F/name
    folder.mkdir()
    plan = copy.deepcopy(base)
    plan.update(format='repeated-comparison-block-v1',status='prepared-not-launched',
                output=f'results/linux-repeated-comparison-v1/{name}',seconds=seconds,
                repeat=1,order_seed=seed,expected_rows=704,expected_solver_invocations=704,
                methods={m:base['methods'][m] for m in methods},
                native_tools={m:base['native_tools'][m] for m in methods if m in base['native_tools']},
                native_binary='results/linux-solver-portfolio-reduced-v1/vass-reach',
                native_binary_sha256=base['native_tools']['native-reduced']['binary_sha256'],
                buffer_agglomeration_methods=['native-reduced','native-frozen'],
                capability_preflight=dict(status='pending',receipt=str((folder/'capability.json').relative_to(ROOT))),
                suite_block=name,
                scope='One registered block of the repeated development comparison; original PNML/XML, all176 properties/175distinct representatives; reserved evaluation untouched.',
                reporting='Retain all failures and partial perf exports; native answers independently checked, external answers reported. Aggregate across all six registered blocks after audit.')
    plan['preflight_file_sha256'].update(setup)
    plan['selection_evidence'].update({str((PARENT/'plan.json').relative_to(ROOT)):sha(PARENT/'plan.json'),str((PARENT/'audit.json').relative_to(ROOT)):sha(PARENT/'audit.json')})
    (folder/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    blocks.append(dict(name=name,seconds=seconds,order_seed=seed,plan_sha256=sha(folder/'plan.json')))
suite = dict(format='repeated-comparison-suite-v1',status='registered-not-launched',
             blocks=blocks,rows=4224,methods=methods,properties=176,representatives=175,
             parent_plan_sha256=sha(PARENT/'plan.json'),parent_audit_sha256=sha(PARENT/'audit.json'),
             setup_sha256=setup,protocol_sha256=sha(ROOT/'research/repeated-comparison-protocol-v1.md'),
             analysis=dict(primary_denominator='175 distinct ordered-branch representatives; also report all176 slots',
                           timeout_penalty='PAR-2: accepted definitive wall time; all other rows cost twice the registered budget',
                           repeatability='Per-query/budget solved frequency and wall-time median/range across three blocks',
                           comparison='Paired gains/losses per block; all-block intersection/union; common-solved timing explicitly conditioned',
                           counters='No imputation of missing perf values; report coverage and exclusions'),
             capability='Fresh four-property/four-method harness and five component checks at each budget; seed-only blocks inherit explicit audited derivations.')
(F/'suite.json').write_text(json.dumps(suite,indent=2)+'\n')
print(json.dumps(dict(status='registered',rows=4224,suite_sha256=sha(F/'suite.json'))))
