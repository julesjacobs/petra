#!/usr/bin/env python3
"""Read-only corpus audit; writes reports in research and never runs solvers."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'benchmarks/application-parameter-ladders-v2'
SELECTION = ROOT / 'benchmarks/application-parameter-ladders-v2-selection.json'
EXPECTED_SELECTION = 'e729cd00a2facdddcb0273dda32915b0f5a78f17d6e70185a1cb172a80fec605'
REPORT = ROOT / 'research/application-parameter-ladders-v2-audit.json'


def audit():
    issues, identities, cache = [], [], {}

    def label(path):
        path = path.resolve()
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    def check(condition, message):
        if not condition:
            issues.append(message)

    def digest(path):
        path = path.resolve()
        if path not in cache:
            with path.open('rb') as stream:
                cache[path] = hashlib.file_digest(stream, 'sha256').hexdigest()
        return cache[path]

    def identity(path, expected, evidence):
        actual = digest(path)
        check(actual == expected, f'Identity mismatch: {label(path)}')
        identities.append(dict(path=label(path), expected=expected, actual=actual,
                               valid=actual == expected, evidence=evidence))
        return actual

    def read(path):
        return json.loads(path.read_text())

    selection = read(SELECTION)
    manifest = read(CORPUS / 'manifest.json')
    outcomes = read(CORPUS / 'collection-outcomes.json')
    archives = read(CORPUS / 'archive-checksums.json')
    provenance = read(CORPUS / 'collector-provenance.json')
    identity(SELECTION, EXPECTED_SELECTION, 'preregistered selection')
    identity(CORPUS / 'selection.json', EXPECTED_SELECTION, 'collected selection copy')
    check(manifest['selection_sha256'] == archives['selection_sha256'] == EXPECTED_SELECTION,
          'Recorded selection hashes differ')
    identity(ROOT / selection['index_path'], selection['index_sha256'], 'source index')
    for path, expected in selection['prior_selections'].items():
        identity(ROOT / path, expected, 'prior selection')
    reservation = selection['reserved_selection']
    identity(ROOT / reservation['path'], reservation['sha256'], 'reservation metadata')
    reserved = set(read(ROOT / reservation['path'])['reserved_families'])
    for path in selection['prior_selections']:
        for row in read(ROOT / path)['models']:
            if 'evaluation' in row.get('split', ''):
                reserved.add(row['family'])
    check(reserved == set(selection['reserved_families_excluded']) and len(reserved) == 22,
          'Reserved-family exclusion differs')
    for name, expected in provenance['sources'].items():
        identity(CORPUS / 'collector-source' / name, expected, 'collector source snapshot')
    check(manifest['collector_sha256'] == provenance['sources']['collect_stress_mcc.py']
          == selection['collector']['sha256'], 'Collector identity differs')
    check(manifest['importer_sha256'] == provenance['sources']['smpt_import.py'],
          'Importer identity differs')
    runtime = provenance['runtime']
    identity(Path(runtime['python_executable_resolved']), runtime['python_sha256'],
             'recorded collector runtime')
    limits = manifest['per_model_limits']
    check(limits == dict(seconds=120.0, memory_bytes=2048*1024**2,
                        archive_bytes=256*1024**2, expanded_bytes=1024**3,
                        artifact_bytes=1024**3), 'Acquisition limits differ')

    models = {m['name']: m for m in selection['models']}
    queries = manifest['queries']
    check(len(models) == 29 and selection['expected_models'] == 29, 'Model denominator differs')
    check(manifest['collection_complete'] is True, 'Collection incomplete')
    check(manifest['expected_properties'] == selection['expected_properties'] == len(queries) == 464,
          'Property denominator differs')
    expected_slots = {(name, i) for name in models for i in range(16)}
    slots = Counter((q['instance'], q['property_slot']) for q in queries)
    check(set(slots) == expected_slots and set(slots.values()) == {1}, 'Slots missing or duplicated')
    check(len({q['name'] for q in queries}) == 464, 'Query names duplicated')
    status = Counter(q['status'] for q in queries)
    check(status == {'imported': 448, 'unsupported': 16}, 'Unexpected collection outcomes')
    check(not ({q['family'] for q in queries} | {m['family'] for m in models.values()}) & reserved,
          'Reserved family present')
    check(len(outcomes) == len(models) and {o['model'] for o in outcomes} == set(models),
          'Per-model outcomes differ')
    by_model = defaultdict(list)
    groups = defaultdict(list)
    input_paths = set()
    for q in queries:
        by_model[q['instance']].append(q)
        check(q['planned'] is True and q['family'] == models[q['instance']]['family'],
              f'Planned/family metadata differs: {q["name"]}')
        check(q['name'] == f'{q["instance"]}__RC{q["property_slot"]:02}', 'Slot name differs')
        if q['status'] != 'imported':
            check(q['instance'] == 'TokenRing-PT-050' and q['observed'] is False
                  and q['error'] == 'ValueError: Archive expanded-size limit exceeded'
                  and not q.get('branches'), f'Unexpected failed slot: {q["name"]}')
            continue
        check(q['observed'] is True and q['kind'] in {'EF', 'AG'}, 'Imported metadata differs')
        pairs = [(q[k], q[k+'_sha256']) for k in ('pnml', 'xml', 'net', 'property')]
        pairs.extend((b['path'], b['sha256']) for b in q['branches'])
        check(bool(q['branches']), f'No canonical branches: {q["name"]}')
        for relative, expected in pairs:
            path = (CORPUS / relative).resolve()
            check(path.is_relative_to(CORPUS), f'Unexpected input path: {relative}')
            if path not in input_paths:
                identity(path, expected, 'collected manifest input')
                input_paths.add(path)
            else:
                check(digest(path) == expected, f'Conflicting shared input digest: {relative}')
        groups[tuple(b['sha256'] for b in q['branches'])].append(q)

    check(len(archives['archives']) == 29, 'Archive denominator differs')
    check({a['model'] for a in archives['archives']} == set(models), 'Archive names differ')
    for row in archives['archives']:
        path = CORPUS / 'archives' / (row['model'] + '.tgz')
        identity(path, row['sha256'], 'downloaded archive checksum')
        check(path.stat().st_size == row['bytes'], f'Archive size differs: {row["model"]}')
        check(row['url'] == models[row['model']]['url'], 'Archive source URL differs')
    failure_evidence = []
    for outcome in outcomes:
        rows = by_model[outcome['model']]
        count = sum(q['status'] == 'imported' for q in rows)
        check(outcome['planned_properties'] == 16 and outcome['imported_properties'] == count,
              'Outcome count differs')
        check(outcome['success'] is (count == 16), 'Outcome success differs')
        if not outcome['success']:
            progress = outcome['progress']
            check(progress['stage_failed'] == 'extract' and outcome['model'] == 'TokenRing-PT-050'
                  and progress['error'] == rows[0]['error'], 'Failure evidence differs')
            check(outcome['resources']['exit_code'] == 1, 'Failed worker exit differs')
            failure_evidence.append(outcome)

    earlier_groups = defaultdict(list)
    comparison_manifests = []
    for record in selection['prior_metadata_inventory']:
        path = ROOT / record['path']
        if path.name != 'manifest.json':
            continue
        identity(path, record['sha256'], 'preselection corpus metadata')
        data = read(path)
        rows = data.get('queries', []) if isinstance(data, dict) else []
        included = excluded = 0
        for q in rows:
            if q.get('family') in reserved or 'evaluation' in q.get('suite', ''):
                excluded += 1
                continue
            if q.get('status') != 'imported' or not q.get('branches'):
                continue
            included += 1
            for b in q['branches']:
                identity(path.parent / b['path'], b['sha256'], 'earlier development branch')
            key = tuple(b['sha256'] for b in q['branches'])
            earlier_groups[key].append(dict(manifest=label(path), query=q['name'], kind=q['kind']))
        comparison_manifests.append(dict(path=label(path), sha256=digest(path),
                                         included_imported_queries=included,
                                         excluded_reserved_or_evaluation_queries=excluded))
    duplicate_groups = [dict(ordered_branch_sha256=list(key),
                             queries=[dict(name=q['name'], kind=q['kind']) for q in rows])
                        for key, rows in groups.items() if len(rows) > 1]
    property_representatives = len({(q['kind'], key) for key, rows in groups.items() for q in rows})
    cross_matches = [dict(ordered_branch_sha256=list(key),
                          current=[dict(name=q['name'], kind=q['kind']) for q in rows],
                          earlier=earlier_groups[key])
                     for key, rows in groups.items() if key in earlier_groups]

    inventory = []
    for path in sorted(CORPUS.rglob('*')):
        if path.is_file():
            check(not path.is_symlink(), f'Unexpected corpus symlink: {path}')
            inventory.append(dict(path=label(path), bytes=path.stat().st_size, sha256=digest(path)))
    summary = dict(status='passed' if not issues else 'failed', issues=issues,
                   selection_sha256=EXPECTED_SELECTION, manifest_sha256=digest(CORPUS/'manifest.json'),
                   audit_script_sha256=digest(Path(__file__)), planned_models=29, planned_slots=464,
                   collection_status=dict(status), imported_models=sum(o['success'] for o in outcomes),
                   reserved_families_excluded=sorted(reserved),
                   input_files=len(input_paths), input_bytes=sum(p.stat().st_size for p in input_paths),
                   all_corpus_files=len(inventory), all_corpus_bytes=sum(r['bytes'] for r in inventory),
                   archive_files=len(archives['archives']),
                   models=[dict(name=name, family=models[name]['family'],
                                imported=sum(q['status']=='imported' for q in rows),
                                places=rows[0].get('places'), transitions=rows[0].get('transitions'))
                           for name, rows in by_model.items()],
                   exact_ordered_branch_representatives=len(groups),
                   exact_ordered_branch_and_kind_representatives=property_representatives,
                   exact_ordered_branch_duplicate_groups=duplicate_groups,
                   exact_ordered_branch_cross_corpus_matches=cross_matches,
                   comparison_manifests=comparison_manifests, failure_evidence=failure_evidence,
                   identities=identities, corpus_file_inventory=inventory,
                   scope='Read-only byte identities and metadata consistency. Ordered branch SHA256 tuples identify exact canonical reachability-query bytes; original EF/AG kinds are retained separately. No graph-equivalence audit, importer semantic revalidation, solver run, or hardness measurement. Reserved model/property/archive payloads were not read. The recorded expanded-archive rejection was not reproduced by decompressing the failed archive.')
    REPORT.write_text(json.dumps(summary, indent=2)+'\n')
    report = ROOT / 'research/application-parameter-ladders-v2-audit.md'
    report.write_text(f'''# Application parameter ladders v2: collection audit

**{summary['status'].upper()}: 448/464 slots imported from 28/29 models.** All 464 preregistered slots are retained. TokenRing-PT-050 contributes 16 unavailable slots: its recorded extraction failure exceeded the 1 GiB expanded-archive limit. Its downloaded archive and partial files remain preserved and hashed. This audit checked the recorded failure evidence; it did not decompress that archive again to reproduce the limit.

The frozen selection remains `{EXPECTED_SELECTION}`. The collected manifest is `{summary['manifest_sha256']}`. All 22 reserved/evaluation families are excluded; no reserved payloads were read.

Verified all 29 downloaded archive checksums and URLs, collector/importer snapshots and runtime identity, every manifest-referenced input hash ({len(input_paths)} distinct files / {summary['input_bytes']} bytes), and the complete retained corpus inventory ({len(inventory)} files / {summary['all_corpus_bytes']} bytes, including failed-model partial files). Source selection, per-model limits, property slots, and collection outcomes agree.

The 448 imported properties have **{len(groups)} exact ordered-branch representatives**, in {len(duplicate_groups)} duplicate groups containing {sum(len(g['queries']) for g in duplicate_groups)} properties. There are **{len(cross_matches)} matching signatures** against the earlier development manifests listed in the JSON report, including both FastForward imports, earlier MCC development/stress/application sets, and SMPT classic. Reserved/evaluation rows are filtered before branch files are read. Earlier development views overlap and are not additional independent datasets.

Duplicates mean identical ordered canonical branch bytes. They do not establish graph equivalence or absence of renamed/reordered duplicates. Including EF/AG kind gives **{property_representatives} original-property representatives**: FMS-PT-50000 RC01 (AG) and RC12 (EF) share branches but have opposite property polarity. Keep the full 464-slot denominator and report duplicate-aware coverage separately, retaining the 16 unavailable slots in both views; acquisition failure is not solver difficulty.

This is an artifact-identity audit, not an independent proof of importer semantics or benchmark hardness. No solver ran. Reproduce with `python3 research/audit-application-parameter-ladders-v2.py`; detailed identities, all-file hashes, duplicate membership, comparison exclusions, and failure evidence are in `research/application-parameter-ladders-v2-audit.json`.

Audit issues: {json.dumps(issues)}.
''')
    print(json.dumps({k:summary[k] for k in ['status','issues','planned_slots','collection_status',
                                            'input_files','input_bytes','all_corpus_files','all_corpus_bytes',
                                            'exact_ordered_branch_representatives']}))
    print('Internal duplicate groups:', len(duplicate_groups), 'cross-corpus matches:', len(cross_matches))
    return not issues


if __name__ == '__main__':
    raise SystemExit(0 if audit() else 1)
