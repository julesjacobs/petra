#!/usr/bin/env python3
"""Freeze a fixed transfer-graph ladder without exporting or solving it."""
import argparse
import hashlib
import json
from pathlib import Path

from generate_diverse_ser import request

ROOT = Path(__file__).resolve().parents[1]
SIZES = (4, 6)
TOPOLOGIES = ('path', 'cycle', 'chorded')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def edges(sites, topology):
    if type(sites) is not int or sites not in SIZES or topology not in TOPOLOGIES:
        raise ValueError('Expected four or six sites and path/cycle/chorded topology')
    result = {(i, i + 1) for i in range(sites - 1)}
    if topology != 'path':
        result.add((0, sites - 1))
    if topology == 'chorded':
        result.update((i, i + sites // 2) for i in range(sites // 2))
    return sorted(result)


def acquire(resources):
    return [line for i in sorted(resources)
            for line in [f'while (Lock{i} == 1) {{ yield }}', f'Lock{i} := 1']]


def release(resources):
    return [f'Lock{i} := 0' for i in sorted(resources, reverse=True)]


def program(sites, topology, strict):
    if type(strict) is not bool:
        raise ValueError('strict must be Boolean')
    links = edges(sites, topology)
    programs = [request('seed', [
        f'if (Ready == 0) {{ Occupied0 := 1; Occupied{sites // 2} := 1; Ready := 1 }} else {{ 0 }}', '0'])]
    for a, b in links:
        for source, target in [(a, b), (b, a)]:
            resources = [source, target]
            update = [f'Occupied{source} := 0']
            if not strict:
                update += release(resources)
            update += ['yield']
            if not strict:
                update += acquire(resources)
            update += [f'Occupied{target} := 1', 'moved := 1']
            lines = ['while (Ready == 0) { yield }'] + acquire(resources) + [
                'moved := 0',
                f'if ((Occupied{source} == 1) && (Occupied{target} == 0)) {{ ' + '; '.join(update) + ' } else { 0 }',
            ] + release(resources) + ['moved']
            programs.append(request(f'transfer{source}to{target}', lines))
    programs.append(request('count', ['while (Ready == 0) { yield }'] + acquire(range(sites)) +
                            ['answer := ' + ' + '.join(f'Occupied{i}' for i in range(sites))] +
                            release(range(sites)) + ['answer']))
    return '\n'.join(programs)


def cases():
    for sites in SIZES:
        for topology in TOPOLOGIES:
            for strict in (True, False):
                variant = 'strict' if strict else 'early_release'
                name = f'transfer_n{sites}_{topology}_{variant}'
                counterpart = 'early_release' if strict else 'strict'
                yield dict(name=name, source_text=program(sites, topology, strict),
                           paired_with=f'transfer_n{sites}_{topology}_{counterpart}',
                           family='conserved-resource-transfer',
                           parameters=dict(sites=sites, topology=topology, strict=strict,
                                           initial_occupied=[0, sites // 2], undirected_edges=edges(sites, topology)),
                           feasibility_bridge=sites == 4,
                           structural_parameters=dict(request_types=2 * len(edges(sites, topology)) + 2,
                                                      shared_boolean_variables=2 * sites + 1,
                                                      global_valuation_upper_bound=2 ** (2 * sites + 1)),
                           serializable=strict,
                           argument='ordered-strict-two-phase-locking' if strict else 'count-observes-in-flight-debit')


def artifacts():
    files, records = {}, []
    for case in cases():
        data = case.pop('source_text').encode()
        serializable = case.pop('serializable')
        argument = case.pop('argument')
        source = case['name'] + '.ser'
        files[source] = data
        records.append(dict(**case, source=source, sha256=digest(data), bytes=len(data),
                            role='new-mechanism-development-case', exact_source_overlaps=[], independent_test=False,
                            source_expectation=dict(serializable=serializable, argument=argument,
                                basis='source-level argument; research/transfer-ser-programs-v2.md', mechanically_verified=False),
                            export_result=None, solver_result=None))
    provenance = []
    for name in ['scripts/generate_transfer_ser_v2.py', 'scripts/generate_diverse_ser.py',
                 'scripts/test_generate_transfer_ser_v2.py', 'research/transfer-ser-programs-v2.md',
                 'vendor/SerializabilityChecker/src/parser.rs']:
        provenance.append(dict(path=name, sha256=digest((ROOT / name).read_bytes())))
    manifest = dict(format='ser-stress-sources-v1', version=1, corpus='transfer-ser-programs-v2',
                    counts=dict(sources=12, expected_serializable=6, expected_nonserializable=6,
                                four_slot_feasibility_bridges=6, six_slot_cases=6),
                    selection='Fixed4/6-slot x path/cycle/chorded x strict/early-release ladder before export or solving; retain all12.',
                    provenance=provenance, cases=records,
                    limitations=['Source expectations are arguments, not solver ground truth or exported-net proofs.',
                                 'Finite-model tests do not interpret SER or prove unbounded-request behavior.',
                                 'Four-slot bridges are new sources, not duplicates of a previously frozen corpus.',
                                 'Difficulty and export feasibility are unmeasured; global data bounds do not bound export size polynomially.',
                                 'All12 sources, including export/resource failures, remain in the denominator.',
                                 'Correlated development cases; no reserved evaluation families.'])
    files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    files['SHA256SUMS'] = ''.join(f'{digest(data)}  {name}\n' for name, data in sorted(files.items())).encode()
    return files


def freeze(output):
    files = artifacts()
    if output.exists():
        if {p.name for p in output.iterdir()} != set(files) or any(
            not (output / name).is_file() or (output / name).read_bytes() != data for name, data in files.items()
        ):
            raise ValueError('Existing output differs; use a new directory to preserve frozen inputs.')
        return False
    output.mkdir(parents=True)
    for name, data in files.items():
        (output / name).write_bytes(data)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks/transfer-ser-programs-v2')
    args = parser.parse_args()
    try:
        created = freeze(args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"{'Frozen' if created else 'Verified unchanged'} 12 sources: {args.output}")


if __name__ == '__main__':
    main()
