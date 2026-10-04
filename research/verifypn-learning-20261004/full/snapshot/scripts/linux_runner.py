"""Run one benchmark in a transient systemd user service on Linux.

Cgroup memory/CPU accounting includes descendants, including detached children.
Perf counters are optional but never silently disabled. Counts of timed-out runs
can change with scheduling: the deadline controls elapsed time, not instructions.
"""
import csv
import errno
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import psutil


class PerfUnavailable(RuntimeError):
    pass


PROPERTIES = (
    'ActiveState', 'SubState', 'Result', 'ExecMainCode', 'ExecMainStatus',
    'ExecMainStartTimestampMonotonic', 'ExecMainExitTimestampMonotonic',
    'CPUUsageNSec', 'MemoryPeak', 'ControlGroup',
)
EVENTS = ('instructions:u', 'cycles:u', 'task-clock')


def parse_perf(path):
    """Preserve perf's raw value, runtime, and percentage of time running."""
    counters = {}
    for fields in csv.reader(Path(path).read_text().splitlines(), delimiter=';'):
        if len(fields) < 5 or fields[2] not in (*EVENTS, 'task-clock:u'):
            continue
        value, unit, observed_event, runtime, percentage = fields[:5]
        event = 'task-clock' if observed_event == 'task-clock:u' else observed_event
        if value.startswith('<'):
            raise PerfUnavailable(f'{event}: {value}')
        try:
            number = float(value) if '.' in value else int(value)
            running = float(percentage.rstrip('%'))
            runtime_ns = float(runtime)
        except ValueError as error:
            raise PerfUnavailable(f'Malformed perf counter: {fields!r}') from error
        if not math.isfinite(number) or not math.isfinite(running) or not math.isfinite(runtime_ns):
            raise PerfUnavailable(f'Nonfinite perf counter: {fields!r}')
        counters[event] = dict(value=number, unit=unit, observed_event=observed_event,
                               event_runtime_ns=runtime_ns,
                               time_running_percent=running, raw_fields=fields)
    missing = set(EVENTS) - set(counters)
    if missing:
        raise PerfUnavailable(f'Missing perf counters: {sorted(missing)}')
    return counters


