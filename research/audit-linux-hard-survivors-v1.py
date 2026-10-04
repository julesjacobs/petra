#!/usr/bin/env python3
"""Audit fetched hard-survivors results locally; never run a solver or contact Linux.

Default outputs: research/linux-hard-survivors-v1-verification.{json,md}.
Exit 0 means the recorded artifacts pass this consistency audit; exit 1 retains
an incomplete/failed report. This does not rerun independent proof checkers.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import posixpath
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
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


def audit(root, plan_path, results):
    issues, warnings, identities, artifacts = [], [], [], {}

    def check(condition, message):
        if not condition:
            issues.append(message)
        return condition

    def read(path):
        try:
            data = json.loads(path.read_text())
            artifacts[str(path.relative_to(root))] = sha(path)
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
    except OSError as error:
        issues.append(str(error))
    methods = list(plan['methods'])
    artifacts[str(Path(__file__).resolve().relative_to(root))] = sha(Path(__file__).resolve())
    queries = {q['name']: q for q in manifest.get('queries', [])}
    check(len(queries) == plan['properties'] == 8, 'Expected eight distinct queries')
    expected = {(q, m, i) for q in queries for m in methods for i in range(plan['repeat'])}
    counts = Counter((r.get('query'), r.get('method'), r.get('repeat')) for r in rows)
    check(len(rows) == plan['expected_rows'] == 32, 'Expected 32 rows')
    check(set(counts) == expected and all(v == 1 for v in counts.values()),
          'Incomplete, duplicated or unexpected query/method/repeat matrix')
    check(set(environment.get('methods', [])) == set(methods), 'Environment methods differ')
    order = environment.get('property_order', [])
    check(len(order) == len(queries) and set(order) == set(queries), 'Property order does not cover all queries once')
    for key in ['seconds', 'repeat', 'max_states', 'memory_mib', 'outer_grace', 'order_seed', 'linux_cpus', 'perf']:
        check(environment.get(key) == plan[key], f'Environment setting differs: {key}')
    check(environment.get('queries') == 8, 'Environment query count differs')
    check(environment.get('manifest_sha256') == plan['manifest_sha256'], 'Recorded manifest identity differs')
    check(environment.get('binary_sha256') == plan['native_binary_sha256'], 'Recorded native binary identity differs')
    validation_plan = plan['validation']
    limits = dict(enabled=True, seconds=validation_plan['seconds'], memory_mib=validation_plan['memory_mib'],
                  response_mib=validation_plan['response_mib'], dag_check_max_work=validation_plan['dag_check_max_work'],
                  included_in_solver_timing=False)
    check(environment.get('bounded_validation') == limits, 'Uniform validation limits differ')
    selection = read(root/plan['selection_audit'])
    check(selection.get('full_properties') == 69 and selection.get('parent_properties') == 620,
          'Selection denominators differ from 69/620')
    check(set(q['query'] for q in selection.get('decisions', []) if q['selected']) == set(queries),
          'Run corpus differs from complete survivor selection')
    check(manifest.get('source_evidence', {}).get('full_denominator') == 69 and
          manifest.get('source_evidence', {}).get('parent_denominator') == 620, 'Manifest denominators differ')
    for path, digest in plan['selection_evidence'].items():
        identity(root/path, digest, 'local selection evidence bytes')

    # Current local scripts may have evolved: use the fetched runner snapshot.
    recorded = {}
    for name, digest in environment.get('script_sha256', {}).items():
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
            if path == plan['native_binary']:
                check(recorded.get(path) == expected_hash, 'Native tool map identity differs')
    check(environment.get('smpt_configurations') == plan['smpt_configurations'], 'SMPT configuration differs')
    for key in ['binary_sha256', 'source_commit', 'source_status', 'configurations']:
        check(environment.get('verifypn', {}).get(key) == plan['verifypn'][key], f'VerifyPN configuration differs: {key}')
    for method in ['native-focused', 'native-symbolic']:
        tool = environment.get('native_tools', {}).get(method, {})
        check(tool.get('engine') == plan['methods'][method], f'Native method mapping differs: {method}')

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
        check(row.get('verdict') in DEFINITIVE | {'unknown','error'}, f'{label}: invalid verdict')
        check(row.get('property_kind') == query['kind'], f'{label}: property kind differs')
        expected_truth = (row['verdict']=='reachable') == (query['kind']=='EF') if definitive else None
        check(row.get('property_truth') is expected_truth, f'{label}: property truth differs')
        check(row.get('suite') == query['suite'], f'{label}: suite differs')
        mode = 'rust-original-v1' if native else 'verifypn-original' if method=='verifypn-default' else 'smpt-original'
        check(row.get('input_mode') == mode, f'{label}: input mode differs')
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
                check(relative(command[0])==plan['native_binary'], f'{label}: native binary path differs')
                check(option('--method')==plan['methods'][method], f'{label}: engine differs')
                check(float(option('--seconds'))==plan['seconds'], f'{label}: solver seconds differ')
                check(int(option('--max-states'))==plan['max_states'], f'{label}: state cap differs')
                check(option('--property-id')==query['property_id'], f'{label}: property ID differs')
            elif method=='smpt-full-portable':
                check(float(option('--timeout'))==plan['seconds'], f'{label}: SMPT timeout differs')
                check(row.get('enabled_methods')==plan['smpt_configurations'][method], f'{label}: enabled SMPT modes differ')
                check('--auto-reduce' in command, f'{label}: SMPT reduction missing')
                check(relative(command[0])=='vendor/venv/bin/python' and command[1:3]==['-m','smpt'], f'{label}: SMPT entrypoint differs')
            else:
                check(relative(command[0])==relative(plan['verifypn']['binary']) and command[1:3]==['-x','1'] and len(command)==5,
                      f'{label}: VerifyPN command differs')
        except (ValueError, TypeError, IndexError) as error:
            issues.append(f'{label}: malformed command: {error}')
        suffix = '.rust-original.json' if native else '.log'
        log = results/f'{name}.{method}.{repetition}{suffix}'
        for path in [log, Path(str(log)+'.systemd.json'), Path(str(log)+'.perf.csv')]:
            if path.exists():
                artifacts[str(path.relative_to(root))]=sha(path)
            elif row.get('execution_attempted'):
                issues.append(f'{label}: missing captured artifact {path.name}')
        if not native and definitive and log.exists():
            matches = re.findall(r'^FORMULA '+re.escape(query['property_id'])+r' (TRUE|FALSE)(?:\s|$)',
                                 log.read_text(errors='replace'), re.M)
            check(set(matches)=={'TRUE' if expected_truth else 'FALSE'},
                  f'{label}: definitive external formula output differs')
        sidecar = Path(str(log)+'.systemd.json')
        if sidecar.exists():
            check(read(sidecar)==res.get('systemd_properties'), f'{label}: systemd sidecar differs')
        checks = {event:perf_status(res,event) for event in ['instructions:u','cycles:u','task-clock']}
        if any(v!='full-coverage' for v in checks.values()):
            warnings.append(f'{label}: perf coverage {checks}')
        if 'validation' in row:
            validation = row['validation']
            for key, value in dict(seconds_limit=60,memory_limit_bytes=2048*1024**2,response_limit_bytes=64*1024**2,
                                   dag_check_max_work=200000000,included_in_solver_timing=False).items():
                check(validation.get(key)==value, f'{label}: validation setting differs: {key}')
            request_path, response_path = Path(str(log)+'.validation-request.json'), Path(str(log)+'.validation-response.json')
            request = read(request_path)
            check(request.get('query')==query, f'{label}: validation query differs')
            for key, value in dict(memory_bytes=2048*1024**2,response_bytes=64*1024**2,dag_check_max_work=200000000,
                                   exit_code=row.get('exit_code'),outer_timeout=row.get('outer_timeout'),mode='rust-original-v1').items():
                check(request.get(key)==value, f'{label}: validator request differs: {key}')
            if request.get('log'):
                check(relative(request['log'])==str(log.relative_to(root)), f'{label}: validator answer path differs')
            if response_path.exists():
                response = read(response_path)
                if validation.get('exit_code')==0 and not validation.get('outer_timeout'):
                    for key,value in response.items():
                        check(row.get(key)==value, f'{label}: validator response differs: {key}')
            elif definitive:
                issues.append(f'{label}: missing definitive validator response')
            if definitive:
                check(validation.get('exit_code')==0 and not validation.get('outer_timeout') and
                      not validation.get('resources',{}).get('memory_limit_exceeded'), f'{label}: unsuccessful validation')
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
                               cpu_seconds=res.get('cpu_seconds'),peak_memory_bytes=res.get('peak_memory_bytes'),
                               outer_timeout=row.get('outer_timeout'),memory_limit_exceeded=res.get('memory_limit_exceeded')))
    solved = {m:{r['query'] for r in rows if r.get('method')==m and r.get('verdict') in DEFINITIVE} for m in methods}
    for name in queries:
        answers={r.get('verdict') for r in rows if r.get('query')==name} & DEFINITIVE
        check(len(answers)<=1, f'Definitive disagreement: {name}')
    failures=[r for r in rows if r.get('verdict') not in DEFINITIVE or r.get('capability_failures') or r.get('subprocess_error')]
    return dict(status='passed' if not issues else 'failed',audit_issues=issues,warnings=warnings,
        properties=len(queries),rows=len(rows),expected_properties=8,expected_rows=32,
        previous_denominator=69,parent_denominator=620,identities=identities,artifact_sha256=artifacts,
        counts={m:dict(Counter(r.get('verdict') for r in rows if r.get('method')==m)) for m in methods},
        solved={m:len(v) for m,v in solved.items()},union_solved=len(set().union(*solved.values())),
        jointly_unresolved=sorted(set(queries)-set().union(*solved.values())),
        suites={s:dict(properties=sum(q['suite']==s for q in queries.values()),solved={m:sum(queries[n]['suite']==s for n in v if n in queries) for m,v in solved.items()}) for s in sorted({q['suite'] for q in queries.values()})},
        resources={m:dict(outer_timeout_flags=sum(bool(r.get('outer_timeout')) for r in rows if r.get('method')==m),
                         memory_limit_flags=sum(bool((r.get('resources') or {}).get('memory_limit_exceeded')) for r in rows if r.get('method')==m),
                         perf={e:dict(Counter(r['perf'][e] for r in row_audits if r['method']==m)) for e in ['instructions:u','cycles:u','task-clock']}) for m in methods},
        row_audits=row_audits,failures=failures,full_rows=rows,linux_host=environment.get('linux_host'),
        completion_scope='Requires independently confirmed terminal process before fetching. A complete matrix does not prove process termination; harness exit1 is not interpreted as a verdict. Error rows stay in full_rows/failures and never count as solved.',
        validation_scope='Checks recorded bounded-validator request/response/answer consistency and independent-check labels; does not rerun proofs or witnesses. External answers remain tool-reported. Tool binaries not copied locally are checked against environment-recorded hashes only.',
        caveat='Outcome-selected development qualification, one repetition, 8/69/620 provenance retained. CPU8 affinity is not exclusive isolation; instruction counts do not remove deadline censorship or contention. Missing counters and failures are retained. No precise speedup claim.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=ROOT/'results/linux-hard-survivors-v1')
    parser.add_argument('--output',type=Path,default=ROOT/'research/linux-hard-survivors-v1-verification.json')
    args=parser.parse_args()
    try:
        report=audit(ROOT,ROOT/'research/hard-survivors-v1-plan.json',args.results.resolve())
    except Exception as error:
        retained=[]
        try:
            for line in (args.results/'runs.jsonl').read_text().splitlines():
                try:
                    retained.append(json.loads(line))
                except ValueError:
                    retained.append(dict(unparsed_line=line))
        except OSError:
            pass
        report=dict(status='failed',audit_issues=[f'Audit could not finish: {type(error).__name__}: {error}'],
                    full_rows=retained,rows=len(retained),expected_rows=32,expected_properties=8,
                    previous_denominator=69,parent_denominator=620,
                    validation_scope='Audit aborted; no validity or coverage conclusion. Original rows retained.')
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    md=args.output.with_suffix('.md')
    lines=[f"# Linux hard-survivors-v1 audit: {report['status']}",'',
           f"Rows: {report.get('rows',0)}/32; queries: {report.get('properties',0)}/8; provenance: 69 previous / 620 parent queries.",'']
    if 'solved' in report:
        lines += [f"- {m}: {n}/8 recorded definitive answers." for m,n in report['solved'].items()]
        lines += ['',f"Union: {report['union_solved']}/8. Remaining: {', '.join(report['jointly_unresolved']) or 'none'}.",'',report['validation_scope'],'',report['caveat'],'']
    lines += ['Audit issues:'] + [f'- {x}' for x in report['audit_issues']] if report['audit_issues'] else ['No audit issues.']
    lines += ['',f"Warnings: {len(report.get('warnings',[]))}; full rows, failures, resource/perf coverage and identity evidence are retained in `{args.output.name}`."]
    md.write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=report['status'],issues=len(report['audit_issues']),json=str(args.output),markdown=str(md))))
    return int(report['status']!='passed')


if __name__=='__main__':
    sys.exit(main())
