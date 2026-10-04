import itertools
import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from generate_boolean_nets import encode, pigeonhole, pnml_text, property_text, random_cnf
from smpt_import import pnml, properties


def exhaustive_reachable(model):
    initial = tuple(model['initial'])
    seen, todo = {initial}, [initial]
    target = model['target'][0]['coefficients'].index(1)
    while todo:
        marking = todo.pop()
        if marking[target]:
            return True
        for transition in model['transitions']:
            if all(marking[p] >= weight for p, weight in transition['pre']):
                successor = list(marking)
                for p, weight in transition['pre']:
                    successor[p] -= weight
                for p, weight in transition['post']:
                    successor[p] += weight
                assert all(x in (0, 1) for x in successor)
                successor = tuple(successor)
                if successor not in seen:
                    seen.add(successor)
                    todo.append(successor)
    return False


def satisfiable(variables, clauses):
    return any(all(any(assignment[abs(lit) - 1] == (lit > 0) for lit in clause)
                   for clause in clauses)
               for assignment in itertools.product((False, True), repeat=variables))


class EncodingTests(unittest.TestCase):
    def test_truth_table_against_full_state_space(self):
        for variables in range(3, 7):
            for seed in range(10):
                count = 8 if variables == 3 else variables * 4
                formula = random_cnf(variables, count, seed)
                self.assertEqual(exhaustive_reachable(encode(variables, formula)),
                                 satisfiable(variables, formula))

    def test_pigeonhole_both_polarities(self):
        for holes in (1, 2, 3):
            for extra in (0, 1):
                formula = pigeonhole(holes + extra, holes)
                self.assertEqual(exhaustive_reachable(encode((holes + extra) * holes, formula)),
                                 not extra)

    def test_pnml_xml_roundtrip(self):
        model = encode(3, [[1, -2], [2, 3], [-1]])
        self.assertEqual([child.tag for child in ET.fromstring(property_text(3))[0]],
                         ['id', 'description', 'formula'])
        namespace = '{http://www.pnml.org/version-2009/grammar/pnml}'
        tree = ET.fromstring(pnml_text(model))
        for tag in ['place', 'transition']:
            nodes = list(tree.iter(namespace + tag))
            self.assertTrue(nodes)
            for node in nodes:
                self.assertEqual(node.findtext(namespace + 'name/' + namespace + 'text'), node.attrib['id'])
        with tempfile.TemporaryDirectory() as temporary:
            net, query = Path(temporary) / 'model.pnml', Path(temporary) / 'property.xml'
            net.write_text(pnml_text(model))
            query.write_text(property_text(3))
            imported = pnml(net)
            imported['target'] = properties(query, imported)[0]['targets'][0]
            self.assertEqual(imported, model)

    def test_source_edge_cases(self):
        self.assertTrue(exhaustive_reachable(encode(1, [])))
        self.assertFalse(exhaustive_reachable(encode(1, [[1], [-1]])))
        for formula in ([[]], [[0]], [[2]]):
            with self.assertRaises(ValueError):
                encode(1, formula)


if __name__ == '__main__':
    unittest.main()
