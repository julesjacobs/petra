"""Conservative admission of a successful, timely MCC formula result."""
import math
import re

FAILURE = re.compile(
    r'Traceback \(most recent call last\):|\b(?:[A-Za-z]+Exception|Exception in thread)\b'
    r'|\bCANNOT_COMPUTE\b|\boverflow\b|\bunsupported\b|\bnot supported\b'
    r'|command not found|No such file or directory|bad command line'
    r'|\b(?:unknown|unrecognized|invalid) (?:option|argument)\b'
    r'|(?:^|\s)(?:ERROR|FATAL)(?:\s*[:!]|\s*$)|error: 4ti2 failed'
    r'|\b(?:OutOfMemoryError|StackOverflowError|LinkageError|AssertionError)\b',
    re.I,
)


def parse(contents, property_id, kind, code, expired, *, wall=None, seconds=None):
    lines = contents.splitlines()
    formulas = [line for line in lines if re.match(
        r'^FORMULA ' + re.escape(property_id) + r'(?:\s|$)', line)]
    valid = re.compile(r'^FORMULA ' + re.escape(property_id)
                       + r' (TRUE|FALSE)(?:\s+TECHNIQUES(?:\s+.*)?)?\s*$')
    parsed = [valid.fullmatch(line) for line in formulas]
    matches = [match[1] for match in parsed if match is not None]
    failures = sorted(set(line for line in lines if FAILURE.search(line)))
    reasons = []
    if expired:
        reasons.append('outer-timeout')
    if wall is not None and (not math.isfinite(wall) or wall > seconds):
        reasons.append('wall-budget')
    if code != 0:
        reasons.append('nonzero-exit')
    if failures:
        reasons.append('diagnostic-failure')
    if kind not in ('EF', 'AG'):
        reasons.append('unsupported-property-kind')
    if any(match is None for match in parsed):
        reasons.append('malformed-formula-result')
    if len(set(matches)) > 1:
        reasons.append('conflicting-formula-results')
    if not matches:
        reasons.append('missing-formula-result')
    observed = None
    if len(set(matches)) == 1 and kind in ('EF', 'AG'):
        observed = 'reachable' if (matches[0] == 'TRUE') == (kind == 'EF') else 'unreachable'
    return dict(verdict=observed if not reasons else 'unknown',
                observed_verdict=observed, observed_formula_results=matches,
                formula_output=formulas, capability_failures=failures,
                subprocess_error=any(re.search(r'Traceback|Exception|\bERROR\b|\bFATAL\b', line, re.I)
                                     for line in failures),
                admission_failures=reasons)


def admit(result, seconds):
    """Apply the same terminal-status contract before publishing every row."""
    result = dict(result)
    reasons = list(result.get('admission_failures', []))
    if result.get('outer_timeout'):
        reasons.append('outer-timeout')
    wall = result.get('wall_seconds')
    if wall is not None and (not math.isfinite(wall) or wall > seconds):
        reasons.append('wall-budget')
    if result.get('exit_code', 0) != 0:
        reasons.append('nonzero-exit')
    if result.get('subprocess_error') or result.get('capability_failures'):
        reasons.append('diagnostic-failure')
    if (result.get('resources') or {}).get('memory_limit_exceeded'):
        reasons.append('memory-limit')
    if result.get('verdict') not in ('reachable', 'unreachable', 'unknown'):
        reasons.append('nondefinitive-failure')
    if reasons:
        result.setdefault('observed_verdict', result.get('verdict'))
        result['verdict'] = 'unknown'
        result['property_truth'] = None
    result['admission_failures'] = sorted(set(reasons))
    return result
