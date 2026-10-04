#!/usr/bin/env python3
"""Bounded post-run checking, excluded from timed solver measurements."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


class InputChecks:
    def __init__(self):
        self.seen = {}
        self.bytes_hashed = 0

    @staticmethod
    def identity(path):
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns

    def check(self, path, expected):
        path = Path(path).resolve()
        before = self.identity(path)
        if path in self.seen:
            if self.seen[path] != (expected, before):
                raise ValueError(f'Input changed after validation: {path}')
            return
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                digest.update(block)
                self.bytes_hashed += len(block)
        if self.identity(path) != before or digest.hexdigest() != expected:
            raise ValueError(f'Input checksum mismatch or mutation: {path}')
        self.seen[path] = expected, before

    def unchanged(self):
        for path, (_, identity) in self.seen.items():
            if self.identity(path) != identity:
                raise ValueError(f'Input changed after validation: {path}')


def read_json(path, max_bytes=None):
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise ValueError(f'Validation metadata exceeds {max_bytes} bytes: {path}')
    with path.open() as stream:
        return json.load(stream)


def validate(request):
    if request.get('mode') == 'rust-original-v1':
        from rust_original_validation import validate as validate_rust_original
        return validate_rust_original(request)
    if request.get('mode') not in (None, 'python-original-v1'):
        raise ValueError('Unknown original-input validation mode')
    from benchmark import verify
    query = request['query']
    corpus, artifacts, log = (Path(request[key]) for key in ('corpus', 'artifacts', 'log'))
    if request['exit_code'] != 0:
        raise ValueError(f'Frontend exit code {request["exit_code"]}')
    summary = read_json(log, request['response_bytes'])
    expected = dict(property_id=query['property_id'], kind=query['kind'], branch_count=len(query['branches']))
    if any(summary.get(k) != v for k, v in expected.items()):
        raise ValueError('Frontend property identity, polarity or branch count mismatch')
    if read_json(artifacts/'translation.json', request['response_bytes']) != expected:
        raise ValueError('Frontend translation metadata mismatch')
    attempts = summary['attempts']
    if not isinstance(attempts, list) or len(attempts) > len(query['branches']) or [a['branch'] for a in attempts] != list(range(len(attempts))):
        raise ValueError('Invalid attempted branch sequence')
    checks, branches, verdicts = [], [], []
    hashes = InputChecks()
    for index, branch in enumerate(query['branches']):
        path = corpus/branch['path']
        hashes.check(path, branch['sha256'])
        problem = read_json(path)
        generated = read_json(artifacts/f'branch-{index}.json')
        if generated != problem:
            raise ValueError(f'Original-input translation disagrees with canonical branch {index}')
        del generated
        if index < len(attempts):
            attempt = attempts[index]
            branch_result = dict(attempt, verdict='unknown')
            if not attempt['outer_timeout']:
                if attempt['exit_code'] != 0:
                    raise ValueError(f'Branch {index} exit code {attempt["exit_code"]}')
                answer = read_json(artifacts/f'answer-{index}.json')
                verdict = answer['verdict']
                if verdict not in ('reachable', 'unreachable', 'unknown'):
                    raise ValueError(f'Invalid verdict {verdict}')
                check = verify(problem, answer)
                checks.append(check)
                branch_result.update(independent_check=check, engine=answer['method'])
                if verdict != 'unknown' and not check.startswith('python-'):
                    branch_result['unchecked_verdict'] = verdict
                    verdict = 'unknown'
                branch_result['verdict'] = verdict
                del answer
            verdicts.append(branch_result['verdict'])
            branches.append(branch_result)
        del problem
    if len(attempts) < len(query['branches']):
        verdicts.append('unknown')
    verdict = ('reachable' if 'reachable' in verdicts else
               'unreachable' if all(v == 'unreachable' for v in verdicts) else 'unknown')
    return dict(verdict=verdict, independent_checks=checks, branches=branches,
                translation_check='all-canonical-branches-equal')


def run_validation(query, corpus, artifacts, log, exit_code, args, *, mode=None, outer_timeout=False):
    from process_runner import run
    request_path = log.with_name(log.name+'.validation-request.json')
    response_path = log.with_name(log.name+'.validation-response.json')
    validation_log = log.with_name(log.name+'.validation.log')
    request = dict(query=query, corpus=str(corpus), artifacts=str(artifacts), log=str(log),
                   mode=mode, outer_timeout=outer_timeout,
                   exit_code=exit_code, memory_bytes=args.validation_memory_mib*1024**2,
                   response_bytes=args.validation_response_mib*1024**2)
    request_path.write_text(json.dumps(request)+'\n')
    wall, code, expired, resources = run(
        [str(args.native_python), str(Path(__file__).resolve()), '--request', str(request_path),
         '--response', str(response_path)], Path(__file__).resolve().parents[1],
        args.validation_seconds, validation_log, request['memory_bytes'])
    details = dict(wall_seconds=wall, exit_code=code, outer_timeout=expired, resources=resources,
                   seconds_limit=args.validation_seconds, memory_limit_bytes=request['memory_bytes'],
                   response_limit_bytes=request['response_bytes'], included_in_solver_timing=False)
    if expired or code != 0:
        reason = ('memory-limit' if resources.get('memory_limit_exceeded') else
                  'timeout' if expired else 'worker-failure')
        return dict(verdict='unknown', validation=details, validation_failure=reason,
                    failure_stage='validation', independent_checks=[], branches=[])
    try:
        answer = read_json(response_path, request['response_bytes'])
        if answer.get('verdict') not in ('reachable', 'unreachable', 'unknown', 'error'):
            raise ValueError('Invalid validator response')
        answer['validation'] = details
        return answer
    except (OSError, ValueError) as error:
        return dict(verdict='error', validation=details, failure_stage='validation',
                    error=f'Invalid validator response: {error}', independent_checks=[], branches=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--response', type=Path, required=True)
    args = parser.parse_args()
    request = read_json(args.request, 8*1024**2)
    import resource
    if sys.platform == 'linux':
        resource.setrlimit(resource.RLIMIT_AS, (request['memory_bytes'], request['memory_bytes']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (request['response_bytes'], request['response_bytes']))
    try:
        result = validate(request)
    except MemoryError:
        result = dict(verdict='unknown', validation_failure='memory-limit', failure_stage='validation',
                      independent_checks=[], branches=[])
    except Exception as error:
        result = dict(verdict='error', error=f'{type(error).__name__}: {error}', failure_stage='validation',
                      independent_checks=[], branches=[])
    encoded = json.dumps(result)
    if len(encoded.encode())+1 > request['response_bytes']:
        result = dict(verdict='unknown', validation_failure='response-limit', failure_stage='validation',
                      independent_checks=[], branches=[])
    args.response.write_text(json.dumps(result)+'\n')


if __name__ == '__main__':
    main()
