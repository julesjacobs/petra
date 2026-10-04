#!/usr/bin/env python3
"""Audit saved paired evidence and summarize repetitions; never run a solver or checker."""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('measurement_harness', HERE / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)
DEFINITIVE = run.DEFINITIVE


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected):
    return type(actual) is type(expected) and actual == expected


def close(actual, expected):
    return run.finite(actual) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-10)


def index_queries(plan):
    return {(name, q['name']): q for name, corpus in plan['corpora'].items()
            for q in json.loads((ROOT / corpus['path'] / 'manifest.json').read_text())['queries']}


def verify_plan(folder, plan):
    run.load_runner(folder / 'snapshot')
    run.pin_checks(folder, plan)
    for field, expected in dict(format='verifypn-learning-native-paired-v1', methods=run.METHODS,
                                seconds=5.0, outer_grace=0.0, max_states=2000000, memory_mib=2048,
                                validation_seconds=60.0, validation_memory_mib=2048,
                                validation_response_mib=64, validation_dag_work=200000000,
                                repeat=2, order_seed=run.SEED, perf=False).items():
        require(same(plan.get(field), expected), 'Plan differs: ' + field)
    require(plan['campaign'] == folder.name, 'Campaign differs from folder')
    require(plan['binaries']['baseline']['binary_sha256'] == run.BASELINE_SHA, 'Baseline changed')
    queries = index_queries(plan)
    require(len(queries) == 368, 'Available corpus denominator differs')
    selected = {(q['corpus'], q['query']) for q in plan['selected_queries']}
    require(len(selected) == len(plan['selected_queries']) == plan['properties'] and selected <= set(queries), 'Selected denominator differs')
    if plan['campaign'] == 'full':
        require(selected == set(queries), 'Full campaign omitted properties')
        require(len({tuple(b['sha256'] for b in q['branches']) for q in queries.values()}) == 366, 'Full representative denominator differs')
    policy = plan['host_policy']
    require(policy == dict(strict=plan['campaign'] == 'full' and not policy['allow_contention'],
                           allow_contention=policy['allow_contention'], idle_samples=5, sample_seconds=1.0,
                           max_normalized_load1=0.25, max_cpu_percent=10.0)
            and type(policy['allow_contention']) is bool, 'Host policy differs')
    for index in range(2):
        stage = plan['stages'][f'repeat{index + 1}']
        require(stage == dict(schedule=run.schedule(plan['corpora'], selected, index), expected_rows=2 * len(selected)), 'Schedule differs')
    return queries


