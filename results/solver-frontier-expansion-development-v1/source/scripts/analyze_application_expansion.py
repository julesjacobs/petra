#!/usr/bin/env python3
"""Validate and classify a complete registered application difficulty screen."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath

DEFINITIVE = {'reachable', 'unreachable'}
CLASSES = ('all_methods_definitive', 'mixed_solved_unresolved', 'no_method_definitive')
NATIVE_FLAGS = (
    ('target_zero_trap_methods', '--target-zero-trap'),
    ('target_path_potential_methods', '--target-path-potential'),
    ('buffer_agglomeration_methods', '--buffer-agglomeration'),
    ('geometric_branches_methods', '--geometric-branches'),
)


def registered_native_tools(plan, environment):
    """Resolve legacy or per-method registrations and their common input workspace."""
    native = {m for m in plan['methods'] if m.startswith('native-')}
    observed = environment.get('native_tools')
    if not isinstance(observed, dict) or set(observed) != native:
        raise ValueError('Environment native method mismatch')
    for key, _ in NATIVE_FLAGS:
        selected = plan.get(key, [])
        if (not isinstance(selected, list) or any(not isinstance(m, str) for m in selected)
                or len(set(selected)) != len(selected) or not set(selected) <= native):
            raise ValueError(f'Invalid registered native flag methods: {key}')
        if environment.get(key, []) != selected:
            raise ValueError(f'Environment native flag methods differ: {key}')
    explicit = plan.get('native_tools')
    if 'native_tools' in plan and (not isinstance(explicit, dict) or set(explicit) != native):
        raise ValueError('Registered native method mismatch')
    tools = {}
    for method in sorted(native):
        if not isinstance(observed[method], dict):
            raise ValueError(f'Invalid observed native tool: {method}')
        spec = explicit[method] if explicit is not None else dict(
            engine=plan['methods'][method], binary=observed[method].get('binary'),
            binary_sha256=plan['native_binary_sha256'])
        if not isinstance(spec, dict) or set(spec) != {'engine', 'binary', 'binary_sha256'}:
            raise ValueError(f'Invalid native tool registration: {method}')
        binary = spec['binary']
        if (not isinstance(binary, str) or not PurePosixPath(binary).is_absolute()
                or str(PurePosixPath(binary)) != binary or '..' in PurePosixPath(binary).parts):
            raise ValueError(f'Native binary must be an absolute normalized path: {method}')
        if (not isinstance(spec['engine'], str) or not spec['engine']
                or spec['engine'] != plan['methods'][method]
                or not isinstance(spec['binary_sha256'], str) or not spec['binary_sha256']):
            raise ValueError(f'Invalid native engine or identity: {method}')
        if observed[method] != spec:
            raise ValueError(f'Environment native binary or engine mismatch: {method}')
        tools[method] = spec
    by_path = {}
    for spec in tools.values():
        if spec['binary'] in by_path and by_path[spec['binary']] != spec['binary_sha256']:
            raise ValueError('Conflicting registered identities for one native binary')
        by_path[spec['binary']] = spec['binary_sha256']
    if not tools:
        return tools, None
    primary = plan.get('native_binary')
    if (not isinstance(primary, str) or not primary or PurePosixPath(primary).is_absolute()
            or str(PurePosixPath(primary)) != primary or '..' in PurePosixPath(primary).parts):
        raise ValueError('Primary native binary must be a normalized workspace-relative path')
    primary_hash = plan['native_binary_sha256']
    if environment.get('binary_sha256') != primary_hash:
        raise ValueError('Environment primary native binary identity differs')
    suffix = '/' + primary
    workspaces = {spec['binary'][:-len(suffix)] for spec in tools.values()
                  if spec['binary'].endswith(suffix) and spec['binary_sha256'] == primary_hash}
    if len(workspaces) != 1:
        raise ValueError('Primary native binary is missing or ambiguous in native registrations')
    workspace = workspaces.pop() or '/'
    if explicit is None and any(spec['binary'] != str(PurePosixPath(workspace) / primary) for spec in tools.values()):
        raise ValueError('Legacy native binary path differs')
    return tools, workspace


def native_command(plan, query, method, tools, workspace):
    tool = tools[method]
    corpus = PurePosixPath(workspace) / plan['corpus']
    command = [tool['binary'], '--pnml', str(corpus / query['pnml']),
               '--xml', str(corpus / query['xml']), '--property-id', query['property_id'],
               '--method', tool['engine'], '--seconds', str(float(plan['seconds'])),
               '--max-states', str(plan['max_states'])]
    command.extend(flag for key, flag in NATIVE_FLAGS if method in plan.get(key, []))
    return command


def corpus_groups(manifest):
    queries = manifest['queries']
    if len({q['name'] for q in queries}) != len(queries):
        raise ValueError('Duplicate manifest query')
    groups = defaultdict(list)
    for query in queries:
        if query.get('status') != 'imported':
            continue
        groups[tuple(b['sha256'] for b in query['branches'])].append(query['name'])
    return sorted(sorted(names) for names in groups.values())


def failure_flags(row):
    flags = set()
    for part in (row, *row.get('branches', [])):
        resource = part.get('resources') or {}
        if part.get('verdict') == 'error' or part.get('error') or part.get('subprocess_error'):
            flags.add('error')
        if part.get('failure_stage') == 'collection':
            flags.add('collection_failure')
        elif part.get('capability_failures') or part.get('verdict') == 'unsupported':
            flags.add('capability_failure')
        if resource.get('memory_limit_exceeded') or resource.get('systemd_result') == 'oom-kill':
            flags.add('memory_limit')
        if part.get('outer_timeout') or part.get('deadline_exceeded') or resource.get('systemd_result') == 'timeout':
            flags.add('timeout')
    if row.get('execution_attempted') is False:
        flags.add('not_executed')
    if row.get('failure_stage'):
        flags.add('failure_stage:' + row['failure_stage'])
    validation = row.get('validation') or {}
    if validation.get('outer_timeout'):
        flags.add('validation_timeout')
    if (validation.get('resources') or {}).get('memory_limit_exceeded'):
        flags.add('validation_memory_limit')
    if validation.get('exit_code') not in (None, 0) or validation.get('error') or validation.get('subprocess_error'):
        flags.add('validation_error')
    if row.get('exit_code') not in (None, 0):
        flags.add('nonzero_exit')
    return flags


def native_checked(row, query):
    branches = row.get('branches', [])
    indices = [b.get('branch') for b in branches]
    expected = set(range(len(query['branches'])))
    if len(set(indices)) != len(indices) or not set(indices) <= expected:
        return False
    if row.get('translation_check') != 'independent-original-input-equals-all-canonical-branches':
        return False
    validation = row.get('validation') or {}
    if validation.get('exit_code') != 0 or validation.get('outer_timeout') or (validation.get('resources') or {}).get('memory_limit_exceeded'):
        return False
    def checked(branch, verdict):
        return branch.get('verdict') == verdict and branch.get('independent_check', '').startswith('python-')
    if row['verdict'] == 'reachable':
        return any(checked(b, 'reachable') for b in branches)
    return set(indices) == expected and all(checked(b, 'unreachable') for b in branches)


def analyze(manifest, plan, environment, rows):
    groups = corpus_groups(manifest)
    queries = {q['name']: q for q in manifest['queries']}
    methods = list(plan['methods'])
    repeats = plan['repeat']
    if not methods or type(repeats) is not int or repeats < 1:
        raise ValueError('Invalid registered methods or repeat count')
    if len(queries) != plan['properties'] or plan['expected_rows'] != len(queries)*len(methods)*repeats:
        raise ValueError('Registered denominator mismatch')
    for key in ('repeat', 'seconds', 'max_states', 'memory_mib', 'linux_cpus', 'perf', 'outer_grace', 'order_seed', 'manifest_sha256'):
        if environment.get(key) != plan.get(key):
            raise ValueError(f'Environment differs from plan: {key}')
    if len(environment['methods']) != len(methods) or set(environment['methods']) != set(methods):
        raise ValueError('Environment method mismatch')
    order = environment['property_order']
    if len(order) != len(queries) or set(order) != set(queries):
        raise ValueError('Environment property mismatch')
    tools, workspace = registered_native_tools(plan, environment)
    native = set(tools)
    if environment.get('smpt_configurations') != plan['smpt_configurations']:
        raise ValueError('Environment SMPT configuration mismatch')
    for key in ('binary_sha256', 'source_commit', 'configurations'):
        if environment.get('verifypn', {}).get(key) != plan['verifypn'][key]:
            raise ValueError(f'Environment VerifyPN differs from plan: {key}')
    if environment['bounded_validation'].get('enabled') is not True:
        raise ValueError('Independent bounded validation must be enabled')
    for key in ('seconds', 'memory_mib', 'response_mib', 'dag_check_max_work', 'included_in_solver_timing'):
        if environment['bounded_validation'].get(key) != plan['validation'].get(key):
            raise ValueError(f'Environment validation differs from plan: {key}')
    matrix = {}
    for index, row in enumerate(rows):
        if type(row['repeat']) is not int:
            raise ValueError('Invalid repeat index')
        key = row['query'], row['method'], row['repeat']
        if key in matrix:
            raise ValueError(f'Duplicate result row: {key}')
        matrix[key] = index
    expected = {(n, m, i) for n in queries for m in methods for i in range(repeats)}
    if set(matrix) != expected:
        raise ValueError(f'Incomplete or unexpected matrix: {len(expected-set(matrix))} missing, {len(set(matrix)-expected)} extra')
    for row in rows:
        query = queries[row['query']]
        if row['method'] in native and query.get('status') == 'imported':
            if row.get('command') != native_command(plan, query, row['method'], tools, workspace):
                raise ValueError(f'Exact native command differs: {row["query"]}/{row["method"]}/{row["repeat"]}')
    row_flags, effective = [], []
    for row in rows:
        flags = failure_flags(row)
        verdict = row['verdict']
        imported = queries[row['query']].get('status') == 'imported'
        if not imported:
            flags.add('collection_failure')
            verdict = 'unsupported'
        if imported and row['method'] in native and verdict in DEFINITIVE and not native_checked(row, queries[row['query']]):
            flags.add('unchecked_native_answer')
            verdict = 'unknown'
        if row['verdict'] in DEFINITIVE and flags:
            flags.add('inconsistent_definitive_answer')
            verdict = 'unknown'
        row_flags.append(sorted(flags))
        effective.append(verdict)
    representative = {n: group[0] for group in groups for n in group}
    cases = []
    for name, query in sorted(queries.items()):
        indices = [matrix[name, m, i] for m in methods for i in range(repeats)]
        answers = {rows[i]['verdict'] for i in indices} & DEFINITIVE
        solved = [m for m in methods if all(effective[matrix[name, m, i]] in DEFINITIVE for i in range(repeats))]
        classification = CLASSES[0] if len(solved) == len(methods) else CLASSES[1] if solved else CLASSES[2]
        imported = query.get('status') == 'imported'
        if not imported:
            classification = 'collection_unavailable'
        flags = sorted({flag for i in indices for flag in row_flags[i]})
        native_solved, competitor_solved = bool(set(solved) & native), bool(set(solved) - native)
        cases.append(dict(query=name, family=query['family'], kind=query.get('kind'), representative=representative.get(name),
                          imported=imported, collection_status=query.get('status'),
                          classification=classification, definitive_methods=solved, disagreement=len(answers)>1,
                          native_only=native_solved and not competitor_solved,
                          competitor_only=competitor_solved and not native_solved,
                          flags=flags, row_indices=indices))
    duplicate_groups = []
    for group in groups:
        if len(group) < 2:
            continue
        answers = {rows[matrix[n,m,i]]['verdict'] for n in group for m in methods for i in range(repeats)} & DEFINITIVE
        duplicate_groups.append(dict(representative=group[0], queries=group,
                                     kinds=sorted({queries[n]['kind'] for n in group}),
                                     mixed_property_kinds=len({queries[n]['kind'] for n in group})>1,
                                     disagreement=len(answers)>1))
    conflicts = {n for group in duplicate_groups if group['disagreement'] for n in group['queries']}
    for case in cases:
        case['duplicate_disagreement'] = case['query'] in conflicts
    def summarize(selected):
        classes = CLASSES + (('collection_unavailable',) if any(not x['imported'] for x in selected) else ())
        return dict(properties=len(selected), imported_properties=sum(x['imported'] for x in selected),
                    collection_unavailable=sum(not x['imported'] for x in selected),
                    classifications={c:sum(x['classification']==c for x in selected) for c in classes},
                    definitive_by_method={m:sum(m in x['definitive_methods'] for x in selected) for m in methods},
                    disagreements=sum(x['disagreement'] for x in selected),
                    duplicate_disagreements=sum(x['duplicate_disagreement'] for x in selected),
                    native_only=sum(x['native_only'] for x in selected), competitor_only=sum(x['competitor_only'] for x in selected),
                    flagged_queries=dict(Counter(f for x in selected for f in x['flags'])))
    representatives = [c for c in cases if c['query'] == c['representative']]
    candidates = [c for c in cases if c['imported'] and c['classification'] == 'no_method_definitive']
    has_conflicts = any(c['disagreement'] or c['duplicate_disagreement'] for c in cases)
    has_invalid_answers = any('inconsistent_definitive_answer' in flags for flags in row_flags)
    return dict(format='application-difficulty-screen-v1', properties=len(queries), exact_ordered_branch_representatives=len(groups),
                has_conflicts=has_conflicts, has_invalid_answers=has_invalid_answers,
                validity='requires_investigation' if has_conflicts or has_invalid_answers else 'complete_consistent_screen',
                rows=len(rows), repeats=repeats, full=summarize(cases),
                imported=summarize([c for c in cases if c['imported']]), representatives=summarize(representatives),
                families={f:dict(full=summarize([c for c in cases if c['family']==f]),
                                 representatives=summarize([c for c in representatives if c['family']==f]))
                          for f in sorted({q['family'] for q in queries.values()})},
                duplicate_groups=duplicate_groups, cases=cases, row_flags=row_flags, runs=rows,
                selections=dict(collection_unavailable=[c['query'] for c in cases if not c['imported']],
                                all_unresolved=[c['query'] for c in candidates],
                                all_unresolved_without_observed_failures=[c['query'] for c in candidates
                                   if not (set(c['flags'])-{'timeout'}) and not c['disagreement'] and not c['duplicate_disagreement']]),
                scope='Outcome-selected development screen, not held-out evaluation or stable timing evidence. Native definitive answers require independent Python checking metadata; competitor answers are tool-reported. Unknown does not imply mathematical difficulty. All rows and failures retained.',
                duplicate_scope='Exact ordered branch SHA256 tuples only; lexicographically first query is representative. Not semantic equivalence or isomorphism detection. Mixed property kinds and conflicting canonical reachability verdicts are flagged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=Path('research/application-expansion-v1-screen-plan.json'))
    parser.add_argument('--corpus', type=Path)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    corpus = args.corpus or Path(plan['corpus'])
    results = args.results or Path(plan['output'])
    paths = [args.plan, corpus/'manifest.json', results/'environment.json', results/'runs.jsonl']
    hashes = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if hashes[str(paths[1])] != plan['manifest_sha256']:
        raise ValueError('Manifest does not match registered plan')
    manifest, environment = [json.loads(p.read_text()) for p in paths[1:3]]
    rows = [json.loads(line) for line in paths[3].read_text().splitlines() if line.strip()]
    report = analyze(manifest, plan, environment, rows)
    report['sources'] = hashes
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:report[k] for k in ('properties','exact_ordered_branch_representatives','rows','full','families')}, indent=2))


if __name__ == '__main__':
    main()
