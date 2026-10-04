#!/usr/bin/env python3
"""Sequential, whole-property benchmarks for the published SMPT suites."""
import argparse
import collections
import hashlib
import json
import math
import os
import pathlib
import platform
import re
import random
import sys
import shutil
import subprocess

from benchmark import run, verify, DEFAULT_DAG_CHECK_WORK
from bounded_validation import InputChecks
from verifypn_runner import MODES as VERIFYPN_MODES
from its_runner import MODES as ITS_MODES
from external_verdict import admit

ROOT = pathlib.Path(__file__).resolve().parents[1]
SMPT_MODES = {
    'smpt-full': ['WALK', 'STATE-EQUATION', 'BMC', 'INDUCTION', 'K-INDUCTION',
                  'PDR-COV', 'PDR-REACH', 'PDR-REACH-SATURATED', 'SMT', 'CP'],
    'smpt-full-unsaturated': ['WALK', 'STATE-EQUATION', 'BMC', 'INDUCTION',
                             'K-INDUCTION', 'PDR-COV', 'PDR-REACH', 'SMT', 'CP'],
    'smpt': ['STATE-EQUATION', 'BMC'],
    'smpt-state-equation': ['STATE-EQUATION'],
    'smpt-bmc': ['BMC'],
    'smpt-induction': ['INDUCTION'],
    'smpt-k-induction': ['K-INDUCTION'],
    'smpt-pdr-cov': ['PDR-COV'],
    'smpt-pdr-reach': ['PDR-REACH'],
    'smpt-pdr-saturated': ['PDR-REACH-SATURATED'],
    'smpt-portfolio': ['STATE-EQUATION', 'BMC', 'INDUCTION', 'K-INDUCTION',
                       'PDR-COV', 'PDR-REACH', 'PDR-REACH-SATURATED'],
    'smpt-portfolio-unsaturated': ['STATE-EQUATION', 'BMC', 'INDUCTION',
                                   'K-INDUCTION', 'PDR-COV', 'PDR-REACH'],
}
SMPT_MODES['smpt-full-portable'] = SMPT_MODES['smpt-full']
SMPT_MODES['smpt-full-portable-unsaturated'] = SMPT_MODES['smpt-full-unsaturated']


SMPT_SINGLE_CORE_MODES = {
    'smpt-compact-portable': ['WALK', 'STATE-EQUATION', 'BMC', 'K-INDUCTION', 'SMT'],
    'smpt-pdr-reach-portable': ['PDR-REACH', 'SMT'],
    'smpt-pdr-saturated-portable': ['PDR-REACH-SATURATED', 'SMT'],
    'smpt-mcc-portable': SMPT_MODES['smpt-full'],
}
SMPT_MODES.update(SMPT_SINGLE_CORE_MODES)


def smpt_scheduling(method):
    return dict(requested_methods=SMPT_MODES[method], effective_workers=None,
                requested_methods_control_workers=method != 'smpt-mcc-portable',
                scheduling_policy=('official-mcc' if method == 'smpt-mcc-portable'
                                   else 'requested-method-portfolio'),
                effective_workers_note=('Official MCC chooses workers; --methods satisfies the required CLI group and is ignored for scheduling.'
                                        if method == 'smpt-mcc-portable' else
                                        'Chosen dynamically by SMPT; requested methods are not worker counts or execution order.'))


def execute(command, cwd, seconds, output, args):
    if getattr(args, 'linux_cpus', None):
        from linux_runner import run as linux_run
        from process_runner import workspace_workloads
        conflicts = workspace_workloads(getattr(args, 'workspace_root', ROOT))
        if conflicts:
            raise RuntimeError(f'Overlapping workspace workloads invalidate timing: {conflicts}')
        return linux_run(command, cwd, seconds, output,
                         None if args.memory_mib is None else args.memory_mib * 1024**2,
                         cpus=args.linux_cpus, perf=args.perf)
    if args.track_resources:
        from process_runner import run as tracked_run, workspace_workloads
        conflicts = workspace_workloads(getattr(args, 'workspace_root', ROOT))
        if conflicts:
            raise RuntimeError(f'Overlapping workspace workloads invalidate timing: {conflicts}')
        return tracked_run(command, cwd, seconds, output,
                           None if args.memory_mib is None else args.memory_mib * 1024**2)
    elapsed, code, expired = run(command, cwd, seconds, output)
    return elapsed, code, expired, {}


def aggregate(verdicts):
    if 'error' in verdicts:
        return 'error'
    if 'reachable' in verdicts:
        return 'reachable'
    if all(v == 'unreachable' for v in verdicts):
        return 'unreachable'
    return 'unknown'


