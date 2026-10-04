import unittest
from unittest import mock
import test_rust_original_validation as original
from benchmark_smpt_classic import configure_original_modes, rust_original


class GeometricScopeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = original.RustOriginalTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.args = self.fixture.args
        self.args.methods = ['before', 'after']
        self.args.rust_original_method = []
        self.args.bounded_validation = True
        self.args.geometric_branches_method = ['after']

    def test_only_selected_native_invocation_receives_the_flag(self):
        configure_original_modes(self.args)
        query = self.fixture.inputs()
        for method in self.args.methods:
            with mock.patch('benchmark_smpt_classic.execute', return_value=(4, 0, True, {})) as execute:
                rust_original(query, self.fixture.root, self.fixture.root, method, 0, self.args)
            self.assertEqual('--geometric-branches' in execute.call_args.args[0], method == 'after')

    def test_rejects_competitors_absent_labels_and_non_original_input(self):
        for label in ['missing', 'smpt-full-portable', 'verifypn-default']:
            self.args.geometric_branches_method = [label]
            with self.subTest(label=label), self.assertRaises(ValueError):
                configure_original_modes(self.args)
        self.args.geometric_branches_method = ['after']
        self.args.rust_original = False
        self.args.native_original = True
        with self.assertRaises(ValueError):
            configure_original_modes(self.args)


if __name__ == '__main__':
    unittest.main()