def host_evidence(path, policy):
    samples = [json.loads(line) for line in path.read_text().splitlines()]
    require(len(samples) >= policy['idle_samples'] + 1, 'Insufficient host samples')
    require([s['phase'] for s in samples[:5]] == ['preflight'] * 5 and samples[-1]['phase'] == 'terminal'
            and all(s['phase'] == 'measurement' for s in samples[5:-1]), 'Host sample phases differ')
    previous = None
    for sample in samples:
        n = sample['logical_cpus']
        require(type(n) is int and n > 0, 'Invalid logical CPU count')
        before, after = sample['cpu_times_before'], sample['cpu_times_after']
        require(len(before) == len(after) == len(sample['per_cpu_percent']) == n, 'Host CPU sample width differs')
        calculated = []
        for a, b in zip(before, after):
            require(a.keys() == b.keys() and all(run.finite(v) for v in [*a.values(), *b.values()]), 'Invalid CPU times')
            differences = {k: max(0, b[k] - a[k]) for k in b}
            total = sum(v for k, v in differences.items() if k not in ('guest', 'guest_nice'))
            busy = total - differences.get('idle', 0) - differences.get('iowait', 0)
            calculated.append(100 * busy / total if total else 0)
        require(all(close(a, b) for a, b in zip(sample['per_cpu_percent'], calculated)), 'Per-CPU utilization differs')
        require(close(sample['cpu_percent'], sum(calculated) / n), 'Host utilization differs')
        require(len(sample['load_average']) == 3 and all(run.finite(v) for v in sample['load_average']), 'Invalid host load')
        require(close(sample['normalized_load1'], sample['load_average'][0] / n), 'Normalized load differs')
        idle = sample['normalized_load1'] <= policy['max_normalized_load1'] and sample['cpu_percent'] <= policy['max_cpu_percent']
        require(sample['within_idle_thresholds'] is idle, 'Host idle flag differs')
        require(run.finite(sample['monotonic_seconds']), 'Invalid host timestamp')
        if previous:
            require(sample['monotonic_seconds'] > previous['monotonic_seconds'] and before == previous['cpu_times_after'], 'Host samples not contiguous')
        previous = sample
    preflight_ok = all(s['within_idle_thresholds'] for s in samples[:5])
    measurement = samples[5:]
    active_ok = all(s['normalized_load1'] <= policy['max_normalized_load1']
                    and s['cpu_percent'] <= policy['max_cpu_percent'] + 100 / s['logical_cpus'] for s in measurement)
    if policy['strict']:
        require(preflight_ok and active_ok, 'Strict host idle policy failed')
    return dict(samples=len(samples), preflight_within_thresholds=preflight_ok,
                measurement_within_thresholds=active_ok, idle_host_objective_met=policy['strict'] and preflight_ok and active_ok,
                contention_observed=not (preflight_ok and active_ok), explicit_contention_permission=policy['allow_contention'],
                load1_range=[min(s['load_average'][0] for s in samples), max(s['load_average'][0] for s in samples)],
                cpu_percent_range=[min(s['cpu_percent'] for s in samples), max(s['cpu_percent'] for s in samples)],
                note='Host-wide observations; no exclusive-CPU guarantee. Active limit allows one CPU for this campaign.')


def resources(row, plan, log):
    usage = row.get('resources')
    require(type(usage) is dict and usage.get('memory_limit_bytes') == 2**31
            and type(usage.get('memory_limit_exceeded')) is bool, 'Missing solver memory evidence')
    if plan['linux_cpus']:
        for field, expected in dict(runner='linux-systemd-user', cpus=plan['linux_cpus'], perf_enabled=False, perf_counters=None).items():
            require(same(usage.get(field), expected), 'Linux resource setting differs: ' + field)
        state = json.loads(Path(str(log) + '.systemd.json').read_text())
        require(state == usage['systemd_properties'] and state.get('Result') == usage['systemd_result'], 'Cgroup sidecar differs')
        require(usage['memory_limit_exceeded'] is (state.get('Result') == 'oom-kill'), 'Cgroup OOM flag differs')
        for key, field, scale in [('CPUUsageNSec', 'cpu_seconds', 1e9), ('MemoryPeak', 'peak_memory_bytes', 1)]:
            value = state.get(key)
            expected = None if value in (None, '', '[not set]', 'infinity', '18446744073709551615') else int(value) / scale
            require(usage.get(field) == expected, 'Cgroup metric differs: ' + field)
        if state.get('Result') in ('timeout', 'oom-kill'):
            require(row['outer_timeout'] is True, 'Cgroup timeout flag omitted')
    else:
        require(usage.get('sampling_interval_seconds') == 0.01, 'Portable sampling interval differs')
        require(all(run.finite(usage.get(k)) for k in ('sampled_cpu_seconds', 'sampled_peak_rss_bytes')),
                'Invalid sampled resources')
        require(type(usage.get('observed_processes')) is int and usage['observed_processes'] >= 1, 'No sampled solver process')


