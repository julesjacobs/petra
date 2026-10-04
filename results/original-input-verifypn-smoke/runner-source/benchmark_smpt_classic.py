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
import sys
import shutil
import subprocess

from benchmark import run, verify

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


def execute(command, cwd, seconds, output, args):
    if args.track_resources:
        from process_runner import run as tracked_run, workspace_workloads
        conflicts = workspace_workloads(ROOT)
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


def native(query, corpus, output, method, repeat, args):
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
        binary = args.baseline_binary if method == 'frozen-v2' else args.binary
        engine = 'portfolio-v2' if method == 'frozen-v2' else method
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
                check = verify(problem, answer)
                checks.append(check)
                result.update(independent_check=check, engine=answer['method'])
            except Exception as error:
                verdict = 'error'
                result['error'] = repr(error)
        verdicts.append(verdict)
        branches.append(dict(result, verdict=verdict))
    return dict(verdict=aggregate(verdicts), wall_seconds=wall, branches=branches,
                independent_checks=checks)


def native_original(query, corpus, output, method, repeat, args):
    artifacts = output/f'{query["name"]}.{method}.{repeat}.original'
    log = output/f'{query["name"]}.{method}.{repeat}.frontend.json'
    binary = args.baseline_binary if method == 'frozen-v2' else args.binary
    engine = 'portfolio-v2' if method == 'frozen-v2' else method
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
                check = verify(problems[i], answer)
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
    except Exception as error:
        result.update(verdict='error', error=repr(error))
    return result


