"""Register the complete comparison after retrieving a frozen candidate and smoke evidence.

No builds, benchmarks, deployment or remote operations. --smoke-evidence must
name JSON with status=passed and binary_sha256 matching the frozen candidate.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REMOTE = '/home/jules/experiments/pvass-publication/'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke-evidence', type=Path, required=True)
    args = parser.parse_args()
    template = json.loads((HERE / 'template.json').read_text())
    base = read(template['parent_plan'])
    audit = read(template['parent_audit'])
    assert audit['status'] == 'passed'
    assert audit['classification']['full']['definitive_by_method']['native-batched'] == 618
    manifest_path = ROOT / template['corpus'] / 'manifest.json'
    assert sha(manifest_path) == base['manifest_sha256']
    queries = json.loads(manifest_path.read_text())['queries']
    imported = [q for q in queries if q['status'] == 'imported']
    assert len(queries) == len({q['name'] for q in queries}) == 656 and len(imported) == 640
    assert len({tuple(b['sha256'] for b in q['branches']) for q in imported}) == 629
    assert len({(q['kind'], tuple(b['sha256'] for b in q['branches'])) for q in imported}) == 630
    candidate = ROOT / template['candidate_binary']
    directory = candidate.parent
    provenance = json.loads((directory / 'provenance.json').read_text())
    digest = sha(candidate)
    assert digest == provenance['binary_sha256']
    assert sha(directory / 'source.tar.gz') == provenance['source_sha256']
    source_hashes = json.loads((directory / 'source-files-sha256.json').read_text())
    with tarfile.open(directory / 'source.tar.gz') as archive:
        assert {m.name for m in archive.getmembers()} == set(source_hashes)
        for member in archive.getmembers():
            assert member.isfile()
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == source_hashes[member.name]
        walk = archive.extractfile('src/walk.rs').read().decode()
        main_source = archive.extractfile('src/main.rs').read().decode()
    for name, expected in [('DEFAULT_SEED', 0), ('DEFAULT_RESTART_STEPS', 10000), ('MAX_TRACE_STEPS', 100000)]:
        match = re.search(r'pub const ' + name + r': \w+ = ([\d_]+);', walk)
        assert match and int(match[1].replace('_', '')) == expected, name
    assert '"portfolio-walk" =>' in main_source
    assert sha(directory / 'tests.log') == provenance['test_log_sha256']
    assert sha(directory / 'build.log') == provenance['build_log_sha256']
    smoke_path = args.smoke_evidence.resolve()
    assert smoke_path.is_relative_to(ROOT)
    smoke = json.loads(smoke_path.read_text())
    assert smoke['status'] == 'passed' and smoke['binary_sha256'] == digest
    baseline = template['frozen_baseline_binary']
    previous = base['native_tools']['native-batched']
    assert previous['binary'] == REMOTE + baseline and previous['engine'] == 'portfolio-batched'
    assert sha(ROOT / baseline) == previous['binary_sha256']
    required = copy.deepcopy(base['required_file_sha256'])
    closure = read('results/runner-repeated-search-v2/files-sha256.json')
    assert len(closure) == 22
    for name, expected in closure.items():
        assert required[name] == expected and sha(ROOT / name) == expected, name
    for path in [candidate, directory / 'source.tar.gz', directory / 'source-files-sha256.json',
                 directory / 'provenance.json', directory / 'tests.log', directory / 'build.log',
                 directory / 'packaging-provenance.json',
                 ROOT / template['parent_plan'], ROOT / template['parent_audit'], smoke_path,
                 HERE / 'template.json', HERE / 'register.py', HERE / 'README.md',
                 HERE / 'smoke.py', HERE / 'smoke-plan.json', HERE / 'smoke-completion.json',
                 HERE / 'smoke-run.log', HERE / 'smoke-audit-notes.md',
                 ROOT / 'results/linux-application-walk-full-v1-smoke/environment.json',
                 ROOT / 'results/linux-application-walk-full-v1-smoke/runs.jsonl',
                 ROOT / 'research/run-application-walk-full-v1.py',
                 ROOT / 'scripts/analyze_application_expansion.py',
                 ROOT / 'research/audit-linux-application-expansion-v2.py']:
        required[str(path.relative_to(ROOT))] = sha(path)
    plan = copy.deepcopy(base)
    for key in ['corpus', 'properties', 'imported_properties', 'collection_failed_properties',
                'exact_ordered_branch_representatives', 'kind_preserving_representatives', 'expected_rows',
                'expected_solver_invocations', 'methods', 'buffer_agglomeration_methods',
                'seconds', 'repeat', 'max_states', 'linux_cpus', 'perf', 'memory_mib', 'outer_grace',
                'order_seed', 'output', 'walk_defaults']:
        plan[key] = template[key]
    for key, value in template['validation'].items():
        assert plan['validation'][key] == value
    tools = {}
    for label in ['native-walk', 'native-batched', 'native-frozen']:
        frozen = label == 'native-frozen'
        tools[label] = dict(engine=template['methods'][label],
                           binary=REMOTE + (baseline if frozen else template['candidate_binary']),
                           binary_sha256=previous['binary_sha256'] if frozen else digest)
    plan.update(native_binary=template['candidate_binary'], native_binary_sha256=digest,
                native_tools=tools, required_file_sha256=required,
                target_zero_trap_methods=[], target_path_potential_methods=[], geometric_branches_methods=[],
                smoke_evidence=str(smoke_path.relative_to(ROOT)),
                status='registered-not-deployed-not-started',
                scope='Complete unchanged656-slot cohort;640imports and16collection failures; no survivor filter or new/reserved inputs.',
                candidate_scope='Same frozen candidate binary portfolio-walk versus portfolio-batched; strongest previous frozen native configuration is repeated-search portfolio-batched+buffer (618/640), selected on prior development evidence.',
                runner_scope='Reuse exactly the prior22-file frozen runner closure, fail registration if any current runtime file differs. No silent shared-runner replacement.',
                walk_policy='Use verified compiled defaults seed0/restart10000/trace100000; no seed tuning or executable wrappers. Source and binary hashes identify the complete portfolio allocation.',
                followup='Audit complete3280-row artifact before conclusions; no automatic reruns or survivor qualification.',
                reporting='Keep656planned/640imported/629ordered-branch and630kind-preserving denominators, both parent cohorts and every family/failure. Native answers independently checked; competitors tool-reported. One seeded repetition is exploratory.',
                execution='Deploy only after all measuring sessions terminal; verify frozen binaries, original inputs, runner closure, smoke and MiniZinc configuration. Launch explicitly with an idle host and fresh output.')
    output = HERE / 'plan.json'
    with output.open('x') as stream:
        json.dump(plan, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(plan=str(output.relative_to(ROOT)), sha256=sha(output), expected_rows=3280,
                          candidate_sha256=digest, executed=False)))


if __name__ == '__main__':
    main()