def validator(row, query, plan, corpus, output, log):
    from analyze_application_expansion import native_checked
    details = row.get('validation')
    solved = row['verdict'] in DEFINITIVE
    if details is None:
        require(not solved and row['outer_timeout'] is True, 'Missing validation without solver timeout')
        return
    require(Path(str(log) + '.validation.log').is_file(), 'Missing validator log')
    request = json.loads(Path(str(log) + '.validation-request.json').read_text())
    expected = dict(query=query, corpus=str(corpus), artifacts=str(output), log=str(log), mode='rust-original-v1',
                    outer_timeout=row['outer_timeout'], exit_code=row['exit_code'], memory_bytes=2**31,
                    response_bytes=64 * 2**20, dag_check_max_work=200000000)
    require(request == expected, 'Validator request differs')
    for field, value in dict(seconds_limit=60.0, memory_limit_bytes=2**31, response_limit_bytes=64 * 2**20,
                             dag_check_max_work=200000000, included_in_solver_timing=False).items():
        require(same(details.get(field), value), 'Validator limit differs: ' + field)
    require(run.finite(details.get('wall_seconds')) and type(details.get('outer_timeout')) is bool
            and type(details.get('exit_code')) is int, 'Invalid validator outcome')
    usage = details.get('resources') or {}
    require(usage.get('memory_limit_bytes') == 2**31 and usage.get('sampling_interval_seconds') == 0.01
            and type(usage.get('memory_limit_exceeded')) is bool, 'Validator resource settings differ')
    success = details['exit_code'] == 0 and not details['outer_timeout'] and not usage['memory_limit_exceeded']
    path = Path(str(log) + '.validation-response.json')
    if path.exists() and success:
        require(path.stat().st_size <= 64 * 2**20, 'Validator response exceeds limit')
        response = json.loads(path.read_text())
        require(all(k in response for k in ('verdict', 'branches', 'independent_checks')), 'Incomplete validator response')
        for key, value in response.items():
            observed = row.get(key)
            if key == 'verdict' and row.get('observed_verdict') is not None:
                observed = row['observed_verdict']
            elif key == 'property_truth' and row.get('observed_verdict') in DEFINITIVE:
                observed = (row['observed_verdict'] == 'reachable') == (query['kind'] == 'EF')
            require(same(observed, value), 'Validator response differs: ' + key)
    else:
        require(not success and not solved, 'Missing successful validator response')
    if solved:
        require(success and native_checked(row, query), 'Unchecked native answer')
        answer = json.loads(log.read_text())
        for key, value in dict(kind='original-property-v1', verdict=row['verdict'], property_truth=row['property_truth'],
                               property_id=query['property_id'], property_kind=query['kind'],
                               branch_count=len(query['branches']), deadline_exceeded=False).items():
            require(same(answer.get(key), value), 'Native answer differs: ' + key)
        require(all(run.finite(answer.get(k)) for k in ('parse_seconds', 'solve_seconds')), 'Invalid native frontend timings')
        require([a['branch'] for a in answer['attempts']] == list(range(len(answer['attempts']))), 'Noncontiguous native branches')
        require(len(answer['attempts']) == len(row['branches']), 'Native branch count differs from validator')
        require(all(a['outcome']['verdict'] == b.get('unchecked_verdict', b['verdict'])
                    for a, b in zip(answer['attempts'], row['branches'])), 'Native branch verdict differs')


