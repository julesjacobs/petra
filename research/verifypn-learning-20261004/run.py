#!/usr/bin/env python3
"""Freeze or run serial, paired native measurements. Never builds a solver."""
import argparse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import sys
import sysconfig
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE_SHA = '0f591ec86df357cac0ce175d26a9a77d59a69cc4bc51ec9bfe82a6543971b22e'
CORPORA = [('existing176', 'benchmarks/general-development-v3', 176, 175),
           ('expansion192', 'benchmarks/development-expansion-v4', 192, 191)]
METHODS = ['candidate', 'baseline']
DEFINITIVE = {'reachable', 'unreachable'}
SEED = 2026100407


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def is_full(name):
    return name == 'full' or name.startswith('full-')


def campaign_path(name):
    require((is_full(name) or name.startswith('diagnostic-')) and all(c.isalnum() or c in '-_' for c in name),
            'Campaign must be full, full-NAME or diagnostic-NAME')
    return HERE / name


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def load_runner(snapshot):
    sys.path.insert(0, str(snapshot / 'scripts'))
    import benchmark_smpt_classic as runner
    runner.ROOT = ROOT
    return runner


def schedule(corpora, selected, index):
    output = []
    for ci, name in enumerate(['expansion192', 'existing176'] if index == 0 else ['existing176', 'expansion192']):
        queries = [q for q in corpora[name]['queries'] if (name, q) in selected]
        random.Random(SEED + 100 * index + ci).shuffle(queries)
        for qi, query in enumerate(queries):
            offset = (qi + index) % 2
            output.extend(dict(corpus=name, query=query, method=m) for m in METHODS[offset:] + METHODS[:offset])
    return output


def runtime_files():
    import psutil
    paths = {Path(sys.executable).absolute(), Path(sys.executable).resolve()}
    for prefix in (Path(sys.prefix), Path(sys.base_prefix)):
        if (prefix / 'pyvenv.cfg').is_file():
            paths.add(prefix / 'pyvenv.cfg')
    stdlib = Path(sysconfig.get_path('stdlib')).resolve()
    for path in stdlib.rglob('*'):
        if 'site-packages' in path.parts or '__pycache__' in path.parts:
            continue
        if path.is_file() and path.suffix in ('.py', '.so', '.dylib', '.zip'):
            paths.add(path)
    for path in Path(psutil.__file__).resolve().parent.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            paths.add(path)
    libdir, library = sysconfig.get_config_var('LIBDIR'), sysconfig.get_config_var('LDLIBRARY')
    if libdir and library and (Path(libdir) / library).is_file():
        paths.add(Path(libdir) / library)
    return {str(p): sha(p) for p in sorted(paths)}


