"""Freeze a new difficulty screen; does not run solvers or modify old experiments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

corpus = 'benchmarks/application-parameter-ladders-v2'
manifest = json.loads((ROOT/corpus/'manifest.json').read_text())
assert manifest['collection_complete'] and len(manifest['queries']) == 464
assert sum(q['status'] == 'imported' for q in manifest['queries']) == 448
base = json.loads((ROOT/'research/application-expansion-v1-screen-plan.json').read_text())
base['required_file_sha256'] = {k:v for k,v in base['required_file_sha256'].items()
                              if not k.startswith('benchmarks/application-expansion-v1/')}
for p in sorted((ROOT/corpus).rglob('*')):
    if p.is_file():
        base['required_file_sha256'][str(p.relative_to(ROOT))] = sha(p)
selection = 'benchmarks/application-parameter-ladders-v2-selection.json'
base.update(corpus=corpus, manifest_sha256=sha(ROOT/corpus/'manifest.json'),
            properties=464, expected_rows=1856, parent_properties=464, source_properties=464,
            imported_properties=448, collection_failed_properties=16,
            output='results/linux-application-parameter-ladders-v2', order_seed=20261011,
            scope='First difficulty screen of all464planned property slots from29new instances of5development families;448imported and16collection failures retained.',
            candidate_scope='Same frozen capacity-direct Rust and VerifyPN as prior application screen. Later Rust implementations excluded. SMPT adds the now smoke-verified isolated MiniZinc/Gecode capability; this is a new configuration.',
            execution='Registered before first solver execution. Require completed acquisition audit, completed dependency setup, identity preflight, and a free measuring host.',
            reporting='Report464slots and448imported queries separately, all1856rows, per-family and per-parameter results, exact ordered-branch duplicate representatives, all failures and unknowns. One repeat screens difficulty only.',
            followup='Select every jointly unresolved imported query for separate longer-budget qualification; retain full parent selection and all failures. Keep complete cohort for regressions.',
            host_caveat='CPU8affinity is not exclusive isolation. Record load, wall time, cgroup resources and instructions. No builds, transfers, imports or engineering on Linux during measurement.',
            selection_evidence={selection:sha(ROOT/selection)},
            minizinc_preflight='research/check-smpt-minizinc-repair-v1.py',
            minizinc_tool_bin='vendor/minizinc-linux-v1/MiniZincIDE-2.10.1-x86_64-linux-gnu/bin',
            minizinc_capability='MiniZinc2.10.1, default Gecode6.4.0; direct and SMPT CP satisfiable/unsatisfiable smoke checks passed. All1136bundle files/configuration/library identities checked separately before launch.',
            status='registered-not-started')
base.pop('validation_policy_change', None)
for name in (selection,'research/check-smpt-minizinc-repair-v1.py',
             'research/smpt-minizinc-repair-v1/metadata.json',
             'research/smpt-minizinc-repair-v1/bundle-files-sha256.json',
             'research/prepare-application-ladders-v2-screen.py'):
    base['required_file_sha256'][name]=sha(ROOT/name)
plan = ROOT/'research/application-parameter-ladders-v2-screen-plan.json'
with plan.open('x') as stream:
    json.dump(base, stream, indent=2, sort_keys=True); stream.write('\n')
launcher = (ROOT/'research/run-linux-application-expansion-v1.sh').read_text()
launcher = launcher.replace('application-expansion-v1', 'application-parameter-ladders-v2')
launcher = launcher.replace('20261008', '20261011')
launcher = launcher.replace('vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py',
    'vendor/venv/bin/python research/check-smpt-minizinc-repair-v1.py\nvendor/venv/bin/python -u scripts/benchmark_smpt_classic.py')
launcher = launcher.replace('  --verifypn-binary',
    '  --tool-bin vendor/minizinc-linux-v1/MiniZincIDE-2.10.1-x86_64-linux-gnu/bin \\\n  --verifypn-binary')
with (ROOT/'research/run-linux-application-parameter-ladders-v2.sh').open('x') as stream:
    stream.write(launcher)
print(json.dumps(dict(plan=str(plan.relative_to(ROOT)), sha256=sha(plan),
                      required_files=len(base['required_file_sha256']), expected_rows=1856)))