def audit_row(row, query, plan, output):
    from analyze_application_expansion import failure_flags, native_checked
    require(row['verdict'] in DEFINITIVE | {'unknown'}, 'Non-normalized row verdict')
    require(row['repeat'] == 0 and row['family'] == query['family'] and row['property_kind'] == query['kind'], 'Row metadata differs')
    require(row['execution_attempted'] is True and row['collection_status'] == query['status'] == 'imported', 'Collection metadata differs')
    require(row['input_mode'] == 'rust-original-v1', 'Wrong native input mode')
    truth = (row['verdict'] == 'reachable') == (query['kind'] == 'EF') if row['verdict'] in DEFINITIVE else None
    require(row['property_truth'] is truth, 'Property polarity differs')
    require(run.finite(row['wall_seconds']) and type(row['exit_code']) is int and type(row['outer_timeout']) is bool, 'Invalid solver outcome')
    corpus = ROOT / plan['corpora'][row['corpus']]['path']
    tool = plan['binaries'][row['method']]
    command = [str(ROOT / tool['binary']), '--pnml', str(corpus / query['pnml']), '--xml', str(corpus / query['xml']),
               '--property-id', query['property_id'], '--method', 'portfolio-excess', '--seconds', '5.0',
               '--max-states', '2000000', '--buffer-agglomeration']
    require(row['command'] == command, 'Native command differs')
    log = output / row['corpus'] / f"{row['query']}.{row['method']}.0.rust-original.json"
    require(log.is_file(), 'Missing native raw output')
    resources(row, plan, log)
    validator(row, query, plan, corpus, output / row['corpus'], log)
    original = dict(row)
    original.pop('admission_failures')
    original['verdict'] = row.get('observed_verdict', row['verdict'])
    require(row['admission_failures'] == run.rejection_reasons(original, query), 'Admission reasons differ')
    if row['verdict'] in DEFINITIVE:
        require(row['wall_seconds'] <= 5 and row['exit_code'] == 0 and row['outer_timeout'] is False
                and not failure_flags(row) and not row['admission_failures'] and not row.get('validation_failure')
                and not row.get('answer_rejected') and native_checked(row, query), 'Invalid accepted answer')
    elif row.get('observed_verdict') in DEFINITIVE:
        require(bool(row['admission_failures']), 'Definitive answer silently rejected')


def reports(rows, queries, selected):
    from analyze_application_expansion import failure_flags
    indexed = {(r['corpus'], r['query'], r['method']): r for r in rows}
    result = {}
    cohorts = [('pooled', selected)]
    cohorts += [(name, {key for key in selected if key[0] == name}) for name, *_ in run.CORPORA]
    cohorts += [('family:' + family, {key for key in selected if queries[key]['family'] == family})
                for family in sorted({queries[k]['family'] for k in selected})]
    for label, cohort in cohorts:
        if not cohort:
            continue
        groups = defaultdict(list)
        for key in sorted(cohort):
            groups[tuple(b['sha256'] for b in queries[key]['branches'])].append(key)
        views = {}
        for name, chosen in [('all_properties', cohort), ('representatives', {min(g) for g in groups.values()})]:
            solved = {m: {key for key in chosen if indexed[*key, m]['verdict'] in DEFINITIVE} for m in run.METHODS}
            views[name] = dict(denominator=len(chosen), methods={m: dict(solved=len(solved[m]),
                par2_mean_seconds=statistics.mean(indexed[*key, m]['wall_seconds'] if key in solved[m] else 10 for key in chosen),
                solver_wall_total_seconds=sum(indexed[*key, m]['wall_seconds'] for key in chosen),
                validation_wall_total_seconds=sum((indexed[*key, m].get('validation') or {}).get('wall_seconds', 0) for key in chosen),
                verdicts=dict(Counter(indexed[*key, m]['verdict'] for key in chosen)),
                failure_flags=dict(Counter(flag for key in chosen for flag in failure_flags(indexed[*key, m])))) for m in run.METHODS},
                gains=[dict(corpus=c, query=q) for c, q in sorted(solved['candidate'] - solved['baseline'])],
                losses=[dict(corpus=c, query=q) for c, q in sorted(solved['baseline'] - solved['candidate'])])
        result[label] = dict(views=views, duplicate_groups=[g for g in groups.values() if len(g) > 1])
    return result


