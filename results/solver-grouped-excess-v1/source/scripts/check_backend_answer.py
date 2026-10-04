"""Bounded-worker entry point for the existing independent backend verifier."""
import argparse
import json
from pathlib import Path
from benchmark import verify


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('problem',type=Path);parser.add_argument('answer',type=Path)
    args=parser.parse_args()
    result=verify(json.loads(args.problem.read_text()),json.loads(args.answer.read_text()))
    if not result or result.startswith('none'):
        raise ValueError('No independently checked answer: '+str(result))
    print(json.dumps(dict(status='passed',check=result)))


if __name__=='__main__':main()
