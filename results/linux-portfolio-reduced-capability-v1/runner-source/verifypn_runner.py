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


def parse_output(contents, property_id, kind, code, expired):
    if kind not in ('EF', 'AG'):
        raise ValueError(f'Unsupported property kind: {kind}')
    lines = re.findall(r'^FORMULA ' + re.escape(property_id)
                       + r' (TRUE|FALSE)(?:\s|$)', contents, re.M)
    if len(set(lines)) > 1:
        return 'error'
    if lines:
        truth = lines[0] == 'TRUE'
        return 'reachable' if truth == (kind == 'EF') else 'unreachable'
    if code and not expired:
        return 'error'
    return 'unknown'


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
    index = query_index(xml, query['property_id'])
    command = [str(args.verifypn_binary), *MODES[method], '-x', str(index),
               str(corpus/query['pnml']), str(xml)]
    grace = 0 if args.outer_grace is None else args.outer_grace
    wall, code, expired, usage = execute(command, args.verifypn_root,
                                        args.seconds + grace, log, args)
    contents = log.read_text()
    verdict = parse_output(contents, query['property_id'], query['kind'], code, expired)
    if expired and getattr(args, 'linux_cpus', None):
        verdict = 'unknown'
    return dict(verdict=verdict, wall_seconds=wall, exit_code=code,
                outer_timeout=expired, resources=usage, command=command,
                formula_output=[line for line in contents.splitlines()
                                if line.startswith('FORMULA ' + query['property_id'] + ' ')],
                independent_checks=['none-external-verifypn'])
