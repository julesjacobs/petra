import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from analyze_instruction_counts import analyze, main, markdown, observations


def environment(properties=('p',), methods=('a', 'b'), repeats=2):
    return dict(property_order=list(properties), methods=list(methods), repeat=repeats,
                queries=len(properties), seconds=5, perf=True, linux_cpus=[2])


def row(query, method, repeat, count=100, verdict='reachable', percent=100):
    return dict(query=query, method=method, repeat=repeat, verdict=verdict,
                property_kind='EF', property_truth=(verdict == 'reachable' if verdict in ('reachable', 'unreachable') else None),
                outer_timeout=False, exit_code=0,
                resources=dict(runner='linux-systemd-user', systemd_result='success',
                               memory_limit_exceeded=False, perf_enabled=True,
                               perf_counters={'instructions:u': dict(value=count, time_running_percent=percent)}))


def matrix(env):
    return [row(q, m, r) for q in env['property_order'] for m in env['methods'] for r in range(env['repeat'])]


class InstructionAnalysisTests(unittest.TestCase):
    def test_median_first_then_geometric_mean_with_explicit_cases(self):
        env = environment(('p', 'q'), repeats=3)
        values = {('p', 'a'): [1, 2, 900], ('p', 'b'): [4, 4, 4],
                  ('q', 'a'): [100, 200, 300], ('q', 'b'): [100, 100, 100]}
        rows = [row(q, m, r, values[q, m][r]) for q in env['property_order']
                for m in env['methods'] for r in range(3)]
        result = analyze(env, rows)
        pair = result['comparisons'][0]
        self.assertEqual((pair['numerator'], pair['denominator']), ('a', 'b'))
        self.assertAlmostEqual(pair['geometric_mean_ratio'], 1)
        self.assertEqual([c['ratio'] for c in pair['cases']], [0.5, 2])
        self.assertEqual([c['query'] for c in pair['cases']], ['p', 'q'])
        self.assertEqual(pair['eligible_properties'], 2)
        variability = result['methods']['a']['instruction_repeat_variability']
        self.assertEqual(variability['maximum_max_over_min'], 900)
        self.assertIn('Numerator median', markdown(result))

    def test_full_matrix_rejects_missing_duplicate_and_unexpected_rows(self):
        env = environment(('p', 'q'))
        rows = matrix(env)
        for broken in (rows[:-1], rows + [rows[0]], rows + [row('other', 'a', 0)],
                       rows + [row('p', 'a', 5)]):
            with self.subTest(rows=len(broken)), self.assertRaises(ValueError):
                analyze(env, broken)
        changed = copy.deepcopy(rows)
        changed[0]['repeat'] = False
        with self.assertRaises(ValueError):
            analyze(env, changed)
        for field, value in [('queries', 3), ('repeat', 0), ('methods', ['a', 'a']),
                             ('property_order', ['p', 'p'])]:
            broken = dict(env, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                analyze(broken, rows)

    def test_timeouts_and_oom_are_counted_and_never_enter_ratios(self):
        env = environment(('timeout', 'oom'))
        rows = matrix(env)
        for item in rows:
            if item['method'] == 'a' and item['repeat'] == 1:
                item['outer_timeout'] = True
                item['resources']['systemd_result'] = 'timeout' if item['query'] == 'timeout' else 'oom-kill'
                item['resources']['memory_limit_exceeded'] = item['query'] == 'oom'
        result = analyze(env, rows)
        failures = result['methods']['a']['failures']
        self.assertEqual(failures['timeout'], 1)
        self.assertEqual(failures['oom'], 1)
        self.assertEqual(result['comparisons'][0]['eligible_properties'], 0)
        self.assertIsNone(result['comparisons'][0]['geometric_mean_ratio'])
        self.assertEqual(result['methods']['a']['property_counts']['stable_solved'], 2)

    def test_unknown_and_unstable_repeats_keep_the_denominator(self):
        env = environment(('unstable', 'unknown'))
        rows = matrix(env)
        for i, item in enumerate(rows):
            if item['method'] == 'a' and (item['query'] == 'unknown' or item['repeat'] == 1):
                rows[i] = row(item['query'], item['method'], item['repeat'], verdict='unknown')
        result = analyze(env, rows)
        a = result['methods']['a']
        self.assertEqual(a['total_properties'], 2)
        self.assertEqual(a['solved_runs'], 1)
        self.assertEqual(a['property_counts']['solved_in_any_repeat'], 1)
        self.assertEqual(a['property_counts']['stable_solved'], 0)
        self.assertEqual(a['property_counts']['unstable_repeat_outcomes'], 1)
        self.assertEqual(result['comparisons'][0]['eligible_properties'], 0)

    def test_missing_invalid_and_multiplexed_counters_are_not_zero(self):
        env = environment(('missing', 'invalid', 'multiplexed'))
        rows = matrix(env)
        for item in rows:
            if item['method'] != 'a' or item['repeat'] != 0:
                continue
            if item['query'] == 'missing':
                item['resources']['perf_counters'] = None
            elif item['query'] == 'invalid':
                item['resources']['perf_counters']['instructions:u']['value'] = 0
            else:
                item['resources']['perf_counters']['instructions:u']['time_running_percent'] = 99.99
        result = analyze(env, rows)
        failures = result['methods']['a']['failures']
        for key in ('missing_counter', 'invalid_counter', 'multiplexed_counter'):
            self.assertEqual(failures[key], 1)
        self.assertEqual(result['comparisons'][0]['eligible_properties'], 0)
        self.assertIsNone(observations(rows[0])['instructions'])
        for value in (float('nan'), float('inf'), -1, True, '123'):
            bad = row('p', 'a', 0, count=value)
            self.assertIn('invalid_counter', observations(bad)['counter_status'])

    def test_definitive_disagreements_never_enter_ratios(self):
        env = environment(('between', 'within'))
        rows = matrix(env)
        for i, item in enumerate(rows):
            if (item['query'] == 'between' and item['method'] == 'b'
                    or item['query'] == 'within' and item['method'] == 'a' and item['repeat'] == 1):
                rows[i] = row(item['query'], item['method'], item['repeat'], verdict='unreachable')
        result = analyze(env, rows)
        self.assertEqual(result['definitive_disagreements'], ['between', 'within'])
        self.assertEqual(result['methods']['a']['property_counts']['conflicting_definitive_repeats'], 1)
        self.assertEqual(result['comparisons'][0]['eligible_properties'], 0)
        self.assertIn('definitive_verdict_disagreement', result['comparisons'][0]['exclusions'][0]['reasons'])

    def test_process_tree_is_not_double_counted_and_branches_sum(self):
        first, second = row('p', 'a', 0, 40), row('p', 'a', 0, 60)
        grouped = dict(query='p', method='a', repeat=0, verdict='reachable', branches=[first, second])
        self.assertEqual(observations(grouped)['instructions'], 100)
        grouped['resources'] = row('p', 'a', 0, 150)['resources']
        self.assertEqual(observations(grouped)['instructions'], 150)
        second['outer_timeout'] = True
        self.assertIn('timeout', observations(grouped)['exclusion_reasons'])
        grouped['resources']['perf_counters'] = None
        self.assertIsNone(observations(grouped)['instructions'])
        self.assertIn('missing_counter', observations(grouped)['counter_status'])

    def test_single_repeat_has_no_variability_estimate(self):
        env = environment(repeats=1)
        result = analyze(env, matrix(env))
        self.assertEqual(result['comparisons'][0]['eligible_properties'], 1)
        variability = result['methods']['a']['instruction_repeat_variability']
        self.assertIsNone(variability['median_max_over_min'])
        self.assertIsNone(variability['cases'][0]['coefficient_of_variation'])

    def test_polarity_and_truth_must_be_consistent(self):
        env = environment()
        rows = matrix(env)
        rows[-1]['property_kind'] = 'AG'
        rows[-1]['property_truth'] = False
        with self.assertRaises(ValueError):
            analyze(env, rows)
        rows = matrix(env)
        rows[0]['property_truth'] = False
        with self.assertRaises(ValueError):
            analyze(env, rows)

    def test_cli_preserves_raw_records_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'raw'
            source.mkdir()
            env = environment()
            (source / 'environment.json').write_text(json.dumps(env))
            (source / 'runs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in matrix(env)))
            original = {p.name: p.read_bytes() for p in source.iterdir()}
            output = Path(tmp) / 'analysis'
            main([str(source), '--output', str(output)])
            self.assertTrue((output / 'analysis.json').is_file())
            self.assertTrue((output / 'analysis.md').is_file())
            for target in (source, output):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    main([str(source), '--output', str(target)])
            self.assertEqual(original, {p.name: p.read_bytes() for p in source.iterdir()})
            with redirect_stdout(io.StringIO()) as stream:
                main([str(source), '--format', 'json'])
            self.assertEqual(json.loads(stream.getvalue())['coverage']['observed_runs'], 4)
            (source / 'runs.jsonl').write_text(json.dumps(matrix(env)[0]) + '\n')
            destination = Path(tmp) / 'incomplete-analysis'
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main([str(source), '--output', str(destination)])
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
