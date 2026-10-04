"""Register qualification locally; never launch a solver or contact Linux."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/application-ladder-qualification-v1'
PARENT_PLAN = 'research/application-portfolio-comparison-v1-plan.json'
ANALYSIS = 'research/application-parameter-ladders-v2-screen-analysis.json'
MANIFEST = 'benchmarks/application-parameter-ladders-v2/manifest.json'
METHODS = ['native-buffer', 'native-batched', 'verifypn-default', 'smpt-full-portable']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def register(seconds, names, evidence):
    if seconds == 300:
        for name, digest in read(BASE / 'selection.json')['source'].items():
            assert sha(ROOT / name) == digest, name
    plan = copy.deepcopy(read(ROOT / PARENT_PLAN))
    parent = read(ROOT / MANIFEST)
    corpus = BASE / f'stage-{seconds}'
    corpus.mkdir()
    original = {q['name']: q for q in parent['queries']}
    queries = []
    for name in names:
        q = copy.deepcopy(original[name])
        assert q['status'] == 'imported'
        q['qualification_parent'] = MANIFEST
        for key in ('pnml', 'xml', 'net', 'property'):
            q[key] = os.path.relpath((ROOT / MANIFEST).parent / q[key], corpus)
        for b in q['branches']:
            b['path'] = os.path.relpath((ROOT / MANIFEST).parent / b['path'], corpus)
        queries.append(q)
    manifest = dict(format='application-qualification-selection-v1',
                    parent_manifest=MANIFEST, parent_manifest_sha256=sha(ROOT / MANIFEST),
                    expected_properties=len(names), queries=queries)
    save(corpus / 'manifest.json', manifest)
    required = plan['required_file_sha256']
    if seconds == 300:
        required.update(evidence)
    for path in [ROOT / MANIFEST, ROOT / ANALYSIS, ROOT / PARENT_PLAN,
                 BASE / 'selection.json', BASE / 'protocol.json',
                 ROOT / 'research/prepare-application-ladder-qualification-v1.py',
                 ROOT / 'research/run-application-ladder-qualification-v1.py',
                 ROOT / 'research/audit-linux-application-expansion-v1.py',
                 ROOT / 'scripts/analyze_application_expansion.py', corpus / 'manifest.json']:
        required[str(path.relative_to(ROOT))] = sha(path)
    plan.update(corpus=str(corpus.relative_to(ROOT)), manifest_sha256=sha(corpus / 'manifest.json'),
                properties=len(names), expected_rows=4 * len(names), imported_properties=len(names),
                collection_failed_properties=0, source_properties=464, parent_properties=464,
                exact_ordered_branch_representatives=len({tuple(b['sha256'] for b in q['branches']) for q in queries}),
                native_tools={m: plan['native_tools'][m] for m in METHODS if m.startswith('native-')},
                methods={m: plan['methods'][m] for m in METHODS}, seconds=seconds,
                order_seed=20261110 if seconds == 60 else 20261111,
                output=f'results/linux-application-ladder-qualification-v1-{seconds}',
                selected_queries=names, selection_evidence=evidence,
                qualification_parent=dict(slots=464, imports=448, collection_failures=16,
                                          representatives=442, original_selected=13),
                status='registered-not-started' if names else 'complete-no-joint-survivors',
                scope='Outcome-selected qualification of all13original ladder joint failures; preserve full464-slot parent.',
                candidate_scope='Frozen native focused+buffer and batched+buffer, VerifyPN default, repaired SMPT full portable.',
                reporting='Keep all52original selected screen rows and64parent collection-failure rows. Report60s recovery for all13, then300s joint survivors separately. Never substitute into prior timings.',
                followup='After complete audited60s results, run300s only for cases with no strictly accepted definitive answer in any of these four configurations. Errors remain eligible; disagreements block advancement.',
                execution='Prepared only. Deployment and launch require terminal predecessor evidence, a free host, registered identity preflight and unchanged dependencies.')
    path = BASE / f'plan-{seconds}.json'
    save(path, plan)
    return dict(plan=str(path.relative_to(ROOT)), sha256=sha(path), properties=len(names), rows=4 * len(names))


def initial():
    analysis = read(ROOT / ANALYSIS)
    assert analysis['validity'] == 'complete_consistent_screen'
    names = analysis['selections']['all_unresolved']
    assert len(names) == len(set(names)) == 13
    assert analysis['full']['properties'] == 464 and analysis['imported']['properties'] == 448
    for name, digest in analysis['sources'].items():
        assert sha(ROOT / name) == digest, name
    rows = analysis['runs']
    failed = set(analysis['selections']['collection_unavailable'])
    BASE.mkdir()
    evidence = {ANALYSIS: sha(ROOT / ANALYSIS), MANIFEST: sha(ROOT / MANIFEST),
                PARENT_PLAN: sha(ROOT / PARENT_PLAN), **analysis['sources']}
    selection = dict(source=evidence, names=names, parent_full=analysis['full'],
                     parent_imported=analysis['imported'], parent_representatives=analysis['representatives'],
                     selected_cases=[c for c in analysis['cases'] if c['query'] in names],
                     prior_selected_rows=[r for r in rows if r['query'] in names],
                     parent_collection_failure_rows=[r for r in rows if r['query'] in failed])
    assert len(selection['prior_selected_rows']) == 52
    assert len(selection['parent_collection_failure_rows']) == 64
    save(BASE / 'selection.json', selection)
    save(BASE / 'protocol.json', dict(
        status='prepared-not-deployed-not-launched', initial_seconds=60, survivor_seconds=300,
        methods=METHODS, repeat=1, linux_cpus=[8], perf=True, memory_mib=2048, outer_grace=0,
        original_selection=names, original_selected=13, parent_slots=464, parent_imports=448,
        parent_collection_failures=16, parent_representatives=442,
        stage_300_rule='All audited60s cases with classification no_method_definitive, including operational failures. Conflicts or incomplete audit block selection. No new5s comparison outcome changes original13.',
        validation='Existing bounded60s/2GiB independent native checks excluded from solver timing; checker failures remain unresolved; external answers tool-reported.',
        interpretation='Outcome-selected development qualification. Timeouts and errors do not establish intrinsic search hardness. Parsing/reduction/search attribution requires uncensored phase evidence.',
        reserved='No new families or payloads accessed. Only previously acquired SharedMemory and TokenRing selections.',
        execution='No automatic chaining. Register300s survivors locally only after confirmed terminal60s run, complete retrieval and successful artifact audit. Deploy and launch explicitly afterward.'))
    print(json.dumps(register(60, names, evidence)))


def advance(receipt_path):
    plan_path = BASE / 'plan-60.json'
    plan = read(plan_path)
    for name in ('research/prepare-application-ladder-qualification-v1.py',
                 'research/run-application-ladder-qualification-v1.py',
                 'research/audit-linux-application-expansion-v1.py',
                 'scripts/analyze_application_expansion.py'):
        assert sha(ROOT / name) == plan['required_file_sha256'][name], name
    receipt = read(receipt_path)
    assert receipt['terminal'] is True and type(receipt['exit_code']) is int
    assert receipt['output'] == plan['output']
    results = ROOT / plan['output']
    for name in ('environment.json', 'runs.jsonl'):
        assert sha(results / name) == receipt['sha256'][name], name
    spec = importlib.util.spec_from_file_location('qualification_auditor', ROOT / 'research/audit-linux-application-expansion-v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.safe_audit(ROOT, plan_path, results)
    save(BASE / 'stage-60-audit.json', report)
    assert report['status'] == 'passed', 'Complete artifact audit required; retain failures and investigate'
    classification = report['classification']
    assert classification['validity'] == 'complete_consistent_screen'
    names = classification['selections']['all_unresolved']
    assert set(names) <= set(read(BASE / 'selection.json')['names'])
    save(BASE / 'stage-60-completion-receipt.json', receipt)
    evidence = {str(p.relative_to(ROOT)): sha(p) for p in
                [plan_path, BASE / 'stage-60-audit.json', BASE / 'stage-60-completion-receipt.json',
                 results / 'environment.json', results / 'runs.jsonl']}
    print(json.dumps(register(300, names, evidence)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--advance-after-terminal-60', type=Path)
    args = parser.parse_args()
    advance(args.advance_after_terminal_60) if args.advance_after_terminal_60 else initial()