def freeze(args):
    require(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'Python assertions must be enabled')
    folder = campaign_path(args.campaign)
    require(not folder.exists(), 'Campaign already exists; choose a fresh diagnostic name')
    require(not (is_full(args.campaign) and args.query), 'Full campaign cannot select a subset')
    require(is_full(args.campaign) or args.query, 'Diagnostic campaign requires explicit --query selections')
    require(args.linux_cpus is None or sys.platform == 'linux', 'Linux backend requires Linux')
    cpus = sorted(set(args.linux_cpus)) if args.linux_cpus is not None else None
    if cpus is not None:
        require(len(cpus) == 1 and 0 <= cpus[0] < os.cpu_count(), 'Pin exactly one available logical CPU')
    baseline = HERE / 'baseline/vass-reach'
    require(sha(baseline) == BASELINE_SHA, 'Baseline differs from preserved binary')
    candidate = args.candidate.resolve()
    require(candidate.is_file() and os.access(candidate, os.X_OK), 'Candidate is not executable')
    require(sha(candidate) != BASELINE_SHA, 'Candidate is identical to baseline')
    corpora, queries, inputs = {}, {}, {}
    for name, path, count, representatives in CORPORA:
        corpus = ROOT / path
        manifest = corpus / 'manifest.json'
        entries = json.loads(manifest.read_text())['queries']
        require(len(entries) == count and len({q['name'] for q in entries}) == count, 'Corpus denominator differs')
        groups = defaultdict(list)
        inputs[str(manifest.relative_to(ROOT))] = sha(manifest)
        for q in entries:
            require(q['status'] == 'imported' and q['kind'] in ('EF', 'AG'), 'Unexpected unavailable or unsupported query')
            queries[name, q['name']] = q
            groups[tuple(b['sha256'] for b in q['branches'])].append(q['name'])
            for p, h in [(q[k], q[k + '_sha256']) for k in ('pnml', 'xml', 'net', 'property')] + [(b['path'], b['sha256']) for b in q['branches']]:
                source = (corpus / p).resolve()
                require(source.is_relative_to(corpus.resolve()), 'Input outside corpus')
                key = str(source.relative_to(ROOT))
                if key not in inputs:
                    require(sha(source) == h, 'Input hash differs: ' + key)
                    inputs[key] = h
                require(inputs[key] == h, 'Conflicting input hash')
        require(len(groups) == representatives, 'Representative denominator differs')
        corpora[name] = dict(path=path, properties=count, representatives=representatives,
                             queries=[q['name'] for q in entries], groups=[sorted(g) for g in groups.values()])
    selected = set(queries)
    if args.query:
        selected = set()
        for name in args.query:
            matches = {key for key in queries if name in (key[1], key[0] + '/' + key[1])}
            require(len(matches) == 1, 'Missing or ambiguous --query: ' + name)
            selected.update(matches)
    sources = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', HERE / 'run.py', HERE / 'audit.py']
    sources += [p for directory in ('src', 'tests', 'scripts', 'vendor/varisat')
                for p in sorted((ROOT / directory).rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    source_before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    binary_before = sha(candidate)
    receipt = None
    if args.build_receipt:
        receipt = json.loads(args.build_receipt.read_text())
        require(receipt.get('binary_sha256') == binary_before, 'Build receipt binary differs')
        expected = {k: v for k, v in source_before.items()
                    if k in ('Cargo.toml', 'Cargo.lock') or k.startswith(('src/', 'vendor/varisat/'))}
        require(receipt.get('source_sha256') == expected, 'Build receipt source inventory differs')
    folder.mkdir()
    snapshot = folder / 'snapshot'
    snapshot.mkdir()
    for source in sources:
        rel = source.relative_to(ROOT)
        target = snapshot / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        require(sha(target) == source_before[str(rel)] == sha(source), 'Source changed during freeze')
    binaries = {}
    for label, source in [('candidate', candidate), ('baseline', baseline)]:
        target = snapshot / (label + '-vass-reach')
        shutil.copy2(source, target)
        digest = binary_before if label == 'candidate' else BASELINE_SHA
        require(sha(target) == digest == sha(source), 'Binary changed during freeze')
        binaries[label] = dict(binary=str(target.relative_to(ROOT)), binary_sha256=digest,
                               engine='portfolio-excess', original=str(source))
    baseline_pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted((HERE / 'baseline').rglob('*')) if p.is_file()}
    stages = {f'repeat{i + 1}': dict(schedule=schedule(corpora, selected, i), expected_rows=2 * len(selected)) for i in range(2)}
    plan = dict(format='verifypn-learning-native-paired-v1', campaign=args.campaign, frozen_utc=now(),
        workspace=str(ROOT), properties=len(selected), methods=METHODS, repeat=2,
        selected_queries=[dict(corpus=c, query=q) for c, q in sorted(selected)], corpora=corpora, stages=stages,
        seconds=5.0, outer_grace=0.0, max_states=2000000, memory_mib=2048, order_seed=SEED,
        validation_seconds=60.0, validation_memory_mib=2048, validation_response_mib=64,
        validation_dag_work=200000000, linux_cpus=cpus, perf=False,
        backend='linux-systemd-user' if cpus else 'portable-process-tree-sampling',
        host_policy=dict(strict=is_full(args.campaign) and not args.allow_contention, allow_contention=args.allow_contention, idle_samples=5, sample_seconds=1.0,
                         max_normalized_load1=0.25, max_cpu_percent=10.0),
        source_sha256=source_before, input_sha256=inputs, baseline_sha256=baseline_pins,
        binaries=binaries, python=str(Path(sys.executable).absolute()), runtime_sha256=runtime_files(),
        python_version=sys.version, platform=platform.platform(), build_receipt=receipt,
        build_correspondence='supplied-build-receipt' if receipt else 'unverified-source-and-binary-snapshot',
        scope=('Contended full development coverage pilot; no speed claim' if args.allow_contention else 'Full development comparison') if is_full(args.campaign) else 'Selected-property diagnostic; no full-corpus or idle-host claim',
        limitations=['Portable solver and validator memory/CPU metrics are sampled; short-lived children may escape samples.',
                    'Portable wall time includes cleanup; Linux solver wall time ends before final cleanup.',
                    'Host samples detect observed contention; they do not establish exclusive CPUs or rule out between-sample interference.',
                    'Source/binary correspondence is unverified without a supplied build receipt; receipts are not reproducible-build verification.'])
    save(folder / 'plan.json', plan)
    print(json.dumps(dict(status='frozen-not-run', campaign=args.campaign, plan_sha256=sha(folder / 'plan.json'),
                         properties=len(selected), rows_per_repeat=2 * len(selected), build_correspondence=plan['build_correspondence'])))


def pin_checks(folder, plan):
    from bounded_validation import InputChecks
    checks = InputChecks()
    checks.check(folder / 'plan.json', sha(folder / 'plan.json'))
    for rel, digest in plan['source_sha256'].items():
        checks.check(folder / 'snapshot' / rel, digest)
    for name in ('run.py', 'audit.py'):
        checks.check(HERE / name, plan['source_sha256'][str((HERE / name).relative_to(ROOT))])
    for key in ('input_sha256', 'baseline_sha256'):
        for rel, digest in plan[key].items():
            checks.check(ROOT / rel, digest)
    for path, digest in plan['runtime_sha256'].items():
        checks.check(Path(path), digest)
    for tool in plan['binaries'].values():
        checks.check(ROOT / tool['binary'], tool['binary_sha256'])
    require(plan['workspace'] == str(ROOT), 'Frozen paths cannot be relocated')
    require(str(Path(sys.executable).absolute()) == plan['python'] and sys.version == plan['python_version'], 'Use frozen Python runtime')
    require(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'Python assertions must be enabled')
    require(not any(k.startswith('VASS_') or k in ('PYTHONPATH', 'PYTHONHOME') for k in os.environ),
            'Unset VASS_*, PYTHONPATH and PYTHONHOME for measurements')
    return checks


@contextmanager
def serial_lock():
    with (ROOT / '.pvass-measurement.lock').open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another measurement harness owns the workspace lock')
        yield


def workspace_idle():
    import psutil
    from process_runner import workspace_workloads
    conflicts = workspace_workloads(ROOT)
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if process.pid == os.getpid() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            argv = process.info['cmdline'] or []
            if 'python' in (process.info['name'] or '').lower() and Path(process.cwd()).is_relative_to(ROOT):
                if any(Path(a).name in ('run.py', 'bounded_validation.py') or
                       (a.endswith('.py') and ('benchmark' in Path(a).name or 'diagnostic' in Path(a).name)) for a in argv):
                    conflicts.append(dict(pid=process.pid, name=process.info['name']))
        except (psutil.Error, OSError, SystemError):
            pass
    require(not conflicts, 'Overlapping workspace workloads: ' + repr(conflicts))


class HostMonitor:
    def __init__(self, stream, policy):
        import psutil
        self.psutil, self.stream, self.policy = psutil, stream, policy
        self.stop = threading.Event()
        self.samples, self.error, self.thread = [], None, None
        self.previous = psutil.cpu_times(percpu=True)
        self.started = time.monotonic()

    def sample(self, phase):
        psutil = self.psutil
        current = psutil.cpu_times(percpu=True)
        percentages = []
        for before, after in zip(self.previous, current):
            differences = {k: max(0, getattr(after, k) - getattr(before, k)) for k in after._fields}
            total = sum(v for k, v in differences.items() if k not in ('guest', 'guest_nice'))
            busy = total - differences.get('idle', 0) - differences.get('iowait', 0)
            percentages.append(100 * busy / total if total else 0)
        load = list(os.getloadavg())
        memory = psutil.virtual_memory()
        item = dict(utc=now(), monotonic_seconds=time.monotonic(), phase=phase,
                    logical_cpus=len(current), load_average=load, normalized_load1=load[0] / len(current),
                    cpu_times_before=[v._asdict() for v in self.previous], cpu_times_after=[v._asdict() for v in current],
                    cpu_percent=sum(percentages) / len(percentages), per_cpu_percent=percentages,
                    memory_available_bytes=memory.available, memory_total_bytes=memory.total)
        item['within_idle_thresholds'] = (item['normalized_load1'] <= self.policy['max_normalized_load1']
                                         and item['cpu_percent'] <= self.policy['max_cpu_percent'])
        self.previous = current
        self.stream.write(json.dumps(item) + '\n')
        self.stream.flush()
        self.samples.append(item)
        return item

    def preflight(self):
        for _ in range(self.policy['idle_samples']):
            time.sleep(self.policy['sample_seconds'])
            self.sample('preflight')
        if self.policy['strict']:
            require(all(s['within_idle_thresholds'] for s in self.samples), 'Host idle thresholds failed; no solver launched')

    def start(self):
        def collect():
            try:
                while not self.stop.wait(self.policy['sample_seconds']):
                    self.sample('measurement')
            except Exception as error:
                self.error = repr(error)
        self.thread = threading.Thread(target=collect, daemon=True)
        self.thread.start()

    def check(self):
        require(self.error is None, 'Host monitor failed: ' + str(self.error))
        if self.policy['strict']:
            # One busy solver/validator CPU is charged to this campaign; all host load remains visible.
            require(all(s['normalized_load1'] <= self.policy['max_normalized_load1'] + 1 / s['logical_cpus']
                        and s['cpu_percent'] <= self.policy['max_cpu_percent'] + 100 / s['logical_cpus']
                        for s in self.samples if s['phase'] != 'preflight'), 'Observed host contention; preserve partial campaign')

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join()
        self.sample('terminal')
        self.check()


def arguments(plan):
    return argparse.Namespace(seconds=plan['seconds'], max_states=plan['max_states'], outer_grace=0.0,
        memory_mib=plan['memory_mib'], track_resources=True, linux_cpus=plan['linux_cpus'], perf=False,
        rust_original=True, native_original=False, rust_original_method=[],
        native_tools={m: dict(info, binary=str(ROOT / info['binary'])) for m, info in plan['binaries'].items()},
        buffer_agglomeration_method=METHODS, target_zero_trap_method=[], target_path_potential_method=[],
        geometric_branches_method=[], native_python=Path(plan['python']), validation_seconds=plan['validation_seconds'],
        validation_memory_mib=plan['validation_memory_mib'], validation_response_mib=plan['validation_response_mib'],
        validation_dag_work=plan['validation_dag_work'], bounded_validation=True)


def rejection_reasons(row, query):
    from analyze_application_expansion import failure_flags, native_checked
    reasons = set(failure_flags(row))
    if not finite(row.get('wall_seconds')):
        reasons.add('invalid-wall-time')
    elif row['wall_seconds'] > 5.0:
        reasons.add('wall-budget')
    if row.get('exit_code') != 0:
        reasons.add('nonzero-exit')
    for field in ('validation_failure', 'answer_rejected', 'admission_failures', 'validation_skipped'):
        if row.get(field):
            reasons.add(field)
    if row.get('verdict') in DEFINITIVE and not native_checked(row, query):
        reasons.add('independent-check-failed')
    return sorted(reasons)


def run_stage(args):
    folder = campaign_path(args.campaign)
    plan = json.loads((folder / 'plan.json').read_text())
    runner = load_runner(folder / 'snapshot')
    with serial_lock():
        checks = pin_checks(folder, plan)
        workspace_idle()
        if args.stage == 'repeat2':
            previous = json.loads((folder / 'repeat1-audit.json').read_text())
            require(previous['status'] == 'passed' and previous['plan_sha256'] == sha(folder / 'plan.json'), 'First repetition audit must pass')
        output = ROOT / 'results/verifypn-learning-20261004' / args.campaign / args.stage
        require(not output.exists() and not (folder / (args.stage + '-execution.json')).exists(), 'Stage already attempted')
        output.mkdir(parents=True)
        for name in plan['corpora']:
            (output / name).mkdir()
        queries = {name: {q['name']: q for q in json.loads((ROOT / c['path'] / 'manifest.json').read_text())['queries']}
                   for name, c in plan['corpora'].items()}
        save(folder / (args.stage + '-execution.json'), dict(plan_sha256=sha(folder / 'plan.json'),
            stage=args.stage, started_utc=now(), pid=os.getpid(), platform=platform.platform(),
            python=plan['python'], backend=plan['backend'], host_policy=plan['host_policy']))
        count, completed, failure = 0, False, None
        host_stream, monitor = None, None
        try:
            host_stream = (output / 'host.jsonl').open('x')
            monitor = HostMonitor(host_stream, plan['host_policy'])
            monitor.preflight()
            monitor.start()
            with (output / 'runs.jsonl').open('x') as stream:
                for item in plan['stages'][args.stage]['schedule']:
                    checks.unchanged()
                    workspace_idle()
                    monitor.check()
                    query = queries[item['corpus']][item['query']]
                    corpus = ROOT / plan['corpora'][item['corpus']]['path']
                    result = runner.rust_original(query, corpus, output / item['corpus'], item['method'], 0, arguments(plan))
                    row = dict(item, repeat=0, family=query['family'], property_kind=query['kind'],
                               execution_attempted=True, collection_status=query['status'], **result)
                    reasons = rejection_reasons(row, query)
                    if row['verdict'] not in DEFINITIVE | {'unknown'} or (row['verdict'] in DEFINITIVE and reasons):
                        row['observed_verdict'] = row['verdict']
                        row['verdict'] = 'unknown'
                    row['admission_failures'] = reasons
                    row['property_truth'] = runner.property_truth(query['kind'], row['verdict'])
                    stream.write(json.dumps(row) + '\n')
                    stream.flush()
                    count += 1
                    print(item['corpus'], item['query'], item['method'], row['verdict'], flush=True)
                    monitor.check()
            checks.unchanged()
            completed = True
        except BaseException as error:
            failure = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            if monitor is not None:
                try:
                    monitor.finish()
                except Exception as error:
                    completed = False
                    failure = failure or repr(error)
            if host_stream is not None:
                host_stream.close()
            artifacts = {str(p.relative_to(ROOT)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
            save(folder / (args.stage + '-terminal.json'), dict(plan_sha256=sha(folder / 'plan.json'), stage=args.stage,
                finished_utc=now(), exit_code=0 if completed else 1, rows=count, failure=failure,
                artifact_sha256=artifacts, host_monitor_error=monitor.error if monitor else 'monitor-not-created'))
        require(completed, 'Stage incomplete: ' + str(failure))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('freeze')
    p.add_argument('--campaign', default='full')
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--query', action='append', default=[], help='Exact query name or corpus/query; diagnostic only')
    p.add_argument('--linux-cpus', type=int, nargs='+')
    p.add_argument('--build-receipt', type=Path)
    p.add_argument('--allow-contention', action='store_true', help='Freeze an explicitly contended coverage pilot; no speed claims')
    p = commands.add_parser('run')
    p.add_argument('--campaign', default='full')
    p.add_argument('stage', choices=['repeat1', 'repeat2'])
    args = parser.parse_args()
    (freeze if args.action == 'freeze' else run_stage)(args)


if __name__ == '__main__':
    main()
