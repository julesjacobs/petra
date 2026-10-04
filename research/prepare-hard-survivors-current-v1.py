"""Prepare all eight historical survivors for current-tool300s qualification; no execution."""
import copy
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/hard-survivors-current-v1'
OLD = 'research/hard-survivors-v1-plan.json'
CURRENT = 'research/application-portfolio-comparison-v1-plan.json'
SOURCE = 'benchmarks/hard-survivors-v1/manifest.json'
METHODS = ['native-buffer', 'native-batched', 'verifypn-default', 'smpt-full-portable']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    old, current, manifest = read(OLD), read(CURRENT), read(SOURCE)
    assert sha(ROOT / SOURCE) == old['manifest_sha256']
    assert old['parent_properties'] == 620 and old['source_properties'] == 69
    assert old['properties'] == len(manifest['queries']) == 8
    prior = read('research/linux-hard-survivors-v1-verification.json')
    rows = prior['full_rows']
    assert len(rows) == 32 and {r['query'] for r in rows} == {q['name'] for q in manifest['queries']}
    OUT.mkdir()
    corpus = OUT / 'corpus'
    corpus.mkdir()
    queries = copy.deepcopy(manifest['queries'])
    inputs = {}
    for q in queries:
        assert q['status'] == 'imported'
        q['family'] = q['suite']
        q['family_grouping_scope'] = 'Existing suite label; no additional family taxonomy inferred'
        for key in ['pnml', 'xml', 'net', 'property', 'source_lola_local', 'source_formula_local', 'source_mapping']:
            if key not in q:
                continue
            source = ((ROOT / SOURCE).parent / q[key]).resolve()
            digest_key = key.removesuffix('_local') + '_sha256'
            assert sha(source) == q[digest_key], str(source)
            inputs[str(source.relative_to(ROOT))] = q[digest_key]
            q[key] = os.path.relpath(source, corpus)
        for b in q['branches']:
            source = ((ROOT / SOURCE).parent / b['path']).resolve()
            assert sha(source) == b['sha256']
            inputs[str(source.relative_to(ROOT))] = b['sha256']
            b['path'] = os.path.relpath(source, corpus)
    save(corpus / 'manifest.json', dict(format='historical-survivor-requalification-v1',
         expected_properties=8, source_manifest=SOURCE, source_manifest_sha256=sha(ROOT / SOURCE),
         selection='All eight original hard-survivors-v1 cases, irrespective of later answers.', queries=queries))
    history_paths = [OLD, SOURCE, 'benchmarks/hard-survivors-v1/selection-audit.json',
                     'research/linux-hard-survivors-v1-verification.json',
                     'results/linux-hard-survivors-v1/environment.json',
                     'results/linux-hard-survivors-v1/runs.jsonl', CURRENT]
    identities = {name: sha(ROOT / name) for name in history_paths}
    save(OUT / 'history.json', dict(parent_properties=620, screening_properties=69, selected_properties=8,
         original_names=[q['name'] for q in manifest['queries']], original_selection_audit=read('benchmarks/hard-survivors-v1/selection-audit.json'),
         historical_300s_rows=rows, historical_audit_status=prior['status'], source_sha256=identities,
         scope='All original failures and selection decisions retained; new dependencies and candidates do not retroactively repair prior results.'))
    plan = copy.deepcopy(current)
    required = {**current['required_file_sha256'], **identities, **inputs}
    for name in ['research/prepare-hard-survivors-current-v1.py', 'research/run-hard-survivors-current-v1.py',
                 'research/run-application-ladder-qualification-v1.py',
                 'research/audit-linux-application-expansion-v1.py', 'scripts/analyze_application_expansion.py',
                 'research/hard-survivors-current-v1/corpus/manifest.json', 'research/hard-survivors-current-v1/history.json']:
        required[name] = sha(ROOT / name)
    plan.update(corpus='research/hard-survivors-current-v1/corpus',
         manifest_sha256=sha(corpus / 'manifest.json'), properties=8, imported_properties=8,
         collection_failed_properties=0, parent_properties=620, source_properties=69,
         exact_ordered_branch_representatives=len({tuple(b['sha256'] for b in q['branches']) for q in queries}),
         expected_rows=32, methods={m:current['methods'][m] for m in METHODS},
         native_tools={m:current['native_tools'][m] for m in METHODS if m.startswith('native-')},
         seconds=300, order_seed=20261112, output='results/linux-hard-survivors-current-v1',
         required_file_sha256=required, selection_evidence=identities,
         status='prepared-not-deployed-not-launched',
         input_scope=old['input_scope'],
         scope='Current-tool300s requalification of all eight historical outcome-selected survivors. Preserve620parent/69screened/8selected denominators.',
         candidate_scope='Frozen repeated-search native focused+buffer and batched+buffer; VerifyPN default; repaired SMPT full portable.',
         execution='Prepare only. Launch explicitly after prior measurement session terminal, idle-host and full identity checks. No automatic deployment.',
         reporting='All32rows; six FastForward and two pigeonhole cases separately. Prior failures remain in history.json. One repetition qualifies recovery, not stable speed or general superiority.',
         followup='No automatic survivor filtering or follow-up. Investigate contradictions and operational failures before interpretation.',
         reserved='Only unchanged eight previously acquired development cases; no reserved family payloads accessed.')
    save(OUT / 'plan.json', plan)
    print(json.dumps(dict(plan=str((OUT/'plan.json').relative_to(ROOT)),sha256=sha(OUT/'plan.json'),queries=8,rows=32,executed=False)))


if __name__ == '__main__':
    main()
