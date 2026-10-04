"""Stage one original MCC property and invoke the pinned official ITS portfolio."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from its_adapter import local_name, parse_result, stage_property


ERROR = re.compile(r'Exception|Traceback|\bERROR\b|error while loading shared libraries|'
                   r'command not found|No such file or directory|Cannot run program|'
                   r'Unexpected XML tag|OutOfMemory|overflow', re.IGNORECASE)


def capability_failures(model, properties):
    failures = []
    for path, tags in [(model, {'initialMarking', 'inscription'}),
                       (properties, {'integer-constant'})]:
        root = ET.parse(path).getroot()
        for element in root.iter():
            if local_name(element) not in tags:
                continue
            values = [element] if local_name(element) == 'integer-constant' else [
                child for child in element.iter() if local_name(child) == 'text']
            for value in values:
                number = int((value.text or '').strip())
                if not -(2**31) <= number < 2**31:
                    failures.append('integer-outside-signed-32-bit')
    def constant(element):
        tag = local_name(element)
        if tag == 'integer-constant':
            return int(element.text.strip())
        if tag in ('sum', 'product'):
            values = [constant(child) for child in element]
            if all(value is not None for value in values):
                value = sum(values) if tag == 'sum' else math.prod(values)
                if not -(2**31) <= value < 2**31:
                    failures.append('constant-arithmetic-outside-signed-32-bit')
                return value
        return None
    for element in ET.parse(properties).getroot().iter():
        constant(element)
    return sorted(set(failures))


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-config', type=Path, required=True)
    parser.add_argument('--pnml', type=Path, required=True)
    parser.add_argument('--xml', type=Path, required=True)
    parser.add_argument('--property-id', required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seconds', type=float, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('--seconds must be finite and positive')
    folder = args.artifacts.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / 'its-tool.log'
    result = dict(kind='its-original-v1', property_id=args.property_id,
                  property_kind=None, property_truth=None, verdict='unknown',
                  tool_exit_code=None, timed_out=False, capability_failures=[],
                  errors=[], tool_log=str(log), stage_seconds=None,
                  tool_seconds=0.0, parse_seconds=0.0, total_seconds=None,
                  evidence='external-reported')
    try:
        config = json.loads(args.runtime_config.read_text())
        stage = folder / 'input'
        result.update(stage_property(args.pnml, args.xml, args.property_id, stage))
        result['property_kind'] = result.pop('kind')
        result['kind'] = 'its-original-v1'
        result['capability_failures'] = capability_failures(stage / 'model.pnml', stage / 'ReachabilityCardinality.xml')
        result['stage_seconds'] = time.perf_counter() - start
        if result['capability_failures']:
            result['reason'] = 'unsupported-integer-range'
        else:
            environment = dict(os.environ, BK_EXAMINATION='ReachabilityCardinality',
                               BK_BIN_PATH=str(Path(config['installation']) / 'bin'),
                               BK_INPUT=str(stage),
                               BK_TIME_CONFINEMENT=str(max(1, math.ceil(args.seconds - result['stage_seconds']))),
                               JAVA_HOME=config['java_home'])
            environment.update(config.get('environment', {}))
            environment['PATH'] = str(Path(config['java_home']) / 'bin') + ':' + environment.get('PATH', '')
            command = ['bash', str(Path(config['installation']) / 'BenchKit_head.sh')]
            result['command'] = command
            result['runtime_config'] = str(args.runtime_config.resolve())
            result['tool_environment'] = {key: environment[key] for key in ['BK_EXAMINATION', 'BK_BIN_PATH', 'BK_INPUT', 'BK_TIME_CONFINEMENT', 'JAVA_HOME', 'PATH', *config.get('environment', {})]}
            before = time.perf_counter()
            with log.open('x') as stream:
                process = subprocess.run(command, cwd=stage, env=environment,
                                         stdout=stream, stderr=subprocess.STDOUT)
            result['tool_seconds'] = time.perf_counter() - before
            result['tool_exit_code'] = process.returncode
            before = time.perf_counter()
            output = log.read_text(errors='replace')
            result.update(parse_result(output, args.property_id, result['property_kind'], process.returncode))
            result['errors'] = [line for line in output.splitlines() if ERROR.search(line)]
            if result['errors']:
                result.update(verdict='unknown', property_truth=None, reason='tool-error')
            result['parse_seconds'] = time.perf_counter() - before
    except Exception as error:
        result.update(verdict='unknown', property_truth=None, reason='wrapper-error')
        result['errors'].append(f'{type(error).__name__}: {error}')
    result['total_seconds'] = time.perf_counter() - start
    if result['total_seconds'] > args.seconds:
        result.update(verdict='unknown', property_truth=None, timed_out=True, reason='wrapper-deadline')
    (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
