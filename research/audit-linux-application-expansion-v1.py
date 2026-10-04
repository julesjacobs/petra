#!/usr/bin/env python3
"""Audit fetched application-expansion results locally; never run a solver or contact Linux.

Default outputs: research/linux-application-expansion-v1-verification.{json,md}.
Exit 0 means the recorded artifacts pass this consistency audit; exit 1 retains
an incomplete/failed report. This does not rerun independent proof checkers.
"""
import argparse
import csv
import random
from collections import Counter, defaultdict
import hashlib
import json
import math
import posixpath
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from analyze_application_expansion import analyze, corpus_groups, native_command, registered_native_tools

REMOTE = '/home/jules/experiments/pvass-publication/'
DEFINITIVE = {'reachable', 'unreachable'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(path):
    normalized = posixpath.normpath(path)
    if not normalized.startswith(REMOTE):
        raise ValueError(f'Unexpected remote workspace path: {path}')
    return normalized[len(REMOTE):]


def perf_status(resources, event):
    counter = (resources.get('perf_counters') or {}).get(event) or {}
    value = counter.get('value')
    coverage = counter.get('time_running_percent')
    runtime = counter.get('event_runtime_ns')
    numeric = lambda x: type(x) in (int, float) and math.isfinite(x)
    if not numeric(value) or value < 0:
        return 'missing-or-invalid-value'
    if not numeric(coverage) or not 0 < coverage <= 100 or not numeric(runtime) or runtime <= 0:
        return 'missing-or-invalid-coverage'
    return 'full-coverage' if coverage == 100 else 'multiplexed'


def parse_perf(path):
    """Decode saved counters without importing or running the frozen runner."""
    counters, problems = {}, []
    for fields in csv.reader(path.read_text().splitlines(), delimiter=';'):
        if len(fields) < 5 or fields[2] not in ('instructions:u','cycles:u','task-clock','task-clock:u'):
            continue
        value, unit, observed, runtime, percentage = fields[:5]
        event = 'task-clock' if observed == 'task-clock:u' else observed
        if event in counters:
            problems.append('Duplicate perf event: '+event)
        try:
            number = float(value) if '.' in value else int(value)
            runtime, percentage = float(runtime), float(percentage.rstrip('%'))
            if not all(math.isfinite(x) for x in (number,runtime,percentage)):
                raise ValueError('nonfinite counter')
        except ValueError as error:
            problems.append(f'{event}: {error}')
            continue
        counters[event] = dict(value=number,unit=unit,observed_event=observed,event_runtime_ns=runtime,
                               time_running_percent=percentage,raw_fields=fields)
    return counters, problems


def audit(root, plan_path, results):
    issues, warnings, identities, artifacts = [], [], [], {}
    invalid_rows = []
    def label_path(path):
        return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)

    def check(condition, message):
        if not condition:
            issues.append(message)
        return condition

    def read(path):
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise ValueError('expected JSON object')
            artifacts[label_path(path)] = sha(path)
            return data
        except (OSError, ValueError) as error:
            issues.append(f'{path}: {error}')
            return {}

    def identity(path, expected, source):
        try:
            actual = sha(path)
            valid = check(actual == expected, f'Identity differs: {path}')
        except OSError as error:
            actual, valid = None, False
            issues.append(f'Missing identity evidence {path}: {error}')
        identities.append(dict(path=str(path.relative_to(root)), expected=expected,
                               actual=actual, valid=valid, evidence=source))

    plan = read(plan_path)
    if not plan:
        return dict(status='failed', audit_issues=issues, full_rows=[])
    corpus = root / plan['corpus']
    manifest = read(corpus/'manifest.json')
    environment = read(results/'environment.json')
    identity(corpus/'manifest.json', plan['manifest_sha256'], 'registered manifest bytes')
    rows = []
    run_path = results/'runs.jsonl'
    try:
        artifacts[str(run_path.relative_to(root))] = sha(run_path)
        for line_number, line in enumerate(run_path.read_text().splitlines(), 1):
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError('row is not an object')
                rows.append(row)
            except ValueError as error:
                issues.append(f'Invalid row {line_number}: {error}')
                invalid_rows.append(dict(line_number=line_number, raw_line=line))
    except OSError as error:
        issues.append(str(error))
    methods = list(plan['methods'])
    native_tools = {}
    try:
        native_tools, workspace = registered_native_tools(plan, environment)
        check(workspace is None or workspace.rstrip('/') == REMOTE.rstrip('/'),
              'Registered native workspace differs from Linux workspace')
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        issues.append(f'Native registration invalid: {error}')
    artifacts[label_path(Path(__file__).resolve())] = sha(Path(__file__).resolve())
    artifacts[label_path(ROOT/'scripts/analyze_application_expansion.py')] = sha(ROOT/'scripts/analyze_application_expansion.py')
    queries = {q['name']: q for q in manifest.get('queries', [])}
    check(len(queries) == len(manifest.get('queries', [])) == plan['properties'], 'Registered query denominator differs')
    expected = {(q, m, i) for q in queries for m in methods for i in range(plan['repeat'])}
    counts = Counter((r.get('query'), r.get('method'), r.get('repeat')) for r in rows)
    check(len(rows) == plan['expected_rows'], 'Registered row denominator differs')
    check(set(counts) == expected and all(v == 1 for v in counts.values()),
          'Incomplete, duplicated or unexpected query/method/repeat matrix')
    check(set(environment.get('methods', [])) == set(methods), 'Environment methods differ')
    order = environment.get('property_order', [])
    check(len(order) == len(queries) and set(order) == set(queries), 'Property order does not cover all queries once')
    for key in ['seconds', 'repeat', 'max_states', 'memory_mib', 'outer_grace', 'order_seed', 'linux_cpus', 'perf']:
        check(environment.get(key) == plan[key], f'Environment setting differs: {key}')
    check(environment.get('queries') == plan['properties'], 'Environment query count differs')
    check(environment.get('manifest_sha256') == plan['manifest_sha256'], 'Recorded manifest identity differs')
    check(environment.get('binary_sha256') == plan['native_binary_sha256'], 'Recorded native binary identity differs')
    check(environment.get('rust_original') is True and environment.get('track_resources') is True and
          environment.get('native_original') is False and environment.get('smpt_original') is True and
          environment.get('rust_original_methods') == [], 'Original input/resource mode differs')
    check(environment.get('collection_counts') == dict(planned=len(queries), imported=sum(q['status']=='imported' for q in queries.values()), unsupported=sum(q['status']!='imported' for q in queries.values()), explicitly_unobserved=sum(q.get('observed') is False for q in queries.values())),
          'Collection denominator differs')
    validation_plan = plan['validation']
    limits = dict(enabled=True, seconds=validation_plan['seconds'], memory_mib=validation_plan['memory_mib'],
                  response_mib=validation_plan['response_mib'], dag_check_max_work=validation_plan['dag_check_max_work'],
                  included_in_solver_timing=False)
    check(environment.get('bounded_validation') == limits, 'Uniform validation limits differ')
    groups = corpus_groups(manifest) if manifest else []
    expected_representatives = plan.get('exact_ordered_branch_representatives')
    if expected_representatives is not None:
        check(len(groups) == expected_representatives, 'Registered representative denominator differs')
    shuffled = list(queries)
    random.Random(plan['order_seed']).shuffle(shuffled)
    check(order == shuffled, 'Registered randomized property order differs')
    expected_order = []
    # The frozen runner rotates the environment's method order for each query.
    for index, name in enumerate(order):
        method_order = environment.get('methods', [])
        rotated = method_order[index % len(method_order):] + method_order[:index % len(method_order)] if method_order else []
        expected_order.extend((name, method, repetition) for repetition in range(plan['repeat']) for method in rotated)
    check([(r.get('query'),r.get('method'),r.get('repeat')) for r in rows] == expected_order,
          'Recorded row order differs from frozen scheduling')
    inputs = {}
    for query in queries.values():
        if query['status'] != 'imported':
            continue
        pairs = [(corpus/query[k],query[k+'_sha256']) for k in ('net','property','pnml','xml')]
        pairs.extend((corpus/b['path'],b['sha256']) for b in query['branches'])
        for path,digest in pairs:
            if path.resolve() not in inputs:
                identity(path,digest,'manifest input bytes')
                inputs[path.resolve()] = path.stat().st_size if path.exists() else 0
    check(environment.get('input_preflight') == dict(mode='streaming-deduplicated-sha256',unique_files=len(inputs),bytes_hashed=sum(inputs.values())),
          'Input preflight differs from manifest inputs')
    for path, digest in plan['selection_evidence'].items():
        identity(root/path, digest, 'local selection evidence bytes')

    # Current local scripts may have evolved: use the fetched runner snapshot.
    recorded = {}
    for name, digest in environment.get('script_sha256', {}).items():
        check(Path(name).name == name, f'Invalid runner snapshot name: {name}')
        identity(results/'runner-source'/name, digest, 'environment-pinned fetched runner bytes')
        if 'native_tools' in plan:
            check(plan['required_file_sha256'].get('scripts/'+name) == digest,
                  f'Runner snapshot missing or different in registered file identities: {name}')
        recorded['scripts/'+name] = digest
    for tool in environment.get('native_tools', {}).values():
        recorded[relative(tool['binary'])] = tool['binary_sha256']
    if environment.get('verifypn'):
        recorded[relative(environment['verifypn']['binary'])] = environment['verifypn']['binary_sha256']
    if environment.get('native_python'):
        recorded[relative(environment['native_python'])] = environment['native_python_sha256']
    for tool in environment.get('tools', {}).values():
        recorded[relative(tool['path'])] = tool['sha256']
    for name, digest in environment.get('smpt_source_sha256', {}).items():
        recorded[relative(environment['smpt_root']+'/'+name)] = digest
    for method, tool in native_tools.items():
        path = relative(tool['binary'])
        check(plan['required_file_sha256'].get(path) == tool['binary_sha256'],
              f'Native binary missing or different in registered file identities: {method}')
    for path, expected_hash in plan['required_file_sha256'].items():
        if path.startswith('scripts/'):
            identity(results/'runner-source'/Path(path).name, expected_hash, 'fetched runner bytes')
            check(recorded.get(path) == expected_hash, f'Recorded runner identity differs: {path}')
        elif path.startswith('vendor/'):
            check(recorded.get(path) == expected_hash, f'Recorded tool/source identity differs: {path}')
            identities.append(dict(path=path, expected=expected_hash, actual=recorded.get(path),
                                   valid=recorded.get(path)==expected_hash,
                                   evidence='environment-reported identity; binary bytes not independently fetched here'))
        else:
            identity(root/path, expected_hash, 'local frozen bytes')
            if path in {relative(tool['binary']) for tool in native_tools.values()}:
                check(recorded.get(path) == expected_hash, 'Native tool map identity differs')
    check(environment.get('smpt_configurations') == plan['smpt_configurations'], 'SMPT configuration differs')
    for key in ['binary_sha256', 'source_commit', 'source_status', 'configurations']:
        check(environment.get('verifypn', {}).get(key) == plan['verifypn'][key], f'VerifyPN configuration differs: {key}')
    row_audits = []
    for row in rows:
        name, method, repetition = row.get('query'), row.get('method'), row.get('repeat')
        label = f'{name}/{method}/{repetition}'
        if name not in queries or method not in methods:
            continue
        query = queries[name]
        native = method.startswith('native-')
        res = row.get('resources') or {}
        definitive = row.get('verdict') in DEFINITIVE
        command = row.get('command', [])
        def option(flag):
            try:
                return command[command.index(flag)+1]
            except (ValueError, IndexError):
                return None
        check(row.get('verdict') in DEFINITIVE | {'unknown','error','unsupported'}, f'{label}: invalid verdict')
        check(row.get('property_kind') == query.get('kind'), f'{label}: property kind differs')
        expected_truth = (row['verdict']=='reachable') == (query['kind']=='EF') if definitive else None
        check(row.get('property_truth') is expected_truth, f'{label}: property truth differs')
        check(row.get('suite') == query['suite'], f'{label}: suite differs')
        check(row.get('collection_status') == query['status'] and row.get('collection_observed') == query.get('observed') and
              row.get('property_slot') == query.get('property_slot'), f'{label}: collection metadata differs')
        mode = 'rust-original-v1' if native else 'verifypn-original' if method=='verifypn-default' else 'smpt-original'
        check(row.get('input_mode') == mode, f'{label}: input mode differs')
        if query['status'] != 'imported':
            check(row.get('execution_attempted') is False and row.get('verdict') == 'unsupported' and
                  row.get('failure_stage') == 'collection' and row.get('property_truth') is None and
                  not command and row.get('resources') is None and not row.get('validation'),
                  f'{label}: unavailable input was executed or given a result')
            row_audits.append(dict(query=name, method=method, repeat=repetition,
                                   collection_unavailable=True, execution_attempted=False))
            continue
        if row.get('execution_attempted'):
            check(res.get('runner')=='linux-systemd-user', f'{label}: incorrect resource runner')
            check(res.get('cpus')==plan['linux_cpus'], f'{label}: CPU affinity differs')
            check(res.get('memory_limit_bytes')==plan['memory_mib']*1024**2, f'{label}: memory limit differs')
            check(res.get('perf_enabled') is True, f'{label}: perf disabled')
        else:
            warnings.append(f'{label}: execution not attempted; retained in denominator')
        if definitive:
            check(not any([row.get('outer_timeout'),row.get('deadline_exceeded'),res.get('memory_limit_exceeded'),
                           row.get('failure_stage'),row.get('validation_failure')]), f'{label}: definitive result despite failure/deadline')
            if native:
                check(row.get('exit_code')==0, f'{label}: native definitive result after process error')
            elif row.get('exit_code') != 0:
                warnings.append(f'{label}: external definitive output with nonzero exit retained for investigation')
        try:
            pnml = option('--pnml') if native else option('-n') if method=='smpt-full-portable' else command[-2]
            xml = option('--xml') if method!='verifypn-default' else command[-1]
            for path, key in [(pnml,'pnml'),(xml,'xml')]:
                check((root/relative(path)).resolve()==(corpus/query[key]).resolve(), f'{label}: command {key} differs')
            if native:
                check(command == native_command(plan, query, method, native_tools, REMOTE),
                      f'{label}: exact native command differs')
            elif method=='smpt-full-portable':
                check(float(option('--timeout'))==plan['seconds'], f'{label}: SMPT timeout differs')
                check(row.get('enabled_methods')==plan['smpt_configurations'][method], f'{label}: enabled SMPT modes differ')
                check('--auto-reduce' in command, f'{label}: SMPT reduction missing')
                check(relative(command[0])=='vendor/venv/bin/python' and command[1:3]==['-m','smpt'], f'{label}: SMPT entrypoint differs')
                expected_command = [command[0],'-m','smpt','-n',pnml,'--xml',xml,'--methods',
                    *plan['smpt_configurations'][method],'--timeout',str(math.ceil(plan['seconds'])),
                    '--show-time','--show-techniques','--show-model','--export-proof',
                    REMOTE+plan['output']+f'/{name}.{method}.{repetition}.proof','--auto-reduce']
                check(command==expected_command, f'{label}: exact SMPT command differs')
            else:
                check(relative(command[0])==relative(plan['verifypn']['binary']) and command[1:3]==['-x','1'] and len(command)==5,
                      f'{label}: VerifyPN command differs')
        except (ValueError, TypeError, IndexError, KeyError) as error:
            issues.append(f'{label}: malformed command: {error}')
        suffix = '.rust-original.json' if native else '.log'
        log = results/f'{name}.{method}.{repetition}{suffix}'
        for path in [log, Path(str(log)+'.systemd.json')]:
            if path.exists():
                artifacts[str(path.relative_to(root))]=sha(path)
            elif row.get('execution_attempted'):
                issues.append(f'{label}: missing captured artifact {path.name}')
        matches = []
        if not native and log.exists():
            contents = log.read_text(errors='replace')
            matches = re.findall(r'^FORMULA '+re.escape(query['property_id'])+r' (TRUE|FALSE)(?:\s|$)', contents, re.M)
            if definitive:
                check(set(matches)=={'TRUE' if expected_truth else 'FALSE'},
                      f'{label}: definitive external formula output differs')
            if method=='smpt-full-portable':
                formula = next((line for line in contents.splitlines() if line.startswith('FORMULA ')), None)
                check(row.get('formula_output')==formula, f'{label}: saved SMPT formula field differs')
                capabilities = sorted(set(line for line in contents.splitlines()
                    if re.search(r'command not found|No such file or directory|bad command line|error: 4ti2 failed',line)))
                check(row.get('capability_failures',[])==capabilities, f'{label}: saved capability failures differ')
                check(bool(row.get('subprocess_error'))==('Traceback (most recent call last):' in contents),
                      f'{label}: saved subprocess error differs')
            else:
                formula = [line for line in contents.splitlines() if line.startswith('FORMULA '+query['property_id']+' ')]
                check(row.get('formula_output',[])==formula, f'{label}: saved VerifyPN formula field differs')
        sidecar = Path(str(log)+'.systemd.json')
        if sidecar.exists():
            state = read(sidecar)
            check(state==res.get('systemd_properties'), f'{label}: systemd sidecar differs')
            check(state.get('Result')==res.get('systemd_result'), f'{label}: systemd result differs')
            check(res.get('memory_limit_exceeded') is (state.get('Result')=='oom-kill'), f'{label}: OOM flag differs')
            for key,field,scale in [('CPUUsageNSec','cpu_seconds',1e9),('MemoryPeak','peak_memory_bytes',1)]:
                value = state.get(key)
                expected_value = None if value in (None,'','[not set]','infinity','18446744073709551615') else int(value)/scale
                check(res.get(field)==expected_value, f'{label}: cgroup {field} differs')
            if state.get('Result') in ('timeout','oom-kill'):
                check(row.get('outer_timeout') is True, f'{label}: cgroup failure without outer timeout flag')
        perf_path = Path(str(log)+'.perf.csv')
        counters = res.get('perf_counters') or {}
        interrupted_perf = res.get('systemd_result') in ('timeout','oom-kill') and bool(res.get('perf_failure'))
        if perf_path.exists():
            artifacts[str(perf_path.relative_to(root))] = sha(perf_path)
            parsed, perf_problems = parse_perf(perf_path)
            if counters:
                check(not perf_problems and parsed==counters, f'{label}: raw perf sidecar differs from counters')
            elif interrupted_perf:
                warnings.append(f'{label}: interrupted perf export; partial raw counters retained but not imputed')
            elif row.get('execution_attempted'):
                check(False, f'{label}: missing counters without recorded interrupted perf export')
        elif interrupted_perf:
            warnings.append(f'{label}: missing perf file after recorded cgroup failure')
        elif row.get('execution_attempted'):
            check(False, f'{label}: missing perf sidecar')
        checks = {event:perf_status(res,event) for event in ['instructions:u','cycles:u','task-clock']}
        if any(v!='full-coverage' for v in checks.values()):
            warnings.append(f'{label}: perf coverage {checks}')
        if 'validation' in row:
            validation = row['validation'] or {}
            validation_log = Path(str(log)+'.validation.log')
            if validation_log.exists():
                artifacts[str(validation_log.relative_to(root))] = sha(validation_log)
            else:
                issues.append(f'{label}: missing validation worker log')
            for key, value in dict(seconds_limit=60,memory_limit_bytes=2048*1024**2,response_limit_bytes=64*1024**2,
                                   dag_check_max_work=200000000,included_in_solver_timing=False).items():
                check(validation.get(key)==value, f'{label}: validation setting differs: {key}')
            request_path, response_path = Path(str(log)+'.validation-request.json'), Path(str(log)+'.validation-response.json')
            request = read(request_path)
            check(request.get('query')==query, f'{label}: validation query differs')
            check(request.get('corpus')==REMOTE+plan['corpus'] and request.get('artifacts')==REMOTE+plan['output'],
                  f'{label}: validator corpus or artifacts path differs')
            for key, value in dict(memory_bytes=2048*1024**2,response_bytes=64*1024**2,dag_check_max_work=200000000,
                                   exit_code=row.get('exit_code'),outer_timeout=row.get('outer_timeout'),mode='rust-original-v1').items():
                check(request.get(key)==value, f'{label}: validator request differs: {key}')
            check(request.get('log')==REMOTE+plan['output']+'/'+log.name, f'{label}: validator answer path differs')
            if response_path.exists():
                response = read(response_path)
                check(bool(response), f'{label}: empty validator response')
                if validation.get('exit_code')==0 and not validation.get('outer_timeout'):
                    for key in ('verdict','branches','independent_checks'):
                        check(key in response, f'{label}: missing validator response field {key}')
                    for key,value in response.items():
                        check(row.get(key)==value, f'{label}: validator response differs: {key}')
            elif definitive or (validation.get('exit_code')==0 and not validation.get('outer_timeout')):
                issues.append(f'{label}: missing successful validator response')
            if definitive:
                check(validation.get('exit_code')==0 and not validation.get('outer_timeout') and
                      not (validation.get('resources') or {}).get('memory_limit_exceeded'), f'{label}: unsuccessful validation')
        if native and definitive:
            check('validation' in row, f'{label}: missing bounded validation')
            check(row.get('translation_check')=='independent-original-input-equals-all-canonical-branches', f'{label}: missing original input comparison')
            branches = row.get('branches',[])
            checked = lambda b,v: b.get('verdict')==v and b.get('independent_check','').startswith('python-')
            valid = (any(checked(b,'reachable') for b in branches) if row['verdict']=='reachable' else
                     len(branches)==len(query['branches']) and {b['branch'] for b in branches}==set(range(len(query['branches']))) and
                     all(checked(b,'unreachable') for b in branches))
            check(valid, f'{label}: unchecked native verdict/branch coverage')
            answer = read(log)
            check(answer.get('verdict')==row['verdict'] and answer.get('property_id')==query['property_id'] and
                  answer.get('property_kind')==query['kind'] and answer.get('branch_count')==len(query['branches']) and
                  answer.get('deadline_exceeded') is False, f'{label}: saved native answer inconsistent')
        row_audits.append(dict(query=name,method=method,repeat=repetition,perf=checks,
                               external_formula_matches=matches if not native else None,
                               cpu_seconds=res.get('cpu_seconds'),peak_memory_bytes=res.get('peak_memory_bytes'),
                               outer_timeout=row.get('outer_timeout'),memory_limit_exceeded=res.get('memory_limit_exceeded')))
    analysis = None
    try:
        analysis = analyze(manifest, plan, environment, rows)
        check(analysis['validity'] == 'complete_consistent_screen', 'Classification reports conflicts or invalid definitive answers')
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        issues.append(f'Complete difficulty analysis unavailable: {error}')
    failures = [r for r in rows if r.get('verdict') not in DEFINITIVE or r.get('capability_failures') or r.get('subprocess_error') or r.get('error')]
    # Retain identities of additional captured proof/error artifacts, including
    # artifacts belonging to failed or duplicated rows.
    if results.exists():
        for path in sorted(results.rglob('*')):
            if path.is_file():
                artifacts[str(path.relative_to(root))] = sha(path)
    return dict(status='passed' if not issues else 'failed', audit_issues=issues,warnings=warnings,
        properties=len(queries),rows=len(rows),expected_properties=plan['properties'],expected_rows=plan['expected_rows'],
        exact_ordered_branch_representatives=len(groups), expected_representatives=expected_representatives,
        duplicate_groups=[g for g in groups if len(g)>1],
        families={family:dict(properties=sum(q['family']==family for q in queries.values()),
                             representatives=sum(queries[g[0]]['family']==family for g in groups))
                  for family in sorted({q['family'] for q in queries.values()})},
        identities=identities,artifact_sha256=artifacts,classification=analysis,
        row_audits=row_audits,failures=failures,full_rows=rows,invalid_rows=invalid_rows,
        linux_host=environment.get('linux_host'),
        completion_scope='Requires independently confirmed terminal process before fetching. A complete matrix does not prove process termination; harness exit1 is not interpreted as a verdict.',
        validation_scope='Checks saved validator requests/responses, native answer consistency and independent-check labels; does not rerun proofs or witnesses. External answers remain tool-reported. Unfetched tool identities are environment-reported only. Systemd sidecars contain accounting, not independent proof of configured limits; those rely on frozen runner bytes and recorded settings.',
        caveat='Development difficulty screen; one repetition with full planned and imported denominators reported separately. CPU affinity is not exclusive isolation. Instruction counts do not remove timeout censorship or contention. Failures and missing counters retained; no stable timing or superiority claim.')


