#!/usr/bin/env python3
"""Offline instruction comparison of a complete Linux benchmark matrix.

Only stable, matching definitive answers with uncensored, positive, fully
scheduled counters enter ratios. Deadline-censored counts remain failures;
retired user-space instructions do not make wall-time budgets independent of load.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics

DEFINITIVE = {'reachable', 'unreachable'}
VERDICTS = DEFINITIVE | {'unknown', 'error', 'unsupported'}


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def records_in(row):
    yield row
    branches = row.get('branches', [])
    if not isinstance(branches, list):
        raise ValueError('branches must be a list')
    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError('Branch record must be an object')
        yield from records_in(branch)


def observations(row):
    """Do not double-count frontend process trees and their branch subprocesses."""
    records = list(records_in(row))
    if any(item.get('resources') is not None and not isinstance(item['resources'], dict) for item in records):
        raise ValueError('resources must be an object or null')
    timeout = oom = failed_exit = False
    for item in records:
        usage = item.get('resources') or {}
        memory = bool(usage.get('memory_limit_exceeded')) or usage.get('systemd_result') == 'oom-kill'
        oom |= memory
        timeout |= (usage.get('systemd_result') == 'timeout'
                    or bool(item.get('outer_timeout')) and not memory)
        failed_exit |= item.get('exit_code', 0) not in (0, None)
    if 'resources' in row:
        sources = [row['resources']]
    else:
        sources = [item.get('resources') for item in records[1:]]
    statuses = set()
    values = []
    if not sources:
        statuses.add('missing_counter')
    for usage in sources:
        if not isinstance(usage, dict):
            statuses.add('missing_counter')
            continue
        counters = usage.get('perf_counters')
        counter = counters.get('instructions:u') if isinstance(counters, dict) else None
        if not isinstance(counter, dict):
            statuses.add('missing_counter')
            continue
        value = counter.get('value')
        percent = counter.get('time_running_percent')
        if (not finite_number(value) or value <= 0 or not finite_number(percent)
                or percent <= 0 or percent > 100
                or usage.get('runner') != 'linux-systemd-user'
                or usage.get('perf_enabled') is not True):
            statuses.add('invalid_counter')
            continue
        values.append(value)
        if percent != 100:
            statuses.add('multiplexed_counter')
    instructions = sum(values) if len(values) == len(sources) and sources else None
    reasons = set(statuses)
    if timeout:
        reasons.add('timeout')
    if oom:
        reasons.add('oom')
    if failed_exit:
        reasons.add('failed_exit')
    if row.get('capability_failures'):
        reasons.add('capability_failure')
    return dict(instructions=instructions, timeout=timeout, oom=oom,
                failed_exit=failed_exit, counter_status=sorted(statuses),
                exclusion_reasons=sorted(reasons))


def validate_matrix(environment, rows):
    if not isinstance(environment, dict):
        raise ValueError('environment.json must contain an object')
    properties = environment.get('property_order')
    methods = environment.get('methods')
    repeat = environment.get('repeat')
    for name, axis in [('property_order', properties), ('methods', methods)]:
        if (not isinstance(axis, list) or not axis
                or any(not isinstance(v, str) or not v for v in axis)
                or len(set(axis)) != len(axis)):
            raise ValueError(f'{name} must be a nonempty list of unique nonempty strings')
    if type(repeat) is not int or repeat < 1:
        raise ValueError('repeat must be a positive integer')
    if type(environment.get('queries')) is not int or environment['queries'] != len(properties):
        raise ValueError('queries does not match property_order')
    expected = set(itertools.product(properties, methods, range(repeat)))
    indexed = {}
    polarities = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Run must be an object')
        if (not isinstance(row.get('query'), str) or not isinstance(row.get('method'), str)
                or type(row.get('repeat')) is not int):
            raise ValueError('Run identity requires query, method and integer repeat')
        key = row['query'], row['method'], row['repeat']
        if key not in expected:
            raise ValueError(f'Unexpected run identity: {key}')
        if key in indexed:
            raise ValueError(f'Duplicate run identity: {key}')
        if not isinstance(row.get('verdict'), str) or row['verdict'] not in VERDICTS:
            raise ValueError(f'Unknown verdict for {key}: {row.get("verdict")!r}')
        kind = row.get('property_kind')
        if kind is not None:
            if kind not in ('EF', 'AG') or polarities.setdefault(row['query'], kind) != kind:
                raise ValueError(f'Inconsistent property polarity for {row["query"]}')
            if 'property_truth' in row:
                truth = ((row['verdict'] == 'reachable') == (kind == 'EF')
                         if row['verdict'] in DEFINITIVE else None)
                if row['property_truth'] is not truth:
                    raise ValueError(f'Property truth disagrees with verdict for {key}')
        indexed[key] = row
    missing = expected - indexed.keys()
    if missing:
        raise ValueError(f'Incomplete matrix: {len(missing)} missing runs; first: {sorted(missing)[:5]}')
    return properties, methods, repeat, indexed


def variability(values):
    median = statistics.median(values)
    return dict(repeats=len(values), instructions=values, median_instructions=median,
                minimum_instructions=min(values), maximum_instructions=max(values),
                max_over_min=max(values) / min(values) if len(values) > 1 else None,
                coefficient_of_variation=(statistics.pstdev(values) / statistics.mean(values)
                                          if len(values) > 1 else None))


def analyze(environment, rows):
    properties, methods, repeats, indexed = validate_matrix(environment, rows)
    observed = {key: observations(row) for key, row in indexed.items()}
    summaries = {}
    stable = {}
    valid = {}
    for method in methods:
        cases = []
        verdict_counts = Counter()
        failures = Counter()
        property_counts = Counter()
        for query in properties:
            keys = [(query, method, r) for r in range(repeats)]
            verdicts = [indexed[k]['verdict'] for k in keys]
            verdict_counts.update(verdicts)
            answers = set(verdicts)
            stable[query, method] = next(iter(answers)) if len(answers) == 1 else None
            property_counts['solved_in_any_repeat'] += bool(answers & DEFINITIVE)
            property_counts['solved_in_every_repeat'] += all(v in DEFINITIVE for v in verdicts)
            property_counts['stable_solved'] += stable[query, method] in DEFINITIVE
            property_counts['unstable_repeat_outcomes'] += len(answers) != 1
            property_counts['conflicting_definitive_repeats'] += len(answers & DEFINITIVE) > 1
            reasons = set()
            for key in keys:
                failures.update(observed[key]['exclusion_reasons'])
                reasons.update(observed[key]['exclusion_reasons'])
            if stable[query, method] not in DEFINITIVE:
                reasons.add('not_stably_solved')
            valid[query, method] = sorted(reasons)
            if not reasons:
                values = [observed[k]['instructions'] for k in keys]
                cases.append(dict(query=query, verdict=stable[query, method], **variability(values)))
        ratios = [c['max_over_min'] for c in cases if c['max_over_min'] is not None]
        summaries[method] = dict(
            total_properties=len(properties), total_runs=len(properties) * repeats,
            solved_runs=sum(verdict_counts[v] for v in DEFINITIVE),
            verdict_counts={v: verdict_counts[v] for v in sorted(VERDICTS)},
            property_counts=dict(property_counts),
            failures={k: failures[k] for k in ('timeout', 'oom', 'failed_exit', 'capability_failure',
                                              'missing_counter', 'invalid_counter', 'multiplexed_counter')},
            instruction_repeat_variability=dict(
                eligible_properties=len(cases), cases=cases,
                median_max_over_min=statistics.median(ratios) if ratios else None,
                maximum_max_over_min=max(ratios) if ratios else None))
    comparisons = []
    for numerator, denominator in itertools.combinations(methods, 2):
        cases, excluded = [], []
        for query in properties:
            reasons = [f'{method}:{reason}' for method in (numerator, denominator)
                       for reason in valid[query, method]]
            if (stable[query, numerator] in DEFINITIVE and stable[query, denominator] in DEFINITIVE
                    and stable[query, numerator] != stable[query, denominator]):
                reasons.append('definitive_verdict_disagreement')
            if reasons:
                excluded.append(dict(query=query, reasons=reasons))
                continue
            a = statistics.median(observed[query, numerator, r]['instructions'] for r in range(repeats))
            b = statistics.median(observed[query, denominator, r]['instructions'] for r in range(repeats))
            cases.append(dict(query=query, verdict=stable[query, numerator],
                              numerator_median_instructions=a, denominator_median_instructions=b,
                              ratio=a / b))
        geometric_mean = (math.exp(statistics.mean(math.log(c['numerator_median_instructions'])
                                                   - math.log(c['denominator_median_instructions'])
                                                   for c in cases)) if cases else None)
        comparisons.append(dict(numerator=numerator, denominator=denominator,
                                ratio_definition=f'median instructions({numerator}) / median instructions({denominator})',
                                eligible_properties=len(cases), geometric_mean_ratio=geometric_mean,
                                cases=cases, excluded_properties=len(excluded), exclusions=excluded))
    disagreements = []
    for query in properties:
        answers = {indexed[query, method, r]['verdict'] for method in methods for r in range(repeats)}
        if len(answers & DEFINITIVE) > 1:
            disagreements.append(query)
    return dict(format='pvass-instruction-analysis-v1', coverage=dict(
        properties=len(properties), methods=methods, repeats=repeats, expected_runs=len(indexed),
        observed_runs=len(rows), complete=True), methods=summaries, comparisons=comparisons,
        definitive_disagreements=disagreements,
        caveats=[
            'Instructions count user-space work in the measured process tree; they are not wall-time speedups.',
            'Timeout and OOM runs remain in failure counts. Their counters never enter ratios; elapsed-time censoring still depends on machine load.',
            'Each pair uses its own stable, matching, fully scheduled common-solved subset; inspect the case list and denominator.',
            'Instruction variability uses stable solved properties with positive counters at 100% time_running_percent in every repeat; it is unavailable with one repetition.',
            'Definitive verdict agreement does not independently validate external solver answers.',
            'Frontend and preprocessing scope remain those recorded in environment.json; this analysis does not establish matched input scopes.'])


def markdown(report):
    coverage = report['coverage']
    lines = ['# Instruction-count comparison', '',
             f"Complete matrix: {coverage['properties']} properties × {len(coverage['methods'])} methods × {coverage['repeats']} repetitions.", '',
             '| Method | Solved runs / total | Stable solved properties / total | Unstable outcomes | Timeout runs | OOM runs | Missing / invalid / multiplexed counters |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for method, s in report['methods'].items():
        p, f = s['property_counts'], s['failures']
        lines.append(f"| {method} | {s['solved_runs']} / {s['total_runs']} | {p['stable_solved']} / {s['total_properties']} | {p['unstable_repeat_outcomes']} | {f['timeout']} | {f['oom']} | {f['missing_counter']} / {f['invalid_counter']} / {f['multiplexed_counter']} |")
    for pair in report['comparisons']:
        ratio = pair['geometric_mean_ratio']
        value = 'unavailable' if ratio is None else f'{ratio:.6g}'
        lines += ['', f"## {pair['numerator']} / {pair['denominator']}", '',
                  f"Geometric mean of per-property median instruction ratios: **{value}** across **{pair['eligible_properties']}** eligible properties.",
                  '', 'A ratio below 1 means fewer instructions for the numerator.', '',
                  '| Property | Verdict | Numerator median | Denominator median | Ratio |',
                  '|---|---|---:|---:|---:|']
        for c in pair['cases']:
            lines.append(f"| {c['query']} | {c['verdict']} | {c['numerator_median_instructions']} | {c['denominator_median_instructions']} | {c['ratio']:.6g} |")
        lines += ['', f"Excluded properties: {pair['excluded_properties']}."]
    lines += ['', '## Repeat variability', '',
              '| Method | Eligible properties | Median max/min | Largest max/min |', '|---|---:|---:|---:|']
    for method, s in report['methods'].items():
        v = s['instruction_repeat_variability']
        show = lambda x: 'unavailable' if x is None else f'{x:.6g}'
        lines.append(f"| {method} | {v['eligible_properties']} | {show(v['median_max_over_min'])} | {show(v['maximum_max_over_min'])} |")
    lines += ['', f"Definitive disagreements: {report['definitive_disagreements']}.", '']
    lines.extend('- ' + caveat for caveat in report['caveats'])
    return '\n'.join(lines) + '\n'


def load(directory):
    directory = Path(directory)
    environment_bytes = (directory / 'environment.json').read_bytes()
    run_bytes = (directory / 'runs.jsonl').read_bytes()
    environment = json.loads(environment_bytes)
    rows = [json.loads(line) for line in run_bytes.splitlines() if line.strip()]
    result = analyze(environment, rows)
    result['source'] = dict(directory=str(directory.resolve()),
                           environment_sha256=hashlib.sha256(environment_bytes).hexdigest(),
                           runs_sha256=hashlib.sha256(run_bytes).hexdigest(),
                           environment=environment)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('--output', type=Path, help='Create this new directory with analysis.json and analysis.md')
    parser.add_argument('--format', choices=('json', 'markdown'), default='json', help='Stdout format without --output')
    args = parser.parse_args(argv)
    try:
        report = load(args.results)
        serialized = json.dumps(report, indent=2, allow_nan=False) + '\n'
        rendered = markdown(report)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=False)
            (args.output / 'analysis.json').write_text(serialized)
            (args.output / 'analysis.md').write_text(rendered)
        else:
            print(serialized if args.format == 'json' else rendered, end='')
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
