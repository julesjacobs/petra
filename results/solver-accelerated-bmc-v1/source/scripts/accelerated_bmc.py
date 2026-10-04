#!/usr/bin/env python3
"""Experimental Rust/Z3 accelerated BMC with one whole-query deadline."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def solve(args, directory):
    started = time.monotonic()
    deadline = started + args.seconds
    stages = []
    depths = []
    discovery = None

    def answer(verdict, reason, **extra):
        return dict(verdict=verdict, reason=reason, mode=args.mode,
                    wall_seconds=time.monotonic()-started, depths=depths,
                    stages=stages, discovery=discovery, **extra)

    def run(command, label, maximum_bytes=16*1024*1024):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('whole-query deadline')
        output, error = directory/(label+'.stdout'), directory/(label+'.stderr')
        phase = time.monotonic()
        with output.open('xb') as out, error.open('xb') as err:
            try:
                completed = subprocess.run(command, stdout=out, stderr=err, timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                stages.append(dict(label=label, seconds=time.monotonic()-phase, timeout=True))
                raise TimeoutError(label+' deadline') from exc
        stages.append(dict(label=label, seconds=time.monotonic()-phase, exit_code=completed.returncode))
        if output.stat().st_size > maximum_bytes or error.stat().st_size > maximum_bytes:
            raise ValueError(label+' output limit')
        if time.monotonic() >= deadline:
            raise TimeoutError(label+' deadline')
        return completed.returncode, output, error

    try:
        problem = json.loads(args.problem.read_text())
        words = [[t] for t in range(len(problem['transitions']))]
        if args.mode == 'cycles':
            code, output, error = run([str(args.binary), 'discover', str(args.problem),
                                      str(args.word_length), str(args.extra_words), str(args.discovery_work)], 'discovery')
            if code:
                return answer('unknown', 'discovery failure', failure=error.read_text()[-2000:])
            discovery = json.loads(output.read_text())
            words = discovery['words']
        word_path = directory/'words.json'
        word_path.write_text(json.dumps(words))
        bounds = [0]
        depth = 1
        while depth < args.depth_limit:
            bounds.append(depth)
            depth *= 2
        if args.depth_limit:
            bounds.append(args.depth_limit)
        summary_cells = len(words)*len(problem['places'])
        word_arcs = sum(len(problem['transitions'][t]['pre'])+len(problem['transitions'][t]['post']) for word in words for t in word)
        for depth in bounds:
            if depth and summary_cells > args.encoding_cells:
                return answer('unknown', 'summary cell limit', requested_cells=summary_cells)
            cells = (depth+1)*len(problem['places']) + depth*(len(words)+2*word_arcs)
            if cells > args.encoding_cells:
                return answer('unknown', 'encoding cell limit', requested_cells=cells)
            if depth and not words:
                break
            depths.append(depth)
            mode = 'emit-bmc' if args.mode == 'ordinary' else 'emit'
            command = [str(args.binary), mode, str(args.problem), str(word_path), str(depth)]
            code, formula, error = run(command, f'encode-{depth}', args.formula_bytes)
            if code:
                return answer('unknown', 'encoding failure', failure=error.read_text()[-2000:])
            code, model, error = run([str(args.z3), '-smt2', str(formula), '-T:'+str(max(1,math.ceil(deadline-time.monotonic())))], f'z3-{depth}')
            output = model.read_text()
            status = output.splitlines()[0] if output else ''
            if status == 'sat' and code == 0:
                command[1] = 'check'; command.append(str(model))
                code, checked, error = run(command, f'check-{depth}')
                if code:
                    return answer('unknown', 'witness check failure', failure=error.read_text()[-2000:])
                result = json.loads(checked.read_text())
                if result.get('verdict') != 'reachable':
                    return answer('unknown', 'missing checked witness')
                return answer('reachable', 'checked compressed witness', segments=result['segments'], marking=result['marking'])
            if status != 'unsat':
                return answer('unknown', 'SMT '+(status or 'failure'), solver_exit_code=code, failure=error.read_text()[-2000:])
            # get-value after UNSAT causes Z3 to exit 1; no other error is accepted.
            expected = 'unsat\n' if depth==0 else 'unsat\n(error "line '
            if code not in (0,1) or not output.startswith(expected) or (code==1 and 'model is not available' not in output):
                return answer('unknown', 'SMT error after UNSAT', solver_exit_code=code)
        return answer('unknown', 'bounded schemes exhausted')
    except (TimeoutError, ValueError, OSError) as error:
        return answer('unknown', str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--problem', type=Path, required=True)
    parser.add_argument('--mode', choices=['ordinary','singleton','cycles'], default='cycles')
    parser.add_argument('--binary', type=Path, default=ROOT/'target/release/examples/accelerated_bmc')
    parser.add_argument('--z3', type=Path, default=ROOT/'vendor/venv/bin/z3')
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--depth-limit', type=int, default=16)
    parser.add_argument('--word-length', type=int, default=8)
    parser.add_argument('--extra-words', type=int, default=128)
    parser.add_argument('--discovery-work', type=int, default=2_000_000)
    parser.add_argument('--encoding-cells', type=int, default=200_000)
    parser.add_argument('--formula-bytes', type=int, default=64*1024*1024)
    parser.add_argument('--artifacts', type=Path)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds<=0 or min(args.depth_limit,args.extra_words)<0 or min(args.word_length,args.discovery_work,args.encoding_cells,args.formula_bytes)<=0:
        parser.error('Invalid resource limits')
    args.problem=args.problem.resolve();args.binary=args.binary.resolve();args.z3=args.z3.resolve()
    if args.artifacts:
        args.artifacts.mkdir(parents=True,exist_ok=False)
        result=solve(args,args.artifacts)
    else:
        with tempfile.TemporaryDirectory(prefix='pvass-abmc-') as folder:
            result=solve(args,Path(folder))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
