import pathlib
import tempfile
import unittest
from types import SimpleNamespace

from verifypn_runner import parse_output, query_index, run


class VerifyPNTests(unittest.TestCase):
    def test_default_and_trace_modes_invoke_distinct_configurations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root/'queries.xml').write_text(
                '<property-set><property><id>p</id></property></property-set>')
            args = SimpleNamespace(verifypn_binary=root/'verifypn',
                                   verifypn_root=root, outer_grace=0, seconds=5)
            query = dict(name='q', xml='queries.xml', pnml='net.pnml',
                         property_id='p', kind='EF')
            commands = []

            def execute(command, cwd, seconds, log, options):
                commands.append(command)
                log.write_text('FORMULA p TRUE\n')
                return 0.1, 0, False, {}

            for method in ('verifypn', 'verifypn-default'):
                answer = run(query, root, root, method, 0, args, execute)
                self.assertEqual(answer['verdict'], 'reachable')
            self.assertEqual(commands[0], [str(root/'verifypn'), '--trace',
                                          '-x', '1', str(root/'net.pnml'),
                                          str(root/'queries.xml')])
            self.assertEqual(commands[1], [str(root/'verifypn'), '-x', '1',
                                          str(root/'net.pnml'), str(root/'queries.xml')])

    def test_requested_id_and_polarity(self):
        output = 'FORMULA other TRUE TECHNIQUES EXPLICIT\nFORMULA target.+ FALSE TECHNIQUES EXPLICIT\n'
        self.assertEqual(parse_output(output, 'target.+', 'EF', 0, False), 'unreachable')
        self.assertEqual(parse_output(output, 'target.+', 'AG', 0, False), 'reachable')
        self.assertEqual(parse_output(output, 'target', 'EF', 0, False), 'unknown')
        self.assertEqual(parse_output(output, 'other', 'AG', 0, False), 'unreachable')

    def test_conflicting_answers_are_errors(self):
        output = 'FORMULA p TRUE\nFORMULA p FALSE\n'
        self.assertEqual(parse_output(output, 'p', 'EF', 0, True), 'error')

    def test_timeouts_and_nonzero_exits(self):
        self.assertEqual(parse_output('CANNOT_COMPUTE\n', 'p', 'EF', 0, False), 'unknown')
        self.assertEqual(parse_output('', 'p', 'EF', -9, True), 'unknown')
        self.assertEqual(parse_output('', 'p', 'EF', 1, False), 'error')
        self.assertEqual(parse_output('FORMULA p TRUE\n', 'p', 'EF', -9, True), 'reachable')

    def test_index_is_one_based_and_requires_unique_id(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)/'queries.xml'
            path.write_text('<property-set xmlns="urn:mcc"><property><id>a</id></property>'
                            '<property><id>b</id></property></property-set>')
            self.assertEqual(query_index(path, 'b'), 2)
            with self.assertRaises(ValueError):
                query_index(path, 'missing')
            path.write_text('<property-set><property><id>a</id></property>'
                            '<property><id>a</id></property></property-set>')
            with self.assertRaises(ValueError):
                query_index(path, 'a')


if __name__ == '__main__':
    unittest.main()
