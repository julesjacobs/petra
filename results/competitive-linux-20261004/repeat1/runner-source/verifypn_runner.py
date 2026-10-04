"""Single-property TAPAAL VerifyPN adapter; external verdicts are not proof checked."""
import hashlib
import re
import subprocess

from smpt_import import xml_tree

MODES = {
    "verifypn": ["--trace"],
    "verifypn-default": [],
}


def query_index(path, property_id):
    root = xml_tree(path)
    if root.tag != 'property-set':
        raise ValueError('Expected property-set')
    matches = [i for i, prop in enumerate(root, 1)
               if prop.tag == 'property' and prop.findtext('id') == property_id]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one property named {property_id}')
    return matches[0]


def check_single_property(path, property_id):
    root = xml_tree(path)
    if (root.tag != 'property-set' or len(root) != 1
            or root[0].tag != 'property' or root[0].findtext('id') != property_id):
        raise ValueError('Competitive original input must contain exactly the requested property')


def parse_output(contents, property_id, kind, code, expired):
    from external_verdict import parse
    return parse(contents, property_id, kind, code, expired)['verdict']


def provenance(binary, source, methods=("verifypn",)):
    configurations = {method: MODES[method] for method in methods}
    version = subprocess.run([str(binary), '--version'], capture_output=True,
                             text=True, timeout=10, check=True)
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    status = subprocess.check_output(
        ['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True)
    return dict(binary=str(binary), binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                source=str(source), source_commit=commit, source_status=status,
                version=version.stdout + version.stderr,
                configurations=configurations,
                configuration='Single-property invocations; verifypn requests trace reconstruction (disabling H/J/R/S/Q reductions), verifypn-default uses unrestricted defaults. Upstream MCC scheduling is not used.',
                proof_check='External verdicts are not independently checked.')


def run(query, corpus, output, method, repeat, args, execute):
    log = output/f'{query["name"]}.{method}.{repeat}.log'
    xml = corpus/query['xml']
    command = [str(args.verifypn_binary), *MODES[method], '-x', '1',
               str(corpus/query['pnml']), str(xml)]
    grace = 0 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, args.verifypn_root,
                                        args.seconds + grace, log, args)
    contents = log.read_text()
    from external_verdict import parse
    parsed = parse(contents, query['property_id'], query['kind'], code, expired,
                   wall=wall, seconds=args.seconds)
    return dict(**parsed, wall_seconds=wall, exit_code=code,
                outer_timeout=expired or wall > args.seconds, resources=usage, command=command,
                query_selection='single-property input checked in common preflight; -x 1',
                independent_checks=['none-external-verifypn'])