def property_truth(kind, verdict):
    if verdict not in ('reachable', 'unreachable'):
        return None
    return (verdict == 'reachable') == (kind == 'EF')


def checked(path, digest):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'Input checksum mismatch: {path}')
    return data


def native_tool(method, args):
    configured = getattr(args, 'native_tools', {}).get(method)
    if configured:
        return pathlib.Path(configured['binary']), configured['engine']
    return (args.baseline_binary, 'portfolio-v2') if method == 'frozen-v2' else (args.binary, method)


def uses_rust_original(method, args):
    return (getattr(args, 'rust_original', False)
            or method in getattr(args, 'rust_original_method', []))


def configure_original_modes(args):
    if args.rust_original and args.native_original:
        raise ValueError('--rust-original and --native-original are distinct input modes')
    for method in args.rust_original_method:
        if method not in args.methods or method in SMPT_MODES or method in VERIFYPN_MODES or method in ITS_MODES:
            raise ValueError(f'--rust-original-method requires a selected native method: {method}')
    if args.rust_original or args.rust_original_method:
        args.bounded_validation = True
    if args.bounded_validation and not (args.native_original or args.rust_original or args.rust_original_method):
        raise ValueError('--bounded-validation requires an original-input native mode')
    for option in ('target_zero_trap', 'target_path_potential', 'buffer_agglomeration', 'geometric_branches'):
        for method in getattr(args, option + '_method', []):
            flag = '--' + option.replace('_', '-') + '-method'
            if method not in args.methods or method in SMPT_MODES or method in VERIFYPN_MODES or method in ITS_MODES:
                raise ValueError(f'{flag} requires a selected native method')
            if not (args.rust_original or method in args.rust_original_method):
                raise ValueError(f'{flag} requires Rust original-input mode')


def method_input_mode(method, args):
    if method in ITS_MODES:
        return 'its-original'
    if method in VERIFYPN_MODES:
        return 'verifypn-original'
    if method in SMPT_MODES:
        return 'smpt-original' if args.smpt_original else 'smpt-translated'
    if uses_rust_original(method, args):
        return 'rust-original-v1'
    return 'python-original-v1' if args.native_original else 'canonical-json'


INPUT_SCOPES = {
    'its-original': 'Original PNML/XML; Python wrapper startup, single-property staging, configured runtime/native startup, preprocessing and ITS solving within the same strict whole-property deadline. External verdicts are not independently proof checked.',
    'rust-original-v1': 'Original PNML/XML; Rust startup, parsing, target DNF and in-process branch solving inside one strict whole-property deadline. Bounded independent Python original-input translation, canonical comparison and witness/proof checking outside timing.',
    'python-original-v1': 'Original PNML/XML; Python startup, parsing, target DNF, branch serialization, Rust startup and solving inside one process-tree deadline. Canonical translation comparison and witness/proof checking outside timing.',
    'canonical-json': 'Pretranslated canonical JSON; original-input translation excluded from timing.',
    'verifypn-original': 'Original PNML/XML; common preflight verifies each XML contains only the requested property, selected by constant -x 1. VerifyPN startup, parsing, preprocessing and solving inside the timed process.',
    'smpt-original': 'Original PNML/XML; SMPT startup, parsing, configured reduction and solving inside the timed process.',
    'smpt-translated': 'Pretranslated Tina net and property XML; original-input translation excluded from timing.',
}


def native(query, corpus, output, method, repeat, args):
    if uses_rust_original(method, args):
        return rust_original(query, corpus, output, method, repeat, args)
    if args.native_original:
        return native_original(query, corpus, output, method, repeat, args)
    verdicts, checks, branches = [], [], []
    wall = 0.0
    for i, branch in enumerate(query['branches']):
        if 'reachable' in verdicts or wall >= args.seconds:
            if 'reachable' not in verdicts:
                verdicts.append('unknown')
            break
        path = corpus/branch['path']
        problem = json.loads(checked(path, branch['sha256']))
        budget = (args.seconds-wall)/(len(query['branches'])-i)
        log = output/f'{query["name"]}.{method}.{repeat}.branch-{i}.json'
        binary, engine = native_tool(method, args)
        command = [str(binary), '--json', str(path), '--method', engine,
                   '--seconds', str(budget), '--max-states', str(args.max_states)]
        grace = 0.5 if args.outer_grace is None else args.outer_grace
        elapsed, code, expired, usage = execute(command, ROOT, budget+grace, log, args)
        wall += elapsed
        result = dict(branch=i, wall_seconds=elapsed, exit_code=code, outer_timeout=expired, resources=usage)
        verdict = 'unknown'
        if not expired:
            try:
                if code != 0:
                    raise ValueError(f'Solver exit code {code}')
                answer = json.loads(log.read_text())
                verdict = answer['verdict']
                if verdict not in ('reachable', 'unreachable', 'unknown'):
                    raise ValueError(f'Invalid verdict {verdict}')
                check = verify(problem, answer, dag_max_work=getattr(args, 'validation_dag_work', DEFAULT_DAG_CHECK_WORK))
                checks.append(check)
                result.update(independent_check=check, engine=answer['method'])
            except TimeoutError as error:
                verdict = 'unknown'
                result.update(validation_failure='checker-resource-limit', validation_reason=str(error),
                              failure_stage='validation')
            except Exception as error:
                verdict = 'error'
                result['error'] = repr(error)
        verdicts.append(verdict)
        branches.append(dict(result, verdict=verdict))
    return dict(verdict=aggregate(verdicts), wall_seconds=wall, branches=branches,
                independent_checks=checks)


