"""Timed original-input ITS wrapper adapter; external answers remain tool-reported."""
import hashlib
import json
import math
from pathlib import Path

from external_verdict import FAILURE, admit, parse

MODES = {'its-mcc': 'official ITS MCC reachability configuration'}
MAX_LOG_BYTES = 64 * 1024**2


def provenance(config):
    config = Path(config)
    scripts = Path(__file__).resolve().parent
    return dict(runtime_config=str(config),
                runtime_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                runtime=json.loads(config.read_text()),
                wrapper_sha256=hashlib.sha256((scripts/'its_original.py').read_bytes()).hexdigest(),
                adapter_sha256=hashlib.sha256((scripts/'its_adapter.py').read_bytes()).hexdigest(),
                proof_check='External ITS verdicts are not independently proof checked.',
                input_scope='Single-property staging and all runtime startup inside the timed wrapper.')


def run(query, corpus, output, method, repeat, args, execute):
    log = output/f'{query["name"]}.{method}.{repeat}.its-original.json'
    artifacts = output/f'{query["name"]}.{method}.{repeat}.its-artifacts'
    command = [str(args.native_python), str(Path(__file__).resolve().parent/'its_original.py'),
               '--runtime-config', str(args.its_runtime_config),
               '--pnml', str(corpus/query['pnml']), '--xml', str(corpus/query['xml']),
               '--property-id', query['property_id'], '--artifacts', str(artifacts),
               '--seconds', str(args.seconds)]
    grace = 0 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, args.workspace_root,
                                        args.seconds + grace, log, args)
    result = dict(verdict='unknown', wall_seconds=wall, exit_code=code,
                  outer_timeout=expired or wall > args.seconds, resources=usage,
                  command=command, artifacts=str(artifacts),
                  input_mode='its-original', independent_checks=['none-external-its'])
    try:
        if log.stat().st_size > MAX_LOG_BYTES:
            raise ValueError('ITS wrapper output exceeds size limit')
        summary = json.loads(log.read_text())
        if not isinstance(summary, dict):
            raise ValueError('ITS wrapper output is not an object')
        if summary.get('kind') != 'its-original-v1':
            raise ValueError('Invalid ITS wrapper result kind')
        if summary.get('property_id') != query['property_id']:
            raise ValueError('ITS property ID mismatch')
        if summary.get('property_kind') != query['kind']:
            raise ValueError('ITS property kind mismatch')
        for field in ('capability_failures', 'errors'):
            if type(summary.get(field)) is not list or not all(isinstance(line, str) for line in summary[field]):
                raise ValueError(f'Invalid ITS {field}')
        if type(summary.get('timed_out')) is not bool:
            raise ValueError('Invalid ITS timeout flag')
        if summary.get('tool_exit_code') is not None and type(summary['tool_exit_code']) is not int:
            raise ValueError('Invalid ITS tool exit code')
        verdict = summary.get('verdict')
        if verdict not in ('reachable', 'unreachable', 'unknown'):
            raise ValueError('Invalid ITS verdict')
        expected_truth = None if verdict == 'unknown' else ((verdict == 'reachable') == (query['kind'] == 'EF'))
        if summary.get('property_truth') is not expected_truth:
            raise ValueError('ITS property polarity mismatch')
        for field in ('stage_seconds', 'tool_seconds', 'parse_seconds', 'total_seconds'):
            value = summary.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid ITS {field}')
        result.update(verdict=verdict, observed_verdict=verdict, its_summary=summary,
                      formula_output=summary.get('formula_output'),
                      capability_failures=list(summary.get('capability_failures') or []),
                      subprocess_error=bool(summary['errors'] or summary.get('error') or summary.get('subprocess_error')),
                      errors=summary['errors'],
                      tool_exit_code=summary.get('tool_exit_code'))
        reasons = []
        if summary.get('tool_exit_code') != 0:
            reasons.append('tool-nonzero-exit')
        if summary.get('timed_out'):
            reasons.append('tool-timeout')
        if summary['total_seconds'] > args.seconds:
            reasons.append('wrapper-wall-budget')
        if summary.get('error'):
            result['error'] = summary['error']
        result['admission_failures'] = reasons
    except (OSError, ValueError, TypeError) as error:
        result.update(error=str(error), admission_failures=['invalid-wrapper-result'])
    observed_logs = []
    contents = []
    total = 0
    try:
        log_paths = sorted(p for p in artifacts.rglob('*') if p.is_file()
                           and (p.suffix.lower() in ('.log', '.out', '.err') or p.name in ('stdout', 'stderr')))
        for path in log_paths:
            total += path.stat().st_size
            if total > MAX_LOG_BYTES:
                result.setdefault('admission_failures', []).append('underlying-log-size-limit')
                break
            data = path.read_bytes()
            decoded = data.decode('utf-8', errors='replace')
            contents.append(decoded)
            failures = [line for line in decoded.splitlines() if FAILURE.search(line)]
            observed_logs.append(dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
            if failures:
                result.setdefault('capability_failures', []).extend(failures)
    except OSError as error:
        result.setdefault('admission_failures', []).append('unreadable-underlying-tool-log')
        result['underlying_log_error'] = str(error)
    result['underlying_logs'] = observed_logs
    if not observed_logs:
        result.setdefault('admission_failures', []).append('missing-underlying-tool-log')
    parsed = parse('\n'.join(contents), query['property_id'], query['kind'],
                   result.get('tool_exit_code'), expired, wall=wall, seconds=args.seconds)
    result['observed_formula_results'] = parsed['observed_formula_results']
    result['formula_output'] = parsed['formula_output']
    result.setdefault('admission_failures', []).extend(parsed['admission_failures'])
    if result['verdict'] in ('reachable', 'unreachable') and result['verdict'] != parsed['verdict']:
        result['admission_failures'].append('wrapper-tool-verdict-mismatch')
    return admit(result, args.seconds)
