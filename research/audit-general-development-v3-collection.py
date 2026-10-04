#!/usr/bin/env python3
"""Audit collected bytes and metadata after acquisition; never run importers/solvers."""
from collections import Counter, defaultdict
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import traceback

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'benchmarks/general-development-v3'
SELECTION = ROOT / 'benchmarks/general-development-v3-selection.json'
EXPECTED_SELECTION = '8b0c3496bc31f6fecf4cb54ff49a8d826b10feb7387ea5a1de7f562d1616fc90'
REPORT = ROOT / 'research/general-development-v3-collection-audit.json'
SCOPE = ('Byte identities and recorded metadata consistency only. No importer semantic '
         'revalidation, graph equivalence, solver execution or hardness measurement. '
         'Prior-corpus overlaps compare branch hashes recorded in frozen metadata; earlier '
         'branch payloads are not rehashed. No reserved model/property/archive payloads '
         'are read. Resource limits are recorded enforcement/sampling evidence, not '
         'independent reconstruction of historical peak memory or wall time.')


def family_group(name):
    for prefix in ('RERS', 'IBM', 'DLC'):
        if name.startswith(prefix):
            return prefix
    for part in ('ProductionCell', 'GPU'):
        if part in name:
            return part
    return name


def audit():
    issues, identities, cache = [], [], {}
    summary = dict(planned_models=11, planned_slots=176, scope=SCOPE)

    def check(ok, message):
        if not ok:
            issues.append(message)
        return bool(ok)

    @contextmanager
    def section(name):
        try:
            yield
        except Exception as error:
            issues.append(f'{name}: {type(error).__name__}: {error}')
            summary.setdefault('exceptions', []).append(dict(section=name, traceback=traceback.format_exc()))

    def label(path):
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    def safe(path, base=ROOT):
        path = Path(path)
        if not path.is_absolute():
            path = base / path
        if not path.is_relative_to(base) or '..' in path.parts:
            raise ValueError(f'Path outside allowed root: {path}')
        for part in (path, *path.parents):
            if part == base.parent:
                break
            if part.is_symlink():
                raise ValueError(f'Symlink refused: {part}')
        return path

    def digest(path):
        if path not in cache:
            with path.open('rb') as stream:
                cache[path] = hashlib.file_digest(stream, 'sha256').hexdigest()
        return cache[path]

    def identity(path, expected, evidence):
        record = dict(path=label(path), expected=expected, evidence=evidence, valid=False)
        identities.append(record)
        try:
            actual = digest(path)
            record.update(actual=actual, valid=actual == expected)
            check(actual == expected, f'Identity mismatch: {label(path)}')
            return actual
        except Exception as error:
            record['error'] = f'{type(error).__name__}: {error}'
            issues.append(f'Unreadable identity: {label(path)}: {record["error"]}')
            return None

    def read(path, default=None):
        try:
            value = json.loads(safe(path).read_text())
            expected_type = list if isinstance(default, list) else dict
            if not isinstance(value, expected_type):
                raise ValueError(f'Expected {expected_type.__name__}, got {type(value).__name__}')
            return value
        except Exception as error:
            issues.append(f'Cannot read {label(path)}: {type(error).__name__}: {error}')
            return {} if default is None else default

    selection = read(SELECTION)
    manifest = read(CORPUS / 'manifest.json')
    outcomes = read(CORPUS / 'collection-outcomes.json', [])
    archives = read(CORPUS / 'archive-checksums.json')
    provenance = read(CORPUS / 'collector-provenance.json')
    models, prior_metadata = {}, {}
    reserved = set(selection.get('reserved_families_excluded', []))
    reserved_groups = set(selection.get('reserved_groups_excluded', []))
    with section('selection and provenance'):
        identity(safe(SELECTION), EXPECTED_SELECTION, 'frozen selection')
        identity(safe(CORPUS / 'selection.json'), EXPECTED_SELECTION, 'collected selection copy')
        check(manifest['selection_sha256'] == archives['selection_sha256'] == EXPECTED_SELECTION,
              'Recorded selection identities differ')
        models = {m['name']: m for m in selection['models']}
        check(len(models) == len(selection['models']) == selection['expected_models'] == 11,
              'Model denominator differs')
        check(selection['expected_properties'] == 176 and selection['property_slots'] == list(range(16)),
              'Frozen property denominator differs')
        check(len(reserved) == len(reserved_groups) == 22, 'Reservation exclusion denominator differs')
        for model in models.values():
            check(model['family'] not in reserved and family_group(model['family']) not in reserved_groups,
                  f'Reserved family/group selected: {model["name"]}')
            check(model['expected_properties'] == 16, f'Property count differs: {model["name"]}')
        for relative, expected in selection['input_sha256'].items():
            path = safe(Path(relative))
            identity(path, expected, 'frozen selection input metadata')
            if path.suffix == '.json':
                data = read(path)
                for row in data.get('prior_metadata_inventory', []):
                    if Path(row['path']).name == 'manifest.json':
                        old = prior_metadata.setdefault(row['path'], row['sha256'])
                        check(old == row['sha256'], f'Conflicting prior metadata identity: {row["path"]}')
                earlier = {m['name'] for m in data.get('models', []) if 'name' in m}
                check(not earlier & set(models), f'Previously indexed model reused in {relative}')
        identity(safe(ROOT / 'research/select-general-development-v3.py'), selection['selector_sha256'],
                 'frozen selector source')
        check(manifest['collection_complete'] is True, 'Collection incomplete')
        check(manifest['source'] == selection['source'], 'Source URL differs')
        check(manifest['suite'] == 'stress-development', 'Corpus split differs')
        sources = provenance['sources']
        check(set(sources) == {'collect_stress_mcc.py', 'smpt_import.py', 'process_runner.py'},
              'Collector snapshot file set differs')
        for name, expected in sources.items():
            identity(safe(Path(name), CORPUS / 'collector-source'), expected, 'collector snapshot')
        check(manifest['collector_sha256'] == sources['collect_stress_mcc.py'] and
              manifest['importer_sha256'] == sources['smpt_import.py'], 'Collector/importer identity differs')
        runtime = provenance['runtime']
        # The interpreter may resolve outside the workspace; this is the recorded executable only.
        identity(Path(runtime['python_executable_resolved']), runtime['python_sha256'], 'collector runtime')
        expected_limits = dict(seconds=120.0, memory_bytes=2048 * 1024**2,
                               archive_bytes=256 * 1024**2, expanded_bytes=1024**3,
                               artifact_bytes=1024**3)
        check(manifest['per_model_limits'] == expected_limits, 'Acquisition limits differ')
    queries = manifest.get('queries', [])
    if not isinstance(queries, list):
        check(False, 'Manifest queries is not an array')
        queries = []
    by_model, groups, inputs = defaultdict(list), defaultdict(list), set()
    with section('full slot denominator'):
        slots = Counter((q['instance'], q['property_slot']) for q in queries)
        expected_slots = {(name, i) for name in models for i in range(16)}
        check(set(slots) == expected_slots and all(n == 1 for n in slots.values()), 'Slots missing or duplicated')
        check(len(queries) == manifest['expected_properties'] == 176, 'Collected property denominator differs')
        check(len({q['name'] for q in queries}) == 176, 'Query names duplicated')
        summary['collection_status'] = dict(Counter(q['status'] for q in queries))
    for index, q in enumerate(queries):
        with section(f'query {index}'):
            name = q['name']
            model = models[q['instance']]
            by_model[q['instance']].append(q)
            check(q['planned'] is True and q['family'] == model['family'] and
                  q['family_group'] == model['family_group'] and q['suite'] == 'stress-development',
                  f'Query selection metadata differs: {name}')
            check(name == f'{q["instance"]}__RC{q["property_slot"]:02}', f'Slot name differs: {name}')
            check(q['status'] in {'imported', 'unsupported'}, f'Unexpected slot status: {name}')
            pairs = [(q[k], q[k + '_sha256']) for k in ('pnml', 'xml', 'net', 'property') if k in q]
            pairs += [(b['path'], b['sha256']) for b in q.get('branches', [])]
            for relative, expected in pairs:
                path = safe(Path(relative), CORPUS)
                identity(path, expected, f'manifest input: {name}')
                inputs.add(path)
            if q['status'] == 'imported':
                check(q['observed'] is True and q['kind'] in {'EF', 'AG'}, f'Imported metadata differs: {name}')
                check(all(k in q for k in ('pnml', 'xml', 'net', 'property', 'branches')),
                      f'Missing imported inputs: {name}')
                # An empty disjunction is a valid, unsatisfiable canonical target.
                groups[tuple(b['sha256'] for b in q['branches'])].append(dict(name=name, kind=q['kind']))
            else:
                check(bool(q.get('error')) and q['error'] != 'collection not attempted',
                      f'Unavailable slot lacks terminal failure: {name}')
    archive_rows = archives.get('archives', [])
    if not isinstance(archive_rows, list):
        check(False, 'Archive identities is not an array')
        archive_rows = []
    with section('archive denominator'):
        names = [a['model'] for a in archive_rows]
        check(len(names) == len(set(names)) and set(names) <= set(models), 'Archive identities duplicated/unplanned')
        expected_archives = {o['model'] for o in outcomes if o.get('progress', {}).get('archive')}
        check(set(names) == expected_archives, 'Downloaded archive inventory differs from worker progress')
    archive_by_model = {a.get('model'): a for a in archive_rows if isinstance(a, dict) and isinstance(a.get('model'), str)}
    for row in archive_rows:
        with section(f'archive row {archive_rows.index(row)}'):
            path = safe(CORPUS / 'archives' / (row['model'] + '.tgz'))
            identity(path, row['sha256'], 'downloaded archive')
            check(path.stat().st_size == row['bytes'] <= 256 * 1024**2, f'Archive size differs: {row["model"]}')
            check(row['url'] == models[row['model']]['url'], f'Archive URL differs: {row["model"]}')
    failure_evidence = []
    with section('outcome denominator'):
        check(len(outcomes) == 11 and [o['model'] for o in outcomes] == list(models),
              'Per-model outcomes missing, duplicated or reordered')
    for outcome in outcomes:
        with section(f'outcome row {outcomes.index(outcome)}'):
            name = outcome['model']
            job = safe(CORPUS / 'collection' / name)
            request, progress = read(job / 'request.json'), read(job / 'progress.json')
            usage = outcome['resources']
            check(progress == outcome['progress'], f'Worker progress differs: {name}')
            check(request['model'] == models[name] and Path(request['output']) == CORPUS and
                  Path(request['job']) == job, f'Worker request differs: {name}')
            for key in ('memory_bytes', 'archive_bytes', 'expanded_bytes', 'artifact_bytes'):
                check(request[key] == manifest['per_model_limits'][key], f'Worker limit differs: {name}/{key}')
            check(usage['seconds_limit'] == 120 and usage['memory_limit_bytes'] == 2048 * 1024**2,
                  f'Worker resource limits differ: {name}')
            check(usage['wall_seconds'] >= 0 and usage['sampled_peak_rss_bytes'] >= 0,
                  f'Invalid recorded resource use: {name}')
            rows = by_model[name]
            imported = sum(q['status'] == 'imported' for q in rows)
            check(outcome['planned_properties'] == 16 and outcome['imported_properties'] == imported,
                  f'Outcome count differs: {name}')
            successful_worker = usage['exit_code'] == 0 and progress.get('stage') == 'complete' and (job / 'records.json').exists()
            check(outcome['success'] is successful_worker, f'Worker completion differs: {name}')
            if successful_worker:
                check(read(job / 'records.json', []) == rows, f'Worker records differ: {name}')
            else:
                failure = usage.get('termination_reason') or progress.get('error') or f'Worker exit {usage["exit_code"]}'
                observed = progress.get('observed_properties', [])
                for q in rows:
                    check(q['status'] == 'unsupported' and q['error'] == failure and
                          q['observed'] is (q['property_slot'] < len(observed)) and not q.get('branches'),
                          f'Failed-worker slot differs: {q["name"]}')
                failure_evidence.append(outcome)
            if progress.get('archive'):
                expected = dict(model=name, url=models[name]['url'], **progress['archive'])
                check(archive_by_model.get(name) == expected, f'Archive progress differs: {name}')
            for key, relative in [('pnml_sha256', 'model.pnml'), ('original_xml_sha256', 'ReachabilityCardinality.xml')]:
                if key in progress:
                    identity(safe(CORPUS / 'inputs' / name / relative), progress[key], 'original input progress')
            if 'archive_expanded_bytes' in progress:
                check(0 <= progress['archive_expanded_bytes'] <= 1024**3, f'Expanded archive limit differs: {name}')
    earlier_groups, comparisons = defaultdict(list), []
    for relative, expected in sorted(prior_metadata.items()):
        with section(f'prior metadata {relative}'):
            path = safe(Path(relative))
            identity(path, expected, 'preselection corpus metadata via frozen input selection')
            if relative in {'benchmarks/harder-programs/manifest.json',
                            'benchmarks/scaling-programs/manifest.json'}:
                records = read(path, [])
                required = {'argument', 'expectation_basis', 'expected_serializable',
                            'family', 'name', 'parameters', 'sha256', 'source'}
                valid = all(isinstance(row, dict) and set(row) == required and
                            isinstance(row['name'], str) and isinstance(row['family'], str) and
                            isinstance(row['source'], str) and row['source'].endswith('.ser') and
                            isinstance(row['parameters'], dict) and
                            type(row['expected_serializable']) is bool and
                            isinstance(row['sha256'], str) and
                            re.fullmatch('[0-9a-f]{64}', row['sha256'])
                            for row in records)
                check(valid and bool(records), f'Unexpected serializability source metadata: {relative}')
                comparisons.append(dict(path=relative, expected_sha256=expected,
                                        schema='serializability-source-manifest-array',
                                        rows=len(records), included=0,
                                        excluded_reserved_or_evaluation=0,
                                        not_comparable_source_only=len(records),
                                        overlap_scope='Source hashes describe .ser programs; no canonical branch signatures exist in this metadata. Program payloads are not read.'))
                continue
            data = read(path)
            excluded = included = 0
            for q in data.get('queries', []):
                if (family_group(q.get('family', '')) in reserved_groups or
                    any('evaluation' in str(q.get(k, '')) for k in ('suite', 'split')) or
                    'evaluation' in relative):
                    excluded += 1
                    continue
                if q.get('status') != 'imported' or 'branches' not in q:
                    continue
                key = tuple(b['sha256'] for b in q['branches'])
                check(all(re.fullmatch('[0-9a-f]{64}', value) for value in key),
                      f'Invalid earlier branch identity: {relative}/{q.get("name")}')
                earlier_groups[key].append(dict(manifest=relative, name=q['name'], kind=q.get('kind')))
                included += 1
            comparisons.append(dict(path=relative, expected_sha256=expected, schema='object-manifest', included=included,
                                    excluded_reserved_or_evaluation=excluded))
    inventory = []
    with section('complete retained corpus inventory'):
        safe(CORPUS)
        for path in sorted(CORPUS.rglob('*')):
            with section(f'inventory {label(path)}'):
                safe(path)
                if path.is_file():
                    inventory.append(dict(path=label(path), bytes=path.stat().st_size, sha256=digest(path)))
        check(bool(inventory), 'Empty retained corpus inventory')
    for outcome_index, outcome in enumerate(outcomes):
        with section(f'artifact accounting {outcome_index}'):
            name = outcome['model']
            check(name in models, f'Unplanned outcome model: {name}')
            counts = dict(archive=0, extracted=0, canonical=0)
            for item in inventory:
                relative = Path(item['path']).relative_to(CORPUS.relative_to(ROOT))
                if relative in {Path('archives') / (name + suffix) for suffix in ('.tgz', '.part')}:
                    counts['archive'] += item['bytes']
                elif relative.is_relative_to(Path('inputs') / name):
                    counts['extracted'] += item['bytes']
                elif relative.parts[0] in {f'{name}__RC{i:02}' for i in range(16)}:
                    counts['canonical'] += item['bytes']
            actual = dict(limit_bytes=1024**3, used_bytes=sum(counts.values()), categories=counts)
            check(outcome['resources']['artifacts'] == actual, f'Artifact accounting differs: {name}')
            check(actual['used_bytes'] <= actual['limit_bytes'], f'Artifact budget exceeded: {name}')
    summary.update(status='failed' if issues else 'passed', issues=issues,
                   selection_sha256=EXPECTED_SELECTION, identities=identities,
                   manifest_sha256=cache.get(CORPUS / 'manifest.json'),
                   audit_script_sha256=digest(Path(__file__)),
                   input_files=len(inputs), corpus_file_inventory=inventory,
                   all_corpus_files=len(inventory), all_corpus_bytes=sum(r['bytes'] for r in inventory),
                   archive_files=len(archive_rows), failure_evidence=failure_evidence,
                   model_outcomes=outcomes, comparison_manifests=comparisons,
                   exact_ordered_branch_representatives=len(groups),
                   exact_ordered_branch_and_kind_representatives=len({(key, q['kind']) for key, rows in groups.items() for q in rows}),
                   exact_ordered_branch_duplicate_groups=[dict(ordered_branch_sha256=list(key), queries=rows)
                                                         for key, rows in groups.items() if len(rows) > 1],
                   exact_ordered_branch_cross_corpus_matches=[dict(ordered_branch_sha256=list(key), current=rows, earlier=earlier_groups[key])
                                                            for key, rows in groups.items() if key in earlier_groups])
    REPORT.write_text(json.dumps(summary, indent=2) + '\n')
    REPORT.with_suffix('.md').write_text(
        '# General development v3: collection audit\n\n'
        f'**{summary["status"].upper()}**. Planned denominator: 11 models / 176 slots. '
        f'Recorded slot outcomes: `{json.dumps(summary.get("collection_status", {}))}`. '
        f'Issues: {len(issues)}.\n\n{SCOPE}\n\n'
        f'Exact ordered-branch representatives: {len(groups)}; EF/AG polarity remains separate. '
        'Retain every planned slot and acquisition failure in reporting. See the JSON report for '
        'identities, partial-failure evidence, duplicate membership and metadata-only earlier matches.\n')
    print(json.dumps({k: summary[k] for k in ('status', 'issues', 'planned_slots', 'all_corpus_files', 'exact_ordered_branch_representatives')}))
    return not issues


if __name__ == '__main__':
    raise SystemExit(0 if audit() else 1)
