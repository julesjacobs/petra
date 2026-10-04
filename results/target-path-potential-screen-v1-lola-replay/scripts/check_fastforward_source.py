#!/usr/bin/env python3
"""Run independent original-LoLA positive-witness replay in a bounded worker.

Request JSON: corpus, source, query, answer; optional branch, manifest_sha256,
seconds (30), memory_mib (2048), max_work (200000000), max_file_bytes (256 MiB).
This writes separate evidence and never changes benchmark results or verdicts.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from fastforward_source_checker import check_artifact


def worker(request):
    try:
        return check_artifact(request)
    except TimeoutError as error:
        return {'verdict': 'unknown', 'validation_failure': 'resource-limit', 'error': str(error)}
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, RecursionError) as error:
        return {'verdict': 'error', 'validation_failure': 'invalid-source-witness', 'error': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--response', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.request.stat().st_size > 1024 * 1024:
        parser.error('request exceeds one MiB')
    request = json.loads(args.request.read_text())
    if args.worker:
        args.response.write_text(json.dumps(worker(request)) + '\n')
        return
    from process_runner import run
    seconds, memory = request.get('seconds', 30), request.get('memory_mib', 2048)
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0 or type(memory) is not int or memory <= 0:
        parser.error('positive finite seconds and positive integer memory_mib required')
    if args.response.exists():
        parser.error('refusing to overwrite existing validation response')
    args.response.parent.mkdir(parents=True, exist_ok=True)
    child_response = args.response.with_name(args.response.name + '.worker.json')
    log = args.response.with_name(args.response.name + '.worker.log')
    if child_response.exists() or log.exists():
        parser.error('refusing to overwrite existing worker artifacts')
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--request', str(args.request.resolve()), '--response', str(child_response.resolve())]
    wall, code, expired, resources = run(command, Path(__file__).resolve().parents[1], seconds, log, memory * 1024**2)
    if expired or code != 0:
        reason = 'memory-limit' if resources.get('memory_limit_exceeded') else 'timeout' if expired else 'worker-failure'
        result = {'verdict': 'unknown', 'validation_failure': reason}
    elif not child_response.exists() or child_response.stat().st_size > 1024 * 1024:
        result = {'verdict': 'unknown', 'validation_failure': 'invalid-worker-response'}
    else:
        try:
            result = json.loads(child_response.read_text())
        except (ValueError, OSError):
            result = {'verdict': 'unknown', 'validation_failure': 'invalid-worker-response'}
    result['checker_sources'] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('check_fastforward_source.py', 'fastforward_source_checker.py', 'process_runner.py')}
    result['validation'] = {'wall_seconds': wall, 'exit_code': code, 'outer_timeout': expired,
                            'resources': resources, 'seconds_limit': seconds, 'memory_limit_bytes': memory * 1024**2,
                            'included_in_solver_timing': False,
                            'memory_enforcement': 'portable sampled process-tree RSS; not a Linux cgroup'}
    args.response.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