def audit_stage(folder, plan, stage):
    queries = verify_plan(folder, plan)
    execution_path, terminal_path = [folder / (stage + suffix) for suffix in ('-execution.json', '-terminal.json')]
    execution, terminal = [json.loads(p.read_text()) for p in (execution_path, terminal_path)]
    require(execution['plan_sha256'] == terminal['plan_sha256'] == run.sha(folder / 'plan.json'), 'Plan identity differs')
    require(execution['stage'] == terminal['stage'] == stage, 'Stage identity differs')
    require(execution['python'] == plan['python'] and execution['backend'] == plan['backend']
            and execution['host_policy'] == plan['host_policy'], 'Execution settings differ')
    require(terminal['exit_code'] == 0 and terminal['rows'] == plan['stages'][stage]['expected_rows']
            and terminal['failure'] is None and terminal['host_monitor_error'] is None, 'Stage incomplete')
    output = ROOT / 'results/verifypn-learning-20261004' / plan['campaign'] / stage
    artifacts = {str(p.relative_to(ROOT)): run.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    require(artifacts == terminal['artifact_sha256'], 'Artifact inventory or hashes differ')
    host = host_evidence(output / 'host.jsonl', plan['host_policy'])
    rows = [json.loads(line) for line in (output / 'runs.jsonl').read_text().splitlines()]
    require([{k: r[k] for k in ('corpus', 'query', 'method')} for r in rows] == plan['stages'][stage]['schedule'], 'Exact row schedule differs')
    issues = []
    for row in rows:
        try:
            audit_row(row, queries[row['corpus'], row['query']], plan, output)
        except Exception as error:
            issues.append(dict(corpus=row['corpus'], query=row['query'], method=row['method'], reason=repr(error)))
    truth, normalized = defaultdict(set), defaultdict(set)
    for row in rows:
        if row['verdict'] in DEFINITIVE:
            key = row['corpus'], row['query']
            truth[key].add(row['property_truth'])
            normalized[tuple(b['sha256'] for b in queries[key]['branches'])].add(row['verdict'])
    require(all(len(v) == 1 for v in truth.values()) and all(len(v) == 1 for v in normalized.values()), 'Accepted answers disagree')
    selected = {(q['corpus'], q['query']) for q in plan['selected_queries']}
    result = dict(status='failed' if issues else 'passed', stage=stage, plan_sha256=run.sha(folder / 'plan.json'),
                  terminal_sha256=run.sha(terminal_path), execution_sha256=run.sha(execution_path),
                  rows=len(rows), issues=issues, accepted_definitive_rows=sum(r['verdict'] in DEFINITIVE for r in rows),
                  host=host, scope=plan['scope'], reports=reports(rows, queries, selected),
                  audit_scope='Saved-evidence audit; independent certificate checking occurred in bounded workers during measurement.')
    return result, rows


def summary(folder, plan, blocks):
    rows = {stage: data for stage, (_, data) in blocks.items()}
    selected = {(q['corpus'], q['query']) for q in plan['selected_queries']}
    queries = index_queries(plan)
    indexed = {stage: {(r['corpus'], r['query'], r['method']): r for r in data} for stage, data in rows.items()}
    truth, normalized = defaultdict(set), defaultdict(set)
    for data in rows.values():
        for row in data:
            if row['verdict'] in DEFINITIVE:
                key = row['corpus'], row['query']
                truth[key].add(row['property_truth'])
                normalized[tuple(b['sha256'] for b in queries[key]['branches'])].add(row['verdict'])
    require(all(len(v) == 1 for v in truth.values()) and all(len(v) == 1 for v in normalized.values()), 'Cross-repeat answer disagreement')
    solved = {stage: {m: {key for key in selected if table[*key, m]['verdict'] in DEFINITIVE}
                     for m in run.METHODS} for stage, table in indexed.items()}
    repeatability = {m: dict(both=len(solved['repeat1'][m] & solved['repeat2'][m]),
                            either=len(solved['repeat1'][m] | solved['repeat2'][m])) for m in run.METHODS}
    stable_gains = set.intersection(*(s['candidate'] - s['baseline'] for s in solved.values()))
    stable_losses = set.intersection(*(s['baseline'] - s['candidate'] for s in solved.values()))
    common = set.intersection(*(s[m] for s in solved.values() for m in run.METHODS))
    ratios = {}
    for include_check in (False, True):
        logs = []
        for key in sorted(common):
            times = {}
            for m in run.METHODS:
                values = []
                for table in indexed.values():
                    row = table[*key, m]
                    values.append(row['wall_seconds'] + ((row.get('validation') or {}).get('wall_seconds', 0) if include_check else 0))
                times[m] = statistics.median(values)
            if all(value > 0 for value in times.values()):
                logs.append(math.log(times['baseline'] / times['candidate']))
        ratios['including_validation' if include_check else 'solver'] = dict(properties=len(logs),
                baseline_over_candidate_geomean=math.exp(statistics.mean(logs)) if logs else None)
    contended = plan['host_policy']['allow_contention'] or any(b[0]['host']['contention_observed'] for b in blocks.values())
    result = dict(status='passed', plan_sha256=run.sha(folder / 'plan.json'), properties=plan['properties'],
                  rows=sum(len(r) for r in rows.values()), scope=plan['scope'], contended=contended,
                  timing_interpretation='Descriptive only; no speed claim' if contended or plan['campaign'] != 'full' else 'Within frozen host thresholds; observational development evidence',
                  blocks={stage: report for stage, (report, _) in blocks.items()}, repeatability=repeatability,
                  stable_gains=[dict(corpus=c, query=q) for c, q in sorted(stable_gains)],
                  stable_losses=[dict(corpus=c, query=q) for c, q in sorted(stable_losses)],
                  conditional_timing=ratios, limitations=plan['limitations'])
    run.save(folder / 'summary.json', result)
    lines = ['# VerifyPN-inspired native development comparison', '', plan['scope'] + '.', '',
             result['timing_interpretation'] + '.', '', '| Method | Repeat 1 | Repeat 2 | Both | Either |',
             '|---|---:|---:|---:|---:|']
    for m in run.METHODS:
        lines.append(f"| {m} | {len(solved['repeat1'][m])}/{plan['properties']} | {len(solved['repeat2'][m])}/{plan['properties']} | {repeatability[m]['both']} | {repeatability[m]['either']} |")
    lines += ['', f"Stable paired gains/losses: **{len(stable_gains)}/{len(stable_losses)}**. All {result['rows']} rows retained.", '',
              'Per-corpus, per-family, original-property and ordered-branch representative views, failure counts, PAR2 and separate checking costs are in `summary.json`.', '',
              'Accepted answers were independently checked against original PNML/XML and every canonical branch during measurement. This audit inspects the saved evidence and does not rerun certificate checking.', '',
              'Build correspondence: `' + plan['build_correspondence'] + '`.', '']
    lines += ['- ' + limitation for limitation in plan['limitations']]
    with (folder / 'REPORT.md').open('x') as stream:
        stream.write('\n'.join(lines) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', default='full')
    parser.add_argument('stage', choices=['repeat1', 'repeat2', 'all'])
    args = parser.parse_args()
    folder = run.campaign_path(args.campaign)
    plan = json.loads((folder / 'plan.json').read_text())
    stages = ['repeat1', 'repeat2'] if args.stage == 'all' else [args.stage]
    blocks = {}
    for stage in stages:
        path = folder / (stage + '-audit.json')
        try:
            result, rows = audit_stage(folder, plan, stage)
        except Exception as error:
            result, rows = dict(status='failed', stage=stage, plan_sha256=run.sha(folder / 'plan.json'), issues=[repr(error)]), []
        if path.exists():
            require(json.loads(path.read_text()) == result, 'Saved audit differs; preserve evidence and investigate')
        else:
            run.save(path, result)
        print(json.dumps(dict(stage=stage, status=result['status'], issues=result['issues'],
                              rows=result.get('rows'), accepted=result.get('accepted_definitive_rows'))))
        if result['status'] != 'passed':
            return 1
        blocks[stage] = result, rows
    if args.stage == 'all':
        report = summary(folder, plan, blocks)
        print(json.dumps(dict(status=report['status'], stable_gains=len(report['stable_gains']), stable_losses=len(report['stable_losses']))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
