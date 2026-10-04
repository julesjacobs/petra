"""Audit saved competitive evidence locally; never execute a solver or checker."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import random
import re
import sys

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
REMOTE = '/home/jules/experiments/pvass-publication'
sys.path.insert(0, str(F / 'analysis-source'))
from analyze_application_expansion import corpus_groups, failure_flags, native_checked
spec = importlib.util.spec_from_file_location('prior_artifact_audit', F / 'analysis-source/audit-general-development-v3-linux-v1.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
DEFINITIVE = {'reachable', 'unreachable'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def solved(row):
    return row.get('verdict') in DEFINITIVE and type(row.get('property_truth')) is bool


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def local_path(remote):
    path = PurePosixPath(remote)
    prefix = PurePosixPath(REMOTE)
    if not path.is_relative_to(prefix):
        raise ValueError(f'Path outside remote workspace: {remote}')
    return ROOT / path.relative_to(prefix)


def option(command, flag):
    return command[command.index(flag) + 1]


class Audit:
    def __init__(self):
        self.issues, self.warnings, self.artifacts, self.identities = [], [], {}, []

    def check(self, condition, message):
        if not condition:
            self.issues.append(message)
        return condition

    def record(self, path):
        digest = sha(path)
        self.artifacts[str(path.relative_to(ROOT))] = digest
        return digest

    def read(self, path):
        self.record(path)
        return json.loads(path.read_text())

    def pin(self, path, expected):
        self.check(self.record(path) == expected, f'Hash mismatch: {path}')


def native_validation(a, plan, block, query, row, log):
    label = f"{block['name']}/{row['query']}/{row['method']}"
    v = row.get('validation')
    if v is None:
        a.check(not solved(row), label + ': missing native validation')
        return
    a.record(Path(str(log) + '.validation.log'))
    request = a.read(Path(str(log) + '.validation-request.json'))
    for k, value in dict(seconds_limit=60, memory_limit_bytes=2**31, response_limit_bytes=64*2**20,
                         dag_check_max_work=200000000, included_in_solver_timing=False).items():
        a.check(v.get(k) == value, label + ': validator limit ' + k)
    a.check(request.get('query') == query, label + ': validator query differs')
    for k, value in dict(corpus=REMOTE + '/' + plan['corpus'], artifacts=REMOTE + '/' + block['output'],
                         memory_bytes=2**31, response_bytes=64*2**20, dag_check_max_work=200000000,
                         exit_code=row['exit_code'], outer_timeout=row['outer_timeout'], mode='rust-original-v1',
                         log=REMOTE + '/' + str(log.relative_to(ROOT))).items():
        a.check(request.get(k) == value, label + ': validator request ' + k)
    response_path = Path(str(log) + '.validation-response.json')
    success = v.get('exit_code') == 0 and not v.get('outer_timeout') and not (v.get('resources') or {}).get('memory_limit_exceeded')
    if response_path.exists():
        response = a.read(response_path)
        if success:
            a.check(all(k in response for k in ['verdict', 'branches', 'independent_checks']), label + ': incomplete validator response')
            for k, value in response.items():
                normalized_failure = (k == 'verdict' and value not in DEFINITIVE | {'unknown'}
                                      and row.get('verdict') == 'unknown'
                                      and 'nondefinitive-failure' in row.get('admission_failures', []))
                a.check(row.get(k) == value or normalized_failure, label + ': validator response ' + k)
    else:
        a.check(not success and not solved(row), label + ': absent successful validator response')
    if solved(row):
        a.check(success and native_checked(row, query), label + ': unchecked native branches')
        answer = a.read(log)
        for k, value in dict(verdict=row['verdict'], property_id=query['property_id'], property_kind=query['kind'],
                             branch_count=len(query['branches']), deadline_exceeded=False).items():
            a.check(answer.get(k) == value, label + ': native answer ' + k)


def resource_evidence(a, plan, row, log, label):
    usage = row.get('resources') or {}
    if not row.get('execution_attempted'):
        a.warnings.append(label + ': execution not attempted, retained')
        return
    for k, value in dict(runner='linux-systemd-user', cpus=[8], memory_limit_bytes=2**31, perf_enabled=True).items():
        a.check(usage.get(k) == value, label + ': resource setting ' + k)
    state = a.read(Path(str(log) + '.systemd.json'))
    a.check(state == usage.get('systemd_properties'), label + ': cgroup sidecar differs')
    a.check(state.get('Result') == usage.get('systemd_result'), label + ': cgroup result differs')
    a.check(usage.get('memory_limit_exceeded') is (state.get('Result') == 'oom-kill'), label + ': OOM flag differs')
    for key, field, scale in [('CPUUsageNSec', 'cpu_seconds', 1e9), ('MemoryPeak', 'peak_memory_bytes', 1)]:
        value = state.get(key)
        expected = None if value in (None, '', '[not set]', 'infinity', '18446744073709551615') else int(value)/scale
        a.check(usage.get(field) == expected, label + ': cgroup ' + field)
    if state.get('Result') in ('timeout', 'oom-kill'):
        a.check(row.get('outer_timeout') is True, label + ': missing cgroup timeout flag')
    perf = Path(str(log) + '.perf.csv')
    counters = usage.get('perf_counters') or {}
    if perf.exists():
        a.record(perf)
        parsed, problems = prior.parse_perf(perf)
        if counters:
            a.check(not problems and parsed == counters, label + ': perf sidecar differs')
        else:
            a.warnings.append(label + ': no accepted counters; raw perf retained')
    else:
        a.check(not counters, label + ': recorded counters without sidecar')
        a.warnings.append(label + ': missing perf sidecar')
    availability = {event: prior.perf_status(usage, event) for event in ['instructions:u', 'cycles:u', 'task-clock']}
    if any(v != 'full-coverage' for v in availability.values()):
        a.warnings.append(dict(row=label, perf_availability=availability))


def command_evidence(a, plan, block, query, row, label):
    cmd, method = row['command'], row['method']
    pnml, xml = [str(PurePosixPath(REMOTE) / plan['corpus'] / query[k]) for k in ['pnml', 'xml']]
    prefix = REMOTE + '/' + block['output'] + f"/{query['name']}.{method}.0"
    if method == 'native-excess':
        expected = [REMOTE + '/' + plan['candidate_binary'], '--pnml', pnml, '--xml', xml,
                    '--property-id', query['property_id'], '--method', 'portfolio-excess', '--seconds', '5.0',
                    '--max-states', '2000000', '--buffer-agglomeration']
        a.check(cmd == expected, label + ': exact native command differs')
    elif method == 'verifypn-default':
        a.check(cmd == [plan['verifypn']['binary'], '-x', '1', pnml, xml], label + ': exact VerifyPN command differs')
    elif method == 'smpt-mcc-portable':
        expected = [REMOTE + '/vendor/venv/bin/python', '-m', 'smpt', '-n', pnml, '--xml', xml, '--methods',
                    *plan['smpt_configurations'][method], '--mcc', '--timeout', '5', '--show-time', '--show-techniques',
                    '--show-model', '--export-proof', prefix + '.proof', '--auto-reduce']
        a.check(cmd == expected, label + ': exact SMPT command differs')
        for k, value in plan['smpt_scheduling'][method].items():
            a.check(row.get(k) == value, label + ': SMPT scheduling ' + k)
    elif method == 'its-mcc':
        opts = plan['its_harness_options']
        config = option(opts, '--its-runtime-config')
        expected = [REMOTE + '/vendor/venv/bin/python', REMOTE + '/' + plan['runner_source'] + '/scripts/its_original.py',
                    '--runtime-config', config, '--pnml', pnml, '--xml', xml,
                    '--property-id', query['property_id'], '--artifacts', prefix + '.its-artifacts', '--seconds', '5.0']
        a.check(cmd == expected, label + ': exact ITS command differs')


def external_evidence(a, plan, query, row, log, label):
    method = row['method']
    spec = importlib.util.spec_from_file_location('frozen_external_parser', ROOT / plan['runner_source'] / 'scripts/external_verdict.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = log.read_text(errors='replace')
    if method == 'its-mcc':
        logs, total = [], 0
        artifacts = local_path(row['artifacts'])
        paths = sorted(p for p in artifacts.rglob('*') if p.is_file()
                       and (p.suffix.lower() in ('.log', '.out', '.err') or p.name in ('stdout', 'stderr')))
        observed = []
        unreadable = 'unreadable-underlying-tool-log' in row.get('admission_failures', [])
        if unreadable:
            a.check(not solved(row) and row.get('underlying_log_error'), label + ': unrecorded ITS read failure')
            a.warnings.append(label + ': retained underlying ITS log read failure')
            paths = [local_path(item['path']) for item in row.get('underlying_logs', [])]
            a.check(all(p.is_relative_to(artifacts) for p in paths), label + ': ITS log outside artifact directory')
        for path in paths:
            data = path.read_bytes()
            total += len(data)
            if total > 64*2**20:
                break
            logs.append(data.decode('utf-8', errors='replace'))
            observed.append(dict(path=REMOTE + '/' + str(path.relative_to(ROOT)), sha256=sha(path), bytes=len(data)))
        a.check(observed == row.get('underlying_logs'), label + ': underlying ITS logs differ')
        if solved(row):
            answer = json.loads(text)
            a.check(answer == row.get('its_summary'), label + ': ITS saved summary differs')
            a.check(answer.get('property_id') == query['property_id'] and answer.get('property_kind') == query['kind'], label + ': ITS saved property differs')
            a.check(answer.get('property_truth') is row['property_truth'] and answer.get('verdict') == row['verdict'], label + ': ITS saved answer differs')
            a.check(answer.get('tool_exit_code') == 0 and not answer.get('errors') and not answer.get('timed_out')
                    and not answer.get('capability_failures') and observed, label + ': ITS tool failed')
            a.check(all(finite(answer.get(k)) for k in ['stage_seconds','tool_seconds','parse_seconds','total_seconds'])
                    and answer['total_seconds'] <= 5, label + ': ITS timings differ')
            a.check(a.read(artifacts / 'result.json') == answer, label + ': ITS artifact summary differs')
        parsed = module.parse('\n'.join(logs), query['property_id'], query['kind'], row.get('tool_exit_code'),
                              row['outer_timeout'], wall=row['wall_seconds'], seconds=5)
    else:
        parsed = module.parse(text, query['property_id'], query['kind'], row['exit_code'],
                              row['outer_timeout'], wall=row['wall_seconds'], seconds=5)
        for key in ['observed_verdict','capability_failures','subprocess_error']:
            a.check(row.get(key) == parsed[key], label + ': parsed external field ' + key)
    for key in ['formula_output','observed_formula_results']:
        a.check(row.get(key) == parsed[key], label + ': parsed external field ' + key)
    a.check(set(parsed['admission_failures']) <= set(row.get('admission_failures', [])), label + ': lost external admission failure')
    if solved(row):
        a.check(parsed['verdict'] == row['verdict'] and not row.get('admission_failures'), label + ': invalid external acceptance')


def audit_block(a, plan, block, queries):
    output = ROOT / block['output']
    terminal = a.read(F / (block['name'] + '-terminal.json'))
    a.check(terminal['plan_sha256'] == sha(F / 'plan.json') and terminal['exit_code'] == 0 and terminal['rows'] == 1472,
            block['name'] + ': incomplete terminal')
    files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    a.check(files == terminal['artifact_sha256'], block['name'] + ': terminal artifact set or hashes differ')
    a.artifacts.update(files)
    execution = a.read(F / (block['name'] + '-execution.json'))
    a.check(execution['plan_sha256'] == sha(F / 'plan.json') and execution['command'] == block['command'], block['name'] + ': execution differs')
    env = a.read(output / 'environment.json')
    for key in ['seconds', 'max_states', 'memory_mib', 'outer_grace', 'linux_cpus', 'perf', 'manifest_sha256']:
        a.check(env.get(key) == plan[key], block['name'] + ': environment ' + key)
    for key, value in dict(repeat=1, queries=368, methods=block['methods'], order_seed=block['order_seed'],
                           property_order=block['property_order'], rust_original=True, native_original=False,
                           rust_original_methods=[], smpt_original=True, track_resources=True, workspace_root=REMOTE,
                           buffer_agglomeration_methods=['native-excess'], target_zero_trap_methods=[],
                           target_path_potential_methods=[], geometric_branches_methods=[],
                           binary_sha256=plan['candidate_binary_sha256']).items():
        a.check(env.get(key) == value, block['name'] + ': environment ' + key)
    a.check(env.get('native_tools') == {'native-excess': dict(engine='portfolio-excess', binary=REMOTE + '/' + plan['candidate_binary'], binary_sha256=plan['candidate_binary_sha256'])}, block['name'] + ': native tool registration')
    limits = dict(enabled=True, seconds=60, memory_mib=2048, response_mib=64, dag_check_max_work=200000000, included_in_solver_timing=False)
    a.check(env.get('bounded_validation') == limits, block['name'] + ': validation limits')
    a.check(env.get('collection_counts') == dict(planned=368, imported=368, unsupported=0, explicitly_unobserved=0), block['name'] + ': collection denominator')
    a.check(env.get('smpt_configurations') == plan['smpt_configurations'] and env.get('smpt_scheduling') == plan['smpt_scheduling'], block['name'] + ': SMPT registration')
    for key in ['binary_sha256', 'source_commit', 'source_status', 'configurations']:
        a.check(env.get('verifypn', {}).get(key) == plan['verifypn'][key], block['name'] + ': VerifyPN ' + key)
    for name, digest in env['script_sha256'].items():
        a.check(Path(name).name == name, 'Invalid runner source name')
        a.pin(output / 'runner-source' / name, digest)
        a.check(plan['required_file_sha256'].get(plan['runner_source'] + '/scripts/' + name) == digest, block['name'] + ': unpinned runner ' + name)
    recorded = {}
    for tool in env.get('tools', {}).values():
        recorded[tool['path']] = tool['sha256']
    recorded[env['native_python']] = env['native_python_sha256']
    recorded[env['verifypn']['binary']] = env['verifypn']['binary_sha256']
    recorded[REMOTE + '/' + plan['candidate_binary']] = env['binary_sha256']
    for name, digest in env['smpt_source_sha256'].items():
        recorded[env['smpt_root'] + '/' + name] = digest
    for path, digest in recorded.items():
        expected = plan['required_file_sha256'].get(str(local_path(path).relative_to(ROOT)))
        a.check(expected == digest, block['name'] + ': runtime identity ' + path)
    its = env.get('its', {})
    config = local_path(option(plan['its_harness_options'], '--its-runtime-config'))
    a.check(its.get('runtime_config_sha256') == sha(config) and its.get('runtime') == a.read(config), block['name'] + ': ITS runtime identity')
    for key, name in [('wrapper_sha256','its_original.py'),('adapter_sha256','its_adapter.py')]:
        a.check(its.get(key) == plan['required_file_sha256'].get(plan['runner_source'] + '/scripts/' + name), block['name'] + ': ITS ' + key)
    rows = [json.loads(line) for line in (output / 'runs.jsonl').read_text().splitlines()]
    a.check(len(rows) == 1472, block['name'] + ': row count')
    observed = [{k: row.get(k) for k in ['query', 'method', 'repeat']} for row in rows]
    expected = [{k: row[k] for k in ['query', 'method', 'repeat']} for row in block['schedule']]
    a.check(observed == expected, block['name'] + ': exact schedule differs')
    for row in rows:
        q, method = queries[row['query']], row['method']
        label = f"{block['name']}/{row['query']}/{method}"
        verdict = row.get('verdict')
        a.check(verdict in DEFINITIVE | {'unknown', 'error', 'unsupported'}, label + ': verdict')
        truth = (verdict == 'reachable') == (q['kind'] == 'EF') if verdict in DEFINITIVE else None
        a.check(row.get('property_truth') is truth, label + ': property semantics')
        for key, value in dict(property_kind=q['kind'], suite=q['suite'], collection_status=q['status'],
                               collection_observed=q.get('observed'), property_slot=q.get('property_slot'),
                               source_corpus=q['source_corpus'], family=q['family'], family_group=q.get('family_group')).items():
            a.check(row.get(key) == value, label + ': metadata ' + key)
        a.check(finite(row.get('wall_seconds')), label + ': invalid wall time')
        if solved(row):
            a.check(row['wall_seconds'] <= 5 and row.get('exit_code') == 0 and not failure_flags(row)
                    and not row.get('validation_failure') and not row.get('answer_rejected') and not row.get('admission_failures'), label + ': failed accepted answer')
        if row.get('wall_seconds', 0) > 5:
            a.check(not solved(row), label + ': accepted late answer')
        suffix = '.rust-original.json' if method == 'native-excess' else '.its-original.json' if method == 'its-mcc' else '.log'
        log = output / f"{row['query']}.{method}.0{suffix}"
        if row.get('execution_attempted'):
            a.record(log)
            resource_evidence(a, plan, row, log, label)
            command_evidence(a, plan, block, q, row, label)
            if method == 'native-excess':
                a.check(row.get('input_mode') == 'rust-original-v1', label + ': native input mode')
                native_validation(a, plan, block, q, row, log)
            else:
                a.check(row.get('input_mode') == {'verifypn-default':'verifypn-original','smpt-mcc-portable':'smpt-original','its-mcc':'its-original'}[method], label + ': external input mode')
                external_evidence(a, plan, q, row, log, label)
        else:
            a.check(not solved(row), label + ': answer without execution')
    return dict(name=block['name'], rows=rows, environment=env, accepted=sum(solved(r) for r in rows))


def run():
    a = Audit()
    for path in [Path(__file__), F/'analysis-source/analyze_application_expansion.py', F/'analysis-source/audit-general-development-v3-linux-v1.py']:
        a.record(path)
    blocks = []
    try:
        for name, digest in a.read(F / 'analysis-sha256.json').items():
            a.pin(ROOT / name, digest)
        plan = a.read(F / 'plan.json')
        protocol = a.read(F / 'protocol.json')
        a.check(plan['protocol'] == protocol and plan['protocol_sha256'] == sha(F / 'protocol.json'), 'Protocol identity differs')
        a.check(plan['properties'] == 368 and plan['representatives'] == 366 and plan['expected_rows'] == 2944, 'Plan denominator differs')
        runner_spec = importlib.util.spec_from_file_location('frozen_campaign_commands', F / 'run.py')
        runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(runner)
        for block in plan['blocks']:
            a.check(block['command'] == runner.command(plan, block), block['name'] + ': frozen invocation command differs')
        terminal = a.read(F / 'terminal.json')
        a.check(terminal['plan_sha256'] == sha(F / 'plan.json') and terminal['exit_code'] == 0 and terminal['completed'] == ['repeat1', 'repeat2'], 'Suite incomplete')
        execution = a.read(F / 'execution.json')
        a.check(execution['plan_sha256'] == sha(F / 'plan.json') and execution['capability_sha256'] == sha(F / 'capability.json'), 'Suite execution identities differ')
        capability = a.read(F / 'capability.json')
        a.check(capability['status'] == 'passed' and capability['plan_sha256'] == sha(F / 'plan.json') and capability['methods'] == plan['methods'], 'Capability missing or mismatched')
        a.check(capability['its_qualification_sha256'] == sha(ROOT / plan['its_qualification']), 'ITS qualification identity differs')
        qualification = a.read(ROOT / plan['its_qualification'])
        a.check(qualification['status'] == 'passed', 'ITS runtime unqualified')
        manifest = a.read(ROOT / plan['corpus'] / 'manifest.json')
        a.check(sha(ROOT / plan['corpus'] / 'manifest.json') == plan['manifest_sha256'], 'Manifest hash differs')
        queries = {q['name']: q for q in manifest['queries']}
        groups = corpus_groups(manifest)
        a.check(len(queries) == 368 and len(groups) == 366 and all(q['status'] == 'imported' for q in queries.values()), 'Manifest denominator differs')
        a.check(Counter(q['source_corpus'] for q in queries.values()) == {'existing176':176, 'expansion192':192}, 'Unexpected corpus membership')
        inputs = {}
        for q in queries.values():
            for path, digest in [(q[k], q[k+'_sha256']) for k in ['pnml', 'xml', 'net', 'property']] + [(b['path'], b['sha256']) for b in q['branches']]:
                p = (ROOT / plan['corpus'] / path).resolve()
                if p not in inputs:
                    a.pin(p, digest)
                    inputs[p] = p.stat().st_size
        # Local source/input pins are checked from fetched bytes. Unfetched executable
        # identities remain explicitly attributed to remote freeze and environment evidence.
        for name, digest in plan['required_file_sha256'].items():
            path = ROOT / name
            if path.exists() and not name.startswith('vendor/'):
                a.pin(path, digest)
                evidence = 'local bytes'
            else:
                evidence = 'remote freeze receipt; environment checked where reported'
            a.identities.append(dict(path=name, sha256=digest, evidence=evidence))
        for name, digest in plan.get('external_file_sha256', {}).items():
            a.identities.append(dict(path=name, sha256=digest, evidence='remote freeze receipt'))
        for index, block in enumerate(plan['blocks']):
            shuffled = list(queries)
            random.Random(protocol['blocks'][index]['order_seed']).shuffle(shuffled)
            a.check(block['order_seed'] == protocol['blocks'][index]['order_seed'] and block['property_order'] == shuffled, 'Frozen query schedule differs')
            methods = plan['methods'] if index == 0 else plan['methods'][::-1]
            expected = [dict(query=q, method=m, repeat=0, source_corpus=queries[q]['source_corpus'])
                        for i,q in enumerate(shuffled) for m in methods[i%4:]+methods[:i%4]]
            a.check(block['methods'] == methods and block['schedule'] == expected, 'Frozen method schedule differs')
            result = audit_block(a, plan, block, queries)
            a.check(result['environment']['input_preflight'] == dict(mode='streaming-deduplicated-sha256', unique_files=len(inputs), bytes_hashed=sum(inputs.values())), block['name'] + ': input preflight')
            blocks.append(result)
        truths, canonical = defaultdict(set), defaultdict(set)
        representative = {q:g[0] for g in groups for q in g}
        for b in blocks:
            for row in b['rows']:
                if solved(row):
                    truths[row['query']].add(row['property_truth'])
                    canonical[representative[row['query']]].add(row['verdict'])
        a.check(all(len(v) == 1 for v in truths.values()), 'Cross-method or cross-repeat disagreement')
        a.check(all(len(v) == 1 for v in canonical.values()), 'Canonical duplicate disagreement')
    except Exception as error:
        a.issues.append(f'Audit interrupted: {type(error).__name__}: {error}')
    return dict(status='passed' if not a.issues else 'failed', issues=a.issues, warnings=a.warnings,
                blocks=[dict(name=b['name'], rows=len(b['rows']), accepted=b['accepted']) for b in blocks],
                artifact_sha256=a.artifacts, identities=a.identities, source_sha256=sha(Path(__file__)),
                scope='Saved-evidence consistency audit. Native checks are inspected, not rerun. External answers remain tool-reported. Missing runtime bytes are labeled.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=F/'audit.json')
    args = parser.parse_args()
    report = run()
    with args.output.open('x') as out:
        json.dump(report, out, indent=2)
        out.write('\n')
    print(json.dumps(dict(status=report['status'], issues=len(report['issues']), warnings=len(report['warnings']))))
    raise SystemExit(report['status'] != 'passed')