def rust_original(query, corpus, output, method, repeat, args):
    from bounded_validation import run_validation
    binary, engine = native_tool(method, args)
    log = output/f'{query["name"]}.{method}.{repeat}.rust-original.json'
    command = [str(binary), '--pnml', str(corpus/query['pnml']), '--xml', str(corpus/query['xml']),
               '--property-id', query['property_id'], '--method', engine,
               '--seconds', str(args.seconds), '--max-states', str(args.max_states)]
    if method in getattr(args, 'target_zero_trap_method', []):
        command.append('--target-zero-trap')
    if method in getattr(args, 'target_path_potential_method', []):
        command.append('--target-path-potential')
    if method in getattr(args, 'buffer_agglomeration_method', []):
        command.append('--buffer-agglomeration')
    if method in getattr(args, 'geometric_branches_method', []):
        command.append('--geometric-branches')
    grace = 0 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, ROOT, args.seconds+grace, log, args)
    expired = expired or wall > args.seconds
    result = dict(verdict='unknown', property_truth=None, wall_seconds=wall, exit_code=code,
                  outer_timeout=expired, resources=usage, command=command,
                  input_mode='rust-original-v1', independent_checks=[], branches=[])
    if expired or code != 0:
        return result
    result.update(run_validation(query, corpus, output, log, code, args,
                                 mode='rust-original-v1', outer_timeout=expired))
    return result


def native_original(query, corpus, output, method, repeat, args):
    artifacts = output/f'{query["name"]}.{method}.{repeat}.original'
    log = output/f'{query["name"]}.{method}.{repeat}.frontend.json'
    binary, engine = native_tool(method, args)
    command = [str(args.native_python), str(ROOT/'scripts/native_original.py'),
               '--pnml', str(corpus/query['pnml']), '--xml', str(corpus/query['xml']),
               '--property-id', query['property_id'], '--binary', str(binary),
               '--method', engine, '--seconds', str(args.seconds),
               '--max-states', str(args.max_states), '--artifacts', str(artifacts)]
    grace = 0.5 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, ROOT, args.seconds+grace, log, args)
    result = dict(verdict='unknown', wall_seconds=wall, exit_code=code,
                  outer_timeout=expired, resources=usage, command=command,
                  artifacts=str(artifacts), independent_checks=[], branches=[])
    if expired:
        return result
    if getattr(args, 'bounded_validation', False):
        from bounded_validation import run_validation
        result.update(run_validation(query, corpus, artifacts, log, code, args))
        return result
    try:
        if code != 0:
            raise ValueError(f'Frontend exit code {code}: {log.read_text()}')
        summary = json.loads(log.read_text())
        expected = dict(property_id=query['property_id'], kind=query['kind'],
                        branch_count=len(query['branches']))
        if any(summary.get(k) != v for k, v in expected.items()):
            raise ValueError('Frontend property identity, polarity or branch count mismatch')
        if json.loads((artifacts/'translation.json').read_text()) != expected:
            raise ValueError('Frontend translation metadata mismatch')
        problems = []
        for i, branch in enumerate(query['branches']):
            problem = json.loads(checked(corpus/branch['path'], branch['sha256']))
            if json.loads((artifacts/f'branch-{i}.json').read_text()) != problem:
                raise ValueError(f'Original-input translation disagrees with canonical branch {i}')
            problems.append(problem)
        attempts = summary['attempts']
        if len(attempts) > len(problems) or [a['branch'] for a in attempts] != list(range(len(attempts))):
            raise ValueError('Invalid attempted branch sequence')
        verdicts = []
        for attempt in attempts:
            i = attempt['branch']
            branch_result = dict(attempt, verdict='unknown')
            if not attempt['outer_timeout']:
                if attempt['exit_code'] != 0:
                    raise ValueError(f'Branch {i} exit code {attempt["exit_code"]}')
                answer = json.loads((artifacts/f'answer-{i}.json').read_text())
                verdict = answer['verdict']
                if verdict not in ('reachable', 'unreachable', 'unknown'):
                    raise ValueError(f'Invalid verdict {verdict}')
                check = verify(problems[i], answer, dag_max_work=getattr(args, 'validation_dag_work', DEFAULT_DAG_CHECK_WORK))
                branch_result.update(independent_check=check, engine=answer['method'])
                result['independent_checks'].append(check)
                if verdict != 'unknown' and not check.startswith('python-'):
                    branch_result['unchecked_verdict'] = verdict
                    verdict = 'unknown'
                branch_result['verdict'] = verdict
            verdicts.append(branch_result['verdict'])
            result['branches'].append(branch_result)
        if len(attempts) < len(problems):
            verdicts.append('unknown')
        result['verdict'] = aggregate(verdicts)
        result['translation_check'] = 'all-canonical-branches-equal'
    except TimeoutError as error:
        result.update(verdict='unknown', validation_failure='checker-resource-limit',
                      validation_reason=str(error), failure_stage='validation')
    except Exception as error:
        result.update(verdict='error', error=repr(error))
    return result