def safe_audit(root, plan_path, results):
    try:
        return audit(root,plan_path,results)
    except Exception as error:
        retained=[]
        try:
            for line in (results/'runs.jsonl').read_text().splitlines():
                try: retained.append(json.loads(line))
                except ValueError: retained.append(dict(unparsed_line=line))
        except OSError: pass
        try:
            plan = json.loads(plan_path.read_text())
        except (OSError, ValueError):
            plan = {}
        return dict(status='failed',audit_issues=[f'Audit could not finish: {type(error).__name__}: {error}'],
                    full_rows=retained,rows=len(retained),expected_rows=plan.get('expected_rows'),expected_properties=plan.get('properties'),expected_representatives=plan.get('exact_ordered_branch_representatives'),
                    validation_scope='Audit aborted; no validity or coverage conclusion. Original rows retained.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'research/application-expansion-v1-screen-plan.json')
    parser.add_argument('--results',type=Path,default=ROOT/'results/linux-application-expansion-v1')
    parser.add_argument('--output',type=Path,default=ROOT/'research/linux-application-expansion-v1-verification.json')
    args=parser.parse_args()
    report=safe_audit(ROOT,args.plan.resolve(),args.results.resolve())
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    md=args.output.with_suffix('.md')
    lines=[f"# Linux application artifact audit: {report['status']}", '',
           f"Rows: {report.get('rows',0)}/{report.get('expected_rows')}; queries: {report.get('properties',0)}/{report.get('expected_properties')}; exact ordered-branch representatives: {report.get('exact_ordered_branch_representatives',0)}.", '']
    if report.get('classification'):
        lines += [json.dumps(report['classification']['full'],indent=2), '',report['validation_scope'],'',report['caveat'],'']
    lines += ['Audit issues:'] + [f'- {x}' for x in report['audit_issues']] if report['audit_issues'] else ['No audit issues.']
    lines += ['',f"Warnings: {len(report.get('warnings',[]))}; all rows, failures, resource sidecars and identities are retained in `{args.output.name}`."]
    md.write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=report['status'],issues=len(report['audit_issues']),json=str(args.output),markdown=str(md))))
    return int(report['status']!='passed')


if __name__=='__main__':
    sys.exit(main())
