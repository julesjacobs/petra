"""Check one saved raw answer; the parent enforces wall and process-tree RSS limits."""
import argparse
import json
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--checker-dir', type=Path, required=True)
parser.add_argument('--query', type=Path, required=True)
parser.add_argument('--answer', type=Path, required=True)
parser.add_argument('--seconds', type=float, required=True)
parser.add_argument('--work', type=int, required=True)
args = parser.parse_args()
started = time.monotonic()
deadline = started + args.seconds
sys.path.insert(0, str(args.checker_dir.resolve()))
from raw_stress_worker import load_json, validate
from raw_schema_check import verify

def record(**fields):
    print(json.dumps(dict(elapsed=time.monotonic() - started, **fields)), flush=True)

try:
    record(stage='query-read')
    query = load_json(args.query)
    validate(query)
    record(stage='proof-read')
    answer = load_json(args.answer)
    if answer.get('verdict') != 'unreachable':
        raise ValueError('expected a negative answer')
    record(stage='independent-verification')
    result = verify(query, answer['proof'], deadline, max_obligations=args.work)
    record(stage='complete', accepted=True, checker=result)
except TimeoutError as error:
    record(stage='complete', accepted=False, status='verification-unknown', reason=str(error))
except Exception as error:
    record(stage='complete', accepted=False, status='rejected-or-error', reason=f'{type(error).__name__}: {error}')