def smpt(query, corpus, output, method, repeat, args):
    log = output/f'{query["name"]}.{method}.{repeat}.log'
    net_key, property_key = ('pnml', 'xml') if args.smpt_original else ('net', 'property')
    method_options = ['--methods', *SMPT_MODES[method]]
    if method == 'smpt-mcc-portable':
        method_options.append('--mcc')
    command = [str(args.smpt_python), '-m', 'smpt',
               '-n', str(corpus/query[net_key]), '--xml', str(corpus/query[property_key]),
               *method_options, '--timeout', str(math.ceil(args.seconds)),
               '--show-time', '--show-techniques', '--show-model', '--export-proof', str(log.with_suffix('.proof'))]
    if args.auto_reduce or method.startswith('smpt-full') or method in SMPT_SINGLE_CORE_MODES:
        command.append('--auto-reduce')
    grace = 1 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, args.smpt_root, args.seconds+grace, log, args)
    if method in SMPT_SINGLE_CORE_MODES:
        expired = expired or wall > args.seconds
    contents = log.read_text()
    from external_verdict import parse
    parsed = parse(contents, query['property_id'], query['kind'], code, expired,
                   wall=wall, seconds=args.seconds)
    return dict(**parsed, wall_seconds=wall, exit_code=code,
                resources=usage, command=command,
                outer_timeout=expired or wall > args.seconds,
                **(smpt_scheduling(method) if method in SMPT_SINGLE_CORE_MODES
                   else dict(enabled_methods=SMPT_MODES[method])),
                independent_checks=['none-external-smpt'])


def import_failure(query):
    return dict(verdict='unsupported', error=query.get('error'), execution_attempted=False,
                failure_stage='collection', collection_status=query.get('status'),
                collection_observed=query.get('observed'), property_slot=query.get('property_slot'),
                resources=None, independent_checks=[], branches=[])


