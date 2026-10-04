"""Single-property input staging and conservative MCC result parsing for ITS."""

import copy
import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def local_name(element):
    return element.tag.rsplit('}', 1)[-1]


def stage_property(model, properties, property_id, destination):
    """Stage unchanged PNML and one EF/AG property in a fresh directory."""
    if not property_id or any(c.isspace() for c in property_id):
        raise ValueError('MCC result identifiers must be nonempty and whitespace-free')
    root = ET.fromstring(Path(properties).read_bytes())
    if local_name(root) != 'property-set':
        raise ValueError('expected property-set')
    selected = []
    for prop in root:
        if local_name(prop) != 'property':
            raise ValueError('unexpected property-set child')
        ids = [e for e in prop if local_name(e) == 'id']
        if len(ids) != 1 or ids[0].text is None:
            raise ValueError('property must have exactly one id')
        if ids[0].text.strip() == property_id:
            selected.append(prop)
    if len(selected) != 1:
        raise ValueError('requested property must occur exactly once')
    prop = selected[0]
    formulas = [e for e in prop if local_name(e) == 'formula']
    if len(formulas) != 1 or len(formulas[0]) != 1:
        raise ValueError('expected one formula')
    outer = formulas[0][0]
    if len(outer) != 1:
        raise ValueError('expected EF or AG formula')
    shape = (local_name(outer), local_name(outer[0]))
    kind = {('exists-path', 'finally'): 'EF', ('all-paths', 'globally'): 'AG'}.get(shape)
    if kind is None or len(outer[0]) != 1:
        raise ValueError('expected EF or AG formula')
    staged = copy.deepcopy(root)
    for child in list(staged):
        staged.remove(child)
    staged.append(copy.deepcopy(prop))
    # ITS SAX compares unprefixed element names; preserve the default namespace.
    if root.tag.startswith('{'):
        ET.register_namespace('', root.tag[1:].split('}', 1)[0])
    xml = ET.tostring(staged, encoding='utf-8', xml_declaration=True)
    pnml = Path(model).read_bytes()
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=False)
    (dest / 'model.pnml').write_bytes(pnml)
    (dest / 'ReachabilityCardinality.xml').write_bytes(xml)
    return dict(property_id=property_id, kind=kind,
                model_sha256=hashlib.sha256(pnml).hexdigest(),
                original_properties_sha256=hashlib.sha256(Path(properties).read_bytes()).hexdigest(),
                staged_properties_sha256=hashlib.sha256(xml).hexdigest())


def parse_result(output, property_id, kind, exit_code, timed_out=False):
    """Return external-reported truth only for a clean, consistent exact-ID result."""
    if kind not in ('EF', 'AG'):
        raise ValueError('expected EF or AG')
    prefix = re.compile(r'^FORMULA\s+' + re.escape(property_id) + r'(?:\s|$)')
    valid = re.compile(r'^FORMULA\s+' + re.escape(property_id)
                       + r'\s+(TRUE|FALSE)(?:\s+TECHNIQUES(?:\s+.*)?)?\s*$')
    lines = [line for line in output.splitlines() if prefix.match(line)]
    matches = [valid.fullmatch(line) for line in lines]
    truth = {m[1] for m in matches if m is not None}
    reason = ('conflicting-verdicts' if len(truth) > 1 else
              'malformed-result' if any(m is None for m in matches) else
              'timeout' if timed_out else
              'nonzero-exit' if exit_code != 0 else
              'missing-result' if not truth else None)
    result = dict(verdict='unknown', property_truth=None, reason=reason,
                  formula_output=lines, evidence='external-reported')
    if reason is None:
        value = truth == {'TRUE'}
        result.update(property_truth=value,
                      verdict='reachable' if value == (kind == 'EF') else 'unreachable')
    return result
