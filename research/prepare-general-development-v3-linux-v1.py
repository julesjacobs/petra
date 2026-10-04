"""Prepare the fixed 176-property qualification plan without deployment or execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
REMOTE = Path('/home/jules/experiments/pvass-publication')
FOLDER = ROOT / 'research/general-development-v3-linux-v1'
RUNNER = 'results/runner-smpt-single-core-v2'


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    parent = read('research/application-walk-full-v1/plan.json')
    assert read('research/application-walk-full-v1/audit.json')['status'] == 'passed'
    prior_env = read('results/linux-application-walk-full-v1/environment.json')
    collection = read('research/general-development-v3-collection-audit.json')
    imports = read('research/general-development-v3-imports/summary.json')
    manifest = read('benchmarks/general-development-v3/manifest.json')
    assert collection['status'] == imports['status'] == 'passed'
    assert imports['matched'] == len(manifest['queries']) == 176
    assert collection['exact_ordered_branch_representatives'] == 175
    assert all(q['status'] == 'imported' for q in manifest['queries'])
    sys.path.insert(0, str(ROOT / RUNNER / 'source/scripts'))
    import benchmark_smpt_classic as runner
    copied_keys = ['native_tools', 'native_binary', 'native_binary_sha256', 'verifypn', 'validation',
                   'minizinc_preflight', 'minizinc_tool_bin', 'walk_defaults', 'walk_policy']
    plan = {key: parent[key] for key in copied_keys}
    plan.update(format='general-development-v3-linux-qualification-v1',
        status='prepared-capability-preflight-pending-not-deployed-not-started',
        corpus='benchmarks/general-development-v3', output='results/linux-general-development-v3-v1',
        properties=176, source_properties=176, parent_properties=176, imported_properties=176,
        collection_failed_properties=0, exact_ordered_branch_representatives=175,
        kind_preserving_representatives=collection['exact_ordered_branch_and_kind_representatives'],
        expected_rows=1584, expected_solver_invocations=1584, seconds=5, repeat=1,
        linux_cpus=[8], perf=True, memory_mib=2048, max_states=2000000, outer_grace=0,
        order_seed=2026092903, manifest_sha256=collection['manifest_sha256'],
        buffer_agglomeration_methods=['native-walk', 'native-batched', 'native-frozen'],
        target_zero_trap_methods=[], target_path_potential_methods=[], geometric_branches_methods=[],
        runner_source=RUNNER + '/source', runner_archive_sha256=sha(RUNNER + '/runner.tar.gz'),
        runner_vendor_symlink=dict(path=RUNNER + '/source/vendor', target='../../../vendor'),
        methods={**parent['methods'], **{name: ('official MCC scheduling' if name == 'smpt-mcc-portable'
                                           else 'requested portable portfolio') for name in runner.SMPT_SINGLE_CORE_MODES}},
        capability_preflight=dict(status='pending', receipt='research/general-development-v3-linux-v1/capability.json',
            requirements='Verify exact harness configurations with synthetic EF true/false and AG polarity, fully reducible SMT/CP, original PNML/XML, CPU8/cgroup/perf, portable WALK patch and repaired MiniZinc. Root performs preflight; no claims until passed.'),
        scope='All 176 fixed source slots from six development family groups, 175 exact ordered-branch representatives. Difficulty unmeasured. All 22 reserved families untouched.',
        reporting='Retain all 1584 rows, duplicates, failures and counters; independently checked native answers, external tool-reported answers. One seeded single-core repeat is exploratory; no stable speed or superiority claim.',
        smpt_selection_rule='Choose whole-cohort definitive coverage first, then capped total solver wall time, then full/compact/PDR/PDR-saturated/MCC fixed order. Oracle union is diagnostic only.')
    smpt = [name for name in plan['methods'] if name.startswith('smpt-')]
    plan['smpt_configurations'] = {name: runner.SMPT_MODES[name] for name in smpt}
    plan['smpt_scheduling'] = {name: runner.smpt_scheduling(name) for name in smpt}
    required = {}
    for name, digest in read(RUNNER + '/files-sha256.json').items():
        required[RUNNER + '/source/' + name] = digest
    for q in manifest['queries']:
        for field in ('net', 'property', 'pnml', 'xml'):
            name = str((ROOT / plan['corpus'] / q[field]).resolve().relative_to(ROOT))
            required[name] = q[field + '_sha256']
        for branch in q['branches']:
            name = str((ROOT / plan['corpus'] / branch['path']).resolve().relative_to(ROOT))
            required[name] = branch['sha256']
    required[plan['corpus'] + '/manifest.json'] = plan['manifest_sha256']
    for tool in plan['native_tools'].values():
        required[str(Path(tool['binary']).relative_to(REMOTE))] = tool['binary_sha256']
    required[str(Path(plan['verifypn']['binary']).relative_to(REMOTE))] = plan['verifypn']['binary_sha256']
    required['vendor/venv/bin/python'] = prior_env['native_python_sha256']
    for name, tool in prior_env['tools'].items():
        path = str(Path(tool['path']).relative_to(REMOTE))
        if path.startswith('vendor/venv/'):
            path = RUNNER + '/source/' + path
        required[path] = tool['sha256']
    for name, digest in prior_env['smpt_source_sha256'].items():
        required['vendor/SMPT-portable/' + name] = digest
    required['scripts/analyze_application_expansion.py'] = sha('scripts/analyze_application_expansion.py')
    plan['required_file_sha256'] = required
    prefixes = ('results/linux-solver-walk-sparse-v2/', 'results/linux-solver-repeated-search-v1/',
                'research/smpt-minizinc-repair-v1/')
    preflight = {name: digest for name, digest in parent['required_file_sha256'].items() if name.startswith(prefixes)}
    preflight.update({RUNNER + '/' + name: sha(RUNNER + '/' + name)
                     for name in ('runner.tar.gz', 'provenance.json', 'files-sha256.json')})
    for name in ('research/check-smpt-minizinc-repair-v1.py', 'research/setup-smpt-minizinc-repair-v1.py',
                 'vendor/SMPT-portable/PORTABILITY.json', 'research/prepare-general-development-v3-linux-v1.py',
                 'research/run-general-development-v3-linux-v1.py', 'research/audit-general-development-v3-linux-v1.py'):
        preflight[name] = sha(name)
    plan['minizinc_identity_closure'] = dict(metadata='research/smpt-minizinc-repair-v1/metadata.json',
        bundle_manifest='research/smpt-minizinc-repair-v1/bundle-files-sha256.json',
        scope='Pinned metadata and bundle manifest transitively pin all 1136 bundle files, shared libraries, configuration presence/contents, inherited overrides, smoke artifacts and SMPT source. Pinned read-only preflight revalidates closure before launch.')
    evidence = ['research/application-walk-full-v1/plan.json', 'research/application-walk-full-v1/audit.json',
                'results/linux-application-walk-full-v1/environment.json', 'benchmarks/general-development-v3-selection.json',
                'research/general-development-v3-collection-audit.json', 'research/general-development-v3-imports/summary.json']
    plan['selection_evidence'] = {name: sha(name) for name in evidence}
    preflight.update(plan['selection_evidence'])
    plan['preflight_file_sha256'] = preflight
    FOLDER.mkdir(exist_ok=True)
    path = FOLDER / 'plan.json'
    with path.open('x') as stream:
        json.dump(plan, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(plan_sha256=sha(path), rows=1584, runtime_pins=len(required),
                         preflight_pins=len(preflight), capability_preflight='pending', deployed=False)))


if __name__ == '__main__':
    main()