def preflight_inputs(queries, corpus, original):
    inputs = InputChecks()
    for query in queries:
        if query['status'] != 'imported':
            continue
        for key in ('net', 'property', *(['pnml', 'xml'] if original else [])):
            inputs.check(corpus/query[key], query[key+'_sha256'])
        if original:
            from verifypn_runner import check_single_property
            check_single_property(corpus/query['xml'], query['property_id'])
        for branch in query['branches']:
            inputs.check(corpus/branch['path'], branch['sha256'])
    return inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', type=pathlib.Path, default=ROOT,
                        help='Workload conflict scope; helper imports and snapshots retain their source root')
    parser.add_argument('--corpus', type=pathlib.Path, default=ROOT/'benchmarks/smpt-classic')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'results/smpt-classic')
    parser.add_argument('--binary', type=pathlib.Path, default=ROOT/'target/release/vass-reach')
    parser.add_argument('--baseline-binary', type=pathlib.Path, default=ROOT/'results/solver-v2/vass-reach')
    parser.add_argument('--native-tool', nargs=3, action='append', default=[], metavar=('LABEL', 'ENGINE', 'BINARY'), help='Name a frozen native engine/binary for paired candidate comparisons')
    parser.add_argument('--verifypn-binary', type=pathlib.Path, default=ROOT/'vendor/verifypn/build-release/verifypn/bin/verifypn')
    parser.add_argument('--verifypn-root', type=pathlib.Path, default=ROOT/'vendor/verifypn')
    parser.add_argument('--its-runtime-config', type=pathlib.Path, help='Pinned ITS runtime/Java/tool configuration JSON')
    parser.add_argument('--methods', nargs='+', default=['portfolio-v2', 'smpt-portfolio-unsaturated'])
    parser.add_argument('--seconds', type=float, default=2)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--max-states', type=int, default=200000)
    parser.add_argument('--filter', default='')
    parser.add_argument('--order-seed', type=int, help='Shuffle properties reproducibly and rotate method order across properties')
    parser.add_argument('--smpt-root', type=pathlib.Path, default=ROOT/'vendor/SMPT')
    parser.add_argument('--smpt-python', type=pathlib.Path, default=ROOT/'vendor/venv/bin/python')
    parser.add_argument('--tool-bin', type=pathlib.Path, action='append', default=[])
    parser.add_argument('--auto-reduce', action='store_true')
    parser.add_argument('--track-resources', action='store_true', help='Sample process trees; requires psutil')
    parser.add_argument('--linux-cpus', nargs='+', type=int, help='Linux systemd cgroup runner with fixed CPU affinity')
    parser.add_argument('--perf', action='store_true', help='Require user-space instruction/cycle counters; needs --linux-cpus')
    parser.add_argument('--smpt-original', action='store_true', help='Give SMPT original PNML/XML including NUPN annotations')
    parser.add_argument('--native-original', action='store_true', help='Time Python PNML/XML translation and all Rust branches within one outer invocation')
    parser.add_argument('--rust-original', action='store_true', help='Opt-in Rust PNML/XML parsing and in-process branch scheduling; bounded independent validation is mandatory')
    parser.add_argument('--rust-original-method', action='append', default=[], metavar='LABEL', help='Use the Rust original-input frontend only for this selected native method; repeat for multiple labels; other methods retain the chosen default input mode')
    parser.add_argument('--target-zero-trap-method', action='append', default=[], metavar='LABEL', help='Enable target-zero trap preprocessing for this Rust original-input method')
    parser.add_argument('--geometric-branches-method', action='append', default=[], metavar='LABEL', help='Enable geometric branch revisits for this Rust original-input method')
    parser.add_argument('--buffer-agglomeration-method', action='append', default=[], metavar='LABEL', help='Enable checked buffer agglomeration for this Rust original-input method')
    parser.add_argument('--target-path-potential-method', action='append', default=[], metavar='LABEL', help='Enable checked target-path slack for this Rust original-input method')
    parser.add_argument('--native-python', type=pathlib.Path, default=pathlib.Path(sys.executable), help='Python frontend executable for --native-original')
    parser.add_argument('--bounded-validation', action='store_true', help='Check original native answers in a separately bounded child')
    parser.add_argument('--validation-seconds', type=float, default=30)
    parser.add_argument('--validation-memory-mib', type=int, default=2048)
    parser.add_argument('--validation-response-mib', type=int, default=1)
    parser.add_argument('--validation-dag-work', type=int, default=DEFAULT_DAG_CHECK_WORK,
                        help='Independent DAG CNF/RUP checker work limit per proof')
    parser.add_argument('--outer-grace', type=float, help='Common additional wall allowance; zero gives a strict outer deadline')
    parser.add_argument('--memory-mib', type=int, help='Sampled aggregate RSS limit; requires --track-resources')
    args = parser.parse_args()
    args.workspace_root = args.workspace_root.resolve()
    try:
        configure_original_modes(args)
    except ValueError as error:
        parser.error(str(error))
    if (not math.isfinite(args.validation_seconds) or args.validation_seconds <= 0
            or min(args.validation_memory_mib, args.validation_response_mib, args.validation_dag_work) <= 0):
        parser.error('Validation limits must be positive and finite')
    args.native_tools = {}
    for label, engine, binary in args.native_tool:
        if label in args.native_tools or label in SMPT_MODES or label in VERIFYPN_MODES or label in ITS_MODES:
            parser.error(f'Duplicate or reserved native tool label: {label}')
        path = pathlib.Path(binary).resolve()
        args.native_tools[label] = dict(engine=engine, binary=str(path),
                                       binary_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if args.linux_cpus is not None:
        if sys.platform != 'linux' or any(cpu < 0 for cpu in args.linux_cpus):
            parser.error('--linux-cpus requires Linux and nonnegative CPU indices')
        args.track_resources = True
        if args.outer_grace is None:
            args.outer_grace = 0
    if args.perf and not args.linux_cpus:
        parser.error('--perf requires --linux-cpus')
    if any(m.startswith('smpt') and m not in SMPT_MODES for m in args.methods):
        parser.error('Unknown SMPT configuration; available: '+', '.join(SMPT_MODES))
    if any(m.startswith('its-') and m not in ITS_MODES for m in args.methods):
        parser.error('Unknown ITS configuration')
    if any(m in ITS_MODES for m in args.methods):
        if args.its_runtime_config is None or not args.its_runtime_config.is_file():
            parser.error('ITS requires --its-runtime-config pointing to the qualified runtime JSON')
        args.its_runtime_config = args.its_runtime_config.resolve()
    if not math.isfinite(args.seconds) or args.seconds <= 0 or args.repeat < 1:
        parser.error('Positive finite seconds and positive repeat required')
    if args.outer_grace is not None and (not math.isfinite(args.outer_grace) or args.outer_grace < 0):
        parser.error('Finite nonnegative outer grace required')
    if args.memory_mib is not None and (args.memory_mib <= 0 or not args.track_resources):
        parser.error('Memory limit must be positive and requires --track-resources')
    args.binary = args.binary.resolve()
    args.baseline_binary = args.baseline_binary.resolve()
    args.verifypn_binary = args.verifypn_binary.resolve()
    args.verifypn_root = args.verifypn_root.resolve()
    args.baseline_binary = args.baseline_binary.resolve()
    args.native_python = args.native_python.absolute()
    args.smpt_root = args.smpt_root.resolve()
    # Preserve a virtual environment executable's symlink path.
    args.smpt_python = args.smpt_python.absolute()
    os.environ['PATH'] = os.pathsep.join([str(p.resolve()) for p in args.tool_bin]
                                       + [str(args.workspace_root/'vendor/venv/bin'), os.environ['PATH']])
    if args.track_resources:
        import psutil
    if any(m.startswith('smpt-full') or m in SMPT_SINGLE_CORE_MODES for m in args.methods):
        if not args.track_resources:
            parser.error('Full SMPT requires --track-resources to clean up detached subprocesses')
        missing = [name for name in ('reduce', 'walk', 'qsolve', 'z3') if not shutil.which(name)]
        if missing:
            parser.error('Missing full SMPT dependencies: '+', '.join(missing))
        help_text = subprocess.run(['walk', '-h'], capture_output=True, text=True, timeout=5)
        if any(m.startswith('smpt-full') and 'portable' not in m for m in args.methods) and '-rg' not in help_text.stdout + help_text.stderr:
            parser.error('SMPT sliced WALK requires a Tina version advertising -rg reduction options')
        if any('portable' in m for m in args.methods):
            marker = args.smpt_root/'PORTABILITY.json'
            if not marker.is_file():
                parser.error('Portable modes require the checkout created by scripts/setup-smpt-portable.py')
            expected = json.loads(marker.read_text())['patched_sha256']
            checked(args.smpt_root/'smpt/interfaces/walk.py', expected)
    corpus, output = args.corpus.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output/'runs.jsonl').exists():
        parser.error('Output already contains runs; choose a new output directory')
    manifest = corpus/'manifest.json'
    queries = [q for q in json.loads(manifest.read_text())['queries'] if re.search(args.filter, q['name'])]
    if args.order_seed is not None:
        random.Random(args.order_seed).shuffle(queries)
    inputs = preflight_inputs(queries, corpus, args.smpt_original or args.native_original or args.rust_original or bool(args.rust_original_method)
                              or any(m in VERIFYPN_MODES or m in ITS_MODES for m in args.methods))
    environment = dict(workspace_root=str(args.workspace_root), seconds=args.seconds, repeat=args.repeat, methods=args.methods,
                       native_tools=args.native_tools,
                       target_zero_trap_methods=args.target_zero_trap_method,
                       target_path_potential_methods=args.target_path_potential_method,
                       buffer_agglomeration_methods=args.buffer_agglomeration_method,
                       geometric_branches_methods=args.geometric_branches_method,
                       order_seed=args.order_seed, property_order=[q['name'] for q in queries],
                       max_states=args.max_states, platform=platform.platform(),
                       queries=len(queries), manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                       binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                       baseline_binary_sha256=(hashlib.sha256(args.baseline_binary.read_bytes()).hexdigest()
                                               if 'frozen-v2' in args.methods else None),
                       script_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted((ROOT/'scripts').iterdir())
                                      if p.is_file() and p.suffix in ('.py', '.txt')},
                       scope='Whole original properties; sequential cold processes. Native branches share a budget; AG answers invert counterexample reachability. Verification excluded from wall time.',
                       smpt_configurations={m: SMPT_MODES[m] for m in args.methods if m in SMPT_MODES},
                       smpt_root=str(args.smpt_root), smpt_python=str(args.smpt_python),
                       auto_reduce=args.auto_reduce, track_resources=args.track_resources,
                       smpt_original=args.smpt_original, outer_grace=args.outer_grace,
                       native_original=args.native_original, native_python=str(args.native_python),
                       rust_original=args.rust_original,
                       rust_original_methods=args.rust_original_method,
                       method_input_scope={m: dict(mode=method_input_mode(m, args),
                                                  scope=INPUT_SCOPES[method_input_mode(m, args)])
                                           for m in args.methods},
                       linux_cpus=args.linux_cpus, perf=args.perf,
                       native_python_sha256=hashlib.sha256(args.native_python.read_bytes()).hexdigest(),
                       native_input_scope=('Per-method selection; see method_input_scope.' if args.rust_original_method else
                                           INPUT_SCOPES['rust-original-v1' if args.rust_original else
                                                        'python-original-v1' if args.native_original else 'canonical-json']),
                       memory_mib=args.memory_mib,
                       tools={name: dict(path=path, sha256=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest())
                              for name in ('reduce', 'walk', 'tina', 'ndrio', 'struct', 'qsolve', '4ti2gmp', '4ti2int64', 'z3', 'minizinc')
                              if (path := shutil.which(name))},
                       smpt_source_sha256={str(p.relative_to(args.smpt_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted((args.smpt_root/'smpt').rglob('*.py'))},
                       smpt='Selected source directory; full modes enable automatic reduction. ceil(seconds) internal timeout and seconds+1 outer timeout including reduction. K-INDUCTION automatically adds BMC. PDR-COV applies only to monotone targets. Portfolio methods execute concurrently inside SMPT. No independent SMPT proof check. Resource sampling is best-effort, not cgroup isolation.')
    if any(m in SMPT_SINGLE_CORE_MODES for m in args.methods):
        environment['smpt_scheduling'] = {m: smpt_scheduling(m)
                                          for m in args.methods if m in SMPT_MODES}
        environment['smpt_auto_reduce_by_method'] = {
            m: args.auto_reduce or m.startswith('smpt-full') or m in SMPT_SINGLE_CORE_MODES
            for m in args.methods if m in SMPT_MODES}
        environment['smpt'] = ('Selected source directory. Requested methods are not effective workers. '
            'Official --mcc selects its own preliminary and subsequent portfolios. '
            'All added portable configurations require automatic reduction and resource tracking. '
            'Internal timeout ceil(seconds); outer allowance seconds plus configured grace '
            '(default zero on Linux, one second elsewhere). Added configurations reject '
            'expired or over-budget answers. External proofs are not independently checked. '
            'See linux_cpus, perf and per-row resources for enforcement.')
    environment['input_preflight'] = dict(mode='streaming-deduplicated-sha256',
                                          unique_files=len(inputs.seen), bytes_hashed=inputs.bytes_hashed)
    environment['collection_counts'] = dict(planned=len(queries),
        imported=sum(q['status'] == 'imported' for q in queries),
        unsupported=sum(q['status'] != 'imported' for q in queries),
        explicitly_unobserved=sum(q.get('observed') is False for q in queries))
    environment['bounded_validation'] = dict(enabled=args.bounded_validation,
        seconds=args.validation_seconds, memory_mib=args.validation_memory_mib,
        response_mib=args.validation_response_mib, dag_check_max_work=args.validation_dag_work,
        included_in_solver_timing=False)
    path = ROOT/'scripts/bounded_validation.py'
    environment['script_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if args.rust_original or args.rust_original_method:
        path = ROOT/'scripts/rust_original_validation.py'
        environment['script_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if any(m in VERIFYPN_MODES for m in args.methods):
        from verifypn_runner import provenance
        environment['verifypn'] = provenance(args.verifypn_binary, args.verifypn_root,
                                                [m for m in args.methods if m in VERIFYPN_MODES])
        path = ROOT/'scripts/verifypn_runner.py'
        environment['script_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if any(m in ITS_MODES for m in args.methods):
        from its_runner import provenance
        environment['its'] = provenance(args.its_runtime_config)
    if args.linux_cpus:
        path = ROOT/'scripts/linux_runner.py'
        environment['script_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        environment['linux_host'] = dict(
            lscpu=subprocess.check_output(['lscpu'], text=True),
            topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,CACHE'], text=True),
            kernel=platform.release(),
            perf_event_paranoid=pathlib.Path('/proc/sys/kernel/perf_event_paranoid').read_text().strip(),
            loadavg=pathlib.Path('/proc/loadavg').read_text().strip(),
            caveat='CPU affinity is not exclusive CPU isolation. Retired instructions count user-space work; wall and cgroup CPU/memory are recorded separately. Deadline/OOM runs remain unknown during counter-flush shutdown grace.')
    (output/'environment.json').write_text(json.dumps(environment, indent=2)+'\n')
    snapshot = output/'runner-source'
    snapshot.mkdir(exist_ok=True)
    for name in environment['script_sha256']:
        shutil.copyfile(ROOT/'scripts'/name, snapshot/name)
    os.environ['PATH'] = str(args.workspace_root/'vendor/venv/bin')+os.pathsep+os.environ['PATH']
    rows = []
    with (output/'runs.jsonl').open('w') as records:
        for query_index, query in enumerate(queries):
            for repeat in range(args.repeat):
                order = args.methods if repeat % 2 == 0 else args.methods[::-1]
                if args.order_seed is not None:
                    offset = (query_index + repeat) % len(order)
                    order = order[offset:] + order[:offset]
                for method in order:
                    inputs.unchanged()
                    if query['status'] != 'imported':
                        result = import_failure(query)
                    elif method in ITS_MODES:
                        from its_runner import run as its
                        result = its(query, corpus, output, method, repeat, args, execute)
                    elif method in VERIFYPN_MODES:
                        from verifypn_runner import run as verifypn
                        result = verifypn(query, corpus, output, method, repeat, args, execute)
                    else:
                        result = smpt(query, corpus, output, method, repeat, args) if method in SMPT_MODES else native(query, corpus, output, method, repeat, args)
                    result = admit(result, args.seconds)
                    row = dict(query=query['name'], suite=query['suite'],
                               source_corpus=query.get('source_corpus'),
                               family=query.get('family'), family_group=query.get('family_group'),
                               method=method, repeat=repeat,
                               property_kind=query.get('kind'), **result)
                    if method in SMPT_SINGLE_CORE_MODES:
                        row.update(smpt_scheduling(method))
                    row['execution_attempted'] = query['status'] == 'imported'
                    row['collection_status'] = query['status']
                    row['collection_observed'] = query.get('observed')
                    row['property_slot'] = query.get('property_slot')
                    row['property_truth'] = property_truth(query.get('kind'), row['verdict'])
                    row['input_mode'] = method_input_mode(method, args)
                    rows.append(row)
                    records.write(json.dumps(row)+'\n')
                    records.flush()
                    print(query['name'], method, row['verdict'], row['property_truth'], flush=True)
    lines = ['# Reachability benchmark comparison', '', f'{len(queries)} original properties; {args.seconds}s budget; {args.repeat} repetition(s).', '',
             '| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |', '|---|---:|---:|---:|---:|']
    for method in args.methods:
        groups = collections.defaultdict(set)
        for row in rows:
            if row['method'] == method:
                groups[row['query']].add(row['verdict'])
        counts = collections.Counter(next(iter(v)) if len(v) == 1 else 'unstable' for v in groups.values())
        lines.append(f'| {method} | {counts["reachable"]} | {counts["unreachable"]} | {counts["unknown"]} | {sum(counts[k] for k in ("error", "unsupported", "unstable"))} |')
    disagreements = []
    for query in queries:
        answers = {r['property_truth'] for r in rows if r['query'] == query['name'] and r['property_truth'] is not None}
        if len(answers) > 1:
            disagreements.append(query['name'])
    lines += ['', 'Collection coverage: '+str(environment['collection_counts'])+'. Unsupported collection slots were not executed by any solver and remain in the denominator.',
              'Bounded validation: '+str(environment['bounded_validation'])+'. Validation resource failures do not establish a definitive answer.',
              'Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.',
              'Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.',
              f'Definitive disagreements: {disagreements}.',
              'Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.']
    failures = collections.Counter(r['method'] for r in rows if r.get('capability_failures'))
    if failures:
        lines += ['', 'Dependency/interface failures were observed: '+str(dict(failures))+'. These runs do not establish a fully working configuration; inspect capability_failures in runs.jsonl.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    if disagreements or any(r['verdict'] == 'error' for r in rows):
        sys.exit(1)


if __name__ == '__main__':
    main()