def _show(unit):
    result = subprocess.run(['systemctl', '--user', 'show', unit,
                             '--property=' + ','.join(PROPERTIES)],
                            check=True, capture_output=True, text=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def _metric(state, key):
    value = state.get(key)
    if not value or value in ('[not set]', 'infinity', '18446744073709551615'):
        return None
    return int(value)


def _remember_processes(state, known):
    group = state.get('ControlGroup')
    if not group:
        return
    try:
        pids = (Path('/sys/fs/cgroup') / group.lstrip('/') / 'cgroup.procs').read_text().split()
    except OSError as error:
        if error.errno in (errno.ENOENT, errno.ENODEV):
            return
        raise
    for pid in pids:
        try:
            process = psutil.Process(int(pid))
            known[(process.pid, process.create_time())] = process
        except psutil.Error:
            pass


def run(command, cwd, seconds, output, memory_bytes=None, *, cpus, perf=False):
    """Return (observed wall seconds, return code, expired, usage).

    Explicit CPU affinity is required. Main-process completion retains accounting
    until this function stops the unique unit and all its remaining descendants.
    perf=True requires all requested counters; failure raises PerfUnavailable.
    """
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('seconds must be positive and finite')
    if not cpus or any(type(cpu) is not int or cpu < 0 for cpu in cpus):
        raise ValueError('cpus must be a nonempty list of nonnegative CPU indices')
    if memory_bytes is not None and (type(memory_bytes) is not int or memory_bytes <= 0):
        raise ValueError('memory_bytes must be a positive integer')
    if not command:
        raise ValueError('empty command')
    command = [str(x) for x in command]
    executable = (os.path.abspath(Path(cwd) / command[0])
                  if '/' in command[0] else shutil.which(command[0]))
    if executable is None:
        raise FileNotFoundError(command[0])
    command[0] = executable
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('')
    perf_path = output.with_name(output.name + '.perf.csv')
    if perf:
        perf_path.unlink(missing_ok=True)
        perf_binary = shutil.which('perf')
        if perf_binary is None:
            raise PerfUnavailable('perf executable is unavailable')
        command = [perf_binary, 'stat', '--no-big-num', '-x', ';', '-o', str(perf_path),
                   '-e', ','.join(EVENTS), '--', *command]
    unit = 'pvass-' + uuid.uuid4().hex + '.service'
    properties = {
        'Type': 'exec', 'ExitType': 'main', 'RemainAfterExit': 'yes',
        'KillMode': 'control-group', 'KillSignal': 'SIGINT' if perf else 'SIGTERM',
        'TimeoutStopSec': '1s',
        'RuntimeMaxSec': f'{seconds:.9f}s', 'CPUAccounting': 'yes',
        'MemoryAccounting': 'yes', 'MemorySwapMax': '0', 'OOMPolicy': 'kill',
        'CPUAffinity': ' '.join(str(cpu) for cpu in sorted(set(cpus))),
        'StandardOutput': 'file:' + str(output).replace('%', '%%'),
        'StandardError': 'inherit',
    }
    if memory_bytes is not None:
        properties['MemoryMax'] = str(memory_bytes)
    launch = ['systemd-run', '--user', '--quiet', '--unit=' + unit,
              '--expand-environment=no',
              '--working-directory=' + str(Path(cwd).resolve()).replace('%', '%%')]
    launch.extend('--property=' + key + '=' + value for key, value in properties.items())
    launch.extend('--setenv=' + key + '=' + value for key, value in os.environ.items())
    launch.extend(['--', *command])
    start = time.perf_counter()
    state = None
    known = {}
    launched = False
    try:
        subprocess.run(launch, check=True, capture_output=True, text=True)
        launched = True
        while True:
            state = _show(unit)
            _remember_processes(state, known)
            if state.get('SubState') in ('exited', 'failed', 'dead'):
                break
            if time.perf_counter() - start > seconds + 15:
                raise RuntimeError(f'{unit}: service did not reach a terminal state: {state}')
            time.sleep(0.01)
        # Read again after completion: initial active/running values are incomplete.
        state = _show(unit)
        elapsed = time.perf_counter() - start
        status = int(state.get('ExecMainStatus', '0'))
        code = status if state.get('ExecMainCode') == '1' else -status
        result = state.get('Result', '')
        expired = result in ('timeout', 'oom-kill')
        if result != 'success' and code == 0:
            code = 1
        cpu_ns = _metric(state, 'CPUUsageNSec')
        usage = dict(runner='linux-systemd-user', unit=unit, cpus=sorted(set(cpus)),
                     systemd_result=result, systemd_properties=state,
                     cpu_seconds=None if cpu_ns is None else cpu_ns / 1e9,
                     peak_memory_bytes=_metric(state, 'MemoryPeak'),
                     memory_limit_bytes=memory_bytes, memory_limit_exceeded=result == 'oom-kill',
                     perf_enabled=perf, perf_counters=None)
        if perf:
            try:
                usage['perf_counters'] = parse_perf(perf_path)
            except (OSError, PerfUnavailable) as error:
                if expired:
                    # A cgroup kill can terminate perf before it exports counters.
                    # Keep the resource failure in the denominator, with no invented count.
                    usage['perf_failure'] = str(error)
                else:
                    raise PerfUnavailable(f'{error}; solver/perf output: {output.read_text()[-4000:]}') from error
        return elapsed, code, expired, usage
    finally:
        # Unique unit name is the ownership boundary. Never enumerate/stop other jobs.
        subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True, check=launched)
        subprocess.run(['systemctl', '--user', 'reset-failed', unit], capture_output=True)
        # After an OOM kill, cgroup removal can precede process-table teardown.
        # Revalidate identities and wait before allowing the next timed command.
        _, alive = psutil.wait_procs(list(known.values()), timeout=3)
        survivors = []
        for process in alive:
            try:
                if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                    survivors.append(process.pid)
            except psutil.Error:
                pass
        if survivors:
            raise RuntimeError(f'{unit}: processes still exiting after cleanup: {survivors}')
        if state is not None:
            output.with_name(output.name + '.systemd.json').write_text(json.dumps(state, indent=2) + '\n')