def smpt(query, corpus, output, method, repeat, args):
    log = output/f'{query["name"]}.{method}.{repeat}.log'
    net_key, property_key = ('pnml', 'xml') if args.smpt_original else ('net', 'property')
    command = [str(args.smpt_python), '-m', 'smpt',
               '-n', str(corpus/query[net_key]), '--xml', str(corpus/query[property_key]),
               '--methods', *SMPT_MODES[method], '--timeout', str(math.ceil(args.seconds)),
               '--show-time', '--show-techniques', '--show-model', '--export-proof', str(log.with_suffix('.proof'))]
    if args.auto_reduce or method.startswith('smpt-full'):
        command.append('--auto-reduce')
    grace = 1 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, args.smpt_root, args.seconds+grace, log, args)
    contents = log.read_text()
    capability_failures = [line for line in contents.splitlines()
                           if re.search(r'command not found|No such file or directory|bad command line|error: 4ti2 failed', line)]
    matches = re.findall(r'^FORMULA '+re.escape(query['property_id'])+r' (TRUE|FALSE)(?: |$)', contents, re.M)
    verdict = 'unknown'
    if len(set(matches)) > 1:
        verdict = 'error'
    elif matches:
        truth = matches[0] == 'TRUE'
        verdict = 'reachable' if truth == (query['kind'] == 'EF') else 'unreachable'
    elif (code and not expired) or 'Traceback (most recent call last):' in contents:
        verdict = 'error'
    return dict(verdict=verdict, wall_seconds=wall, exit_code=code,
                capability_failures=sorted(set(capability_failures)),
                resources=usage, command=command,
                outer_timeout=expired, enabled_methods=SMPT_MODES[method],
                subprocess_error='Traceback (most recent call last):' in contents,
                formula_output=next((line for line in contents.splitlines() if line.startswith('FORMULA ')), None),
                independent_checks=['none-external-smpt'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=pathlib.Path, default=ROOT/'benchmarks/smpt-classic')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'results/smpt-classic')
    parser.add_argument('--binary', type=pathlib.Path, default=ROOT/'target/release/vass-reach')
    parser.add_argument('--baseline-binary', type=pathlib.Path, default=ROOT/'results/solver-v2/vass-reach')
    parser.add_argument('--verifypn-binary', type=pathlib.Path, default=ROOT/'vendor/verifypn/build-release/verifypn/bin/verifypn')
    parser.add_argument('--verifypn-root', type=pathlib.Path, default=ROOT/'vendor/verifypn')
    parser.add_argument('--methods', nargs='+', default=['portfolio-v2', 'smpt-portfolio-unsaturated'])
    parser.add_argument('--seconds', type=float, default=2)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--max-states', type=int, default=200000)
    parser.add_argument('--filter', default='')
    parser.add_argument('--smpt-root', type=pathlib.Path, default=ROOT/'vendor/SMPT')
    parser.add_argument('--smpt-python', type=pathlib.Path, default=ROOT/'vendor/venv/bin/python')
    parser.add_argument('--tool-bin', type=pathlib.Path, action='append', default=[])
    parser.add_argument('--auto-reduce', action='store_true')
    parser.add_argument('--track-resources', action='store_true', help='Sample process trees; requires psutil')
    parser.add_argument('--smpt-original', action='store_true', help='Give SMPT original PNML/XML including NUPN annotations')
    parser.add_argument('--native-original', action='store_true', help='Time Python PNML/XML translation and all Rust branches within one outer invocation')
    parser.add_argument('--native-python', type=pathlib.Path, default=pathlib.Path(sys.executable), help='Python frontend executable for --native-original')
    parser.add_argument('--outer-grace', type=float, help='Common additional wall allowance; zero gives a strict outer deadline')
    parser.add_argument('--memory-mib', type=int, help='Sampled aggregate RSS limit; requires --track-resources')
    args = parser.parse_args()
    if any(m.startswith('smpt') and m not in SMPT_MODES for m in args.methods):
        parser.error('Unknown SMPT configuration; available: '+', '.join(SMPT_MODES))
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
                                       + [str(ROOT/'vendor/venv/bin'), os.environ['PATH']])
    if args.track_resources:
        import psutil
    if any(m.startswith('smpt-full') for m in args.methods):
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
    for q in queries:
        if q['status'] == 'imported':
            checked(corpus/q['net'], q['net_sha256'])
            checked(corpus/q['property'], q['property_sha256'])
            if args.smpt_original or args.native_original or 'verifypn' in args.methods:
                checked(corpus/q['pnml'], q['pnml_sha256'])
                checked(corpus/q['xml'], q['xml_sha256'])
            for branch in q['branches']:
                checked(corpus/branch['path'], branch['sha256'])
    environment = dict(seconds=args.seconds, repeat=args.repeat, methods=args.methods,
                       max_states=args.max_states, platform=platform.platform(),
                       queries=len(queries), manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                       binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                       baseline_binary_sha256=(hashlib.sha256(args.baseline_binary.read_bytes()).hexdigest()
                                               if 'frozen-v2' in args.methods else None),
                       script_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in [pathlib.Path(__file__), ROOT/'scripts/native_original.py', ROOT/'scripts/smpt_import.py', ROOT/'scripts/benchmark.py', ROOT/'scripts/token_moment_checker.py', ROOT/'scripts/token_cut_checker.py', ROOT/'scripts/process_runner.py', ROOT/'scripts/requirements.txt']},
                       scope='Whole original properties; sequential cold processes. Native branches share a budget; AG answers invert counterexample reachability. Verification excluded from wall time.',
                       smpt_configurations={m: SMPT_MODES[m] for m in args.methods if m in SMPT_MODES},
                       smpt_root=str(args.smpt_root), smpt_python=str(args.smpt_python),
                       auto_reduce=args.auto_reduce, track_resources=args.track_resources,
                       smpt_original=args.smpt_original, outer_grace=args.outer_grace,
                       native_original=args.native_original, native_python=str(args.native_python),
                       native_python_sha256=hashlib.sha256(args.native_python.read_bytes()).hexdigest(),
                       native_input_scope=('Original PNML/XML; Python startup, parsing, target DNF, branch serialization, Rust startup and solving inside one process-tree deadline. Canonical translation comparison and witness/proof checking outside timing.' if args.native_original else 'Pretranslated canonical JSON; original-input translation excluded from timing.'),
                       memory_mib=args.memory_mib,
                       tools={name: dict(path=path, sha256=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest())
                              for name in ('reduce', 'walk', 'tina', 'ndrio', 'struct', 'qsolve', '4ti2gmp', '4ti2int64', 'z3', 'minizinc')
                              if (path := shutil.which(name))},
                       smpt_source_sha256={str(p.relative_to(args.smpt_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted((args.smpt_root/'smpt').rglob('*.py'))},
                       smpt='Selected source directory; full modes enable automatic reduction. ceil(seconds) internal timeout and seconds+1 outer timeout including reduction. K-INDUCTION automatically adds BMC. PDR-COV applies only to monotone targets. Portfolio methods execute concurrently inside SMPT. No independent SMPT proof check. Resource sampling is best-effort, not cgroup isolation.')
    if 'verifypn' in args.methods:
        from verifypn_runner import provenance
        environment['verifypn'] = provenance(args.verifypn_binary, args.verifypn_root)
        path = ROOT/'scripts/verifypn_runner.py'
        environment['script_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'environment.json').write_text(json.dumps(environment, indent=2)+'\n')
    snapshot = output/'runner-source'
    snapshot.mkdir(exist_ok=True)
    for name in environment['script_sha256']:
        shutil.copyfile(ROOT/'scripts'/name, snapshot/name)
    os.environ['PATH'] = str(ROOT/'vendor/venv/bin')+os.pathsep+os.environ['PATH']
    rows = []
    with (output/'runs.jsonl').open('w') as records:
        for query in queries:
            for repeat in range(args.repeat):
                for method in args.methods if repeat % 2 == 0 else args.methods[::-1]:
                    if query['status'] != 'imported':
                        result = dict(verdict='unsupported', error=query.get('error'))
                    elif method == 'verifypn':
                        from verifypn_runner import run as verifypn
                        result = verifypn(query, corpus, output, method, repeat, args, execute)
                    else:
                        result = smpt(query, corpus, output, method, repeat, args) if method in SMPT_MODES else native(query, corpus, output, method, repeat, args)
                    row = dict(query=query['name'], suite=query['suite'], method=method, repeat=repeat,
                               property_kind=query.get('kind'), **result)
                    row['property_truth'] = property_truth(query.get('kind'), row['verdict'])
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
    lines += ['', 'Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.',
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
