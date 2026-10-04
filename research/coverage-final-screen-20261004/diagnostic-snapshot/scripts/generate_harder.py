#!/usr/bin/env python3
"""Generate finite-data SER families; concurrency/request multiplicity is unbounded."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def request(name, lines):
    return 'request ' + name + ' {\n    ' + ';\n    '.join(lines) + '\n}\n'


def lock(lines, enabled):
    if not enabled:
        return lines
    return ['while (Lock == 1) { yield }', 'Lock := 1'] + lines[:-1] + ['answer := ' + lines[-1], 'Lock := 0', 'answer']


def pause(stages):
    return [f'stage := {stages}', 'while (!(stage == 0)) { yield; stage := stage - 1 }']


def counter(domain, stages, safe):
    programs = []
    for name, update in [
        ('incr', f'if (saved == {domain - 1}) {{ X := 0 }} else {{ X := saved + 1 }}'),
    ]:
        programs.append(request(name, lock(['saved := X'] + pause(stages) + [update, 'X'], safe)))
    return '\n'.join(programs)


def replicas(cells, safe):
    names = [f'Cell{i}' for i in range(cells)]
    write = [f'value := 1 - {names[0]}']
    for i, name in enumerate(names):
        if i:
            write.append('yield')
        write.append(f'{name} := value')
    write.append('value')
    read = [' + '.join(name for i, name in enumerate(names) for _ in range(2**i))]
    return request('write', lock(write, safe)) + '\n' + request('read', lock(read, safe))


def monitor(domain, cycles):
    advance = [f'if (Phase == {domain - 1}) {{ Phase := 0 }} else {{ Phase := Phase + 1 }}', '0']
    wait = [f'while (!(Phase == {phase})) {{ yield }}' for phase in list(range(1, domain)) + [0]]
    observe = [f'remaining := {cycles}', 'while (!(remaining == 0)) { ' + '; '.join(wait + ['remaining := remaining - 1']) + ' }', '100']
    return request('advance', advance) + '\n' + request('observe', observe)


def cases(scaling=False):
    if scaling:
        for safe in [False, True]:
            yield ("counter_d31_s16_"+("locked" if safe else "racy"), "cyclic-counter", dict(domain=31,stages=16,locked=safe), safe, counter(31,16,safe), "lock-linearization" if safe else "two-increments-return-one")
            yield ("replicas_n8_"+("locked" if safe else "racy"), "replicated-register", dict(cells=8,locked=safe), safe, replicas(8,safe), "lock-linearization" if safe else "read-torn-write")
        for domain,cycles in [(4,32),(5,64)]:
            yield (f"monitor_d{domain}_c{cycles}", "phase-monitor", dict(domain=domain,cycles=cycles), False, monitor(domain,cycles), "observe-completes-only-with-interleaved-advances")
        return

    for domain, stages in [(3, 1), (5, 2), (7, 3), (17, 8)]:
        for safe in [False, True]:
            yield (f'counter_d{domain}_s{stages}_' + ('locked' if safe else 'racy'), 'cyclic-counter',
                   dict(domain=domain, stages=stages, locked=safe), safe, counter(domain, stages, safe),
                   'lock-linearization' if safe else 'two-increments-return-one')
    for cells in [2, 3, 4, 6]:
        for safe in [False, True]:
            yield (f'replicas_n{cells}_' + ('locked' if safe else 'racy'), 'replicated-register',
                   dict(cells=cells, locked=safe), safe, replicas(cells, safe),
                   'lock-linearization' if safe else 'read-torn-write')
    for domain in [2, 3]:
        for cycles in [2, 4, 6]:
            yield (f'monitor_d{domain}_c{cycles}', 'phase-monitor', dict(domain=domain, cycles=cycles), False,
                   monitor(domain, cycles), 'observe-completes-only-with-interleaved-advances')

    for domain, cycles in [(3, 12), (4, 12)]:
        yield (f'monitor_d{domain}_c{cycles}', 'phase-monitor', dict(domain=domain, cycles=cycles), False,
               monitor(domain, cycles), 'observe-completes-only-with-interleaved-advances')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scaling', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks/harder-programs')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, family, parameters, serializable, source, argument in cases(args.scaling):
        path = args.output / (name + '.ser')
        path.write_text(source)
        manifest.append(dict(name=name, source=path.name, family=family, parameters=parameters,
                             expected_serializable=serializable, argument=argument,
                             expectation_basis='semantic argument; see research/harder-programs.md',
                             sha256=hashlib.sha256(source.encode()).hexdigest()))
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Generated {len(manifest)} programs in {args.output}')


if __name__ == '__main__':
    main()
