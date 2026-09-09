import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from projectlib import validate_replay_cases


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.spec = {'requirements': [{'id': 'FR-1'}], 'replay_cases': [{
            'id': 'viewer-empty', 'title': '空数据', 'role': 'viewer', 'scenario': 'empty',
            'pages': ['list'], 'requirement_ids': ['FR-1'], 'source': 'ai-inferred',
            'status': 'pending', 'state': {'orders': []}}]}

    def test_valid_and_legacy(self):
        before = copy.deepcopy(self.spec)
        self.assertEqual(validate_replay_cases(self.spec, {'list'}), [])
        self.assertEqual(self.spec, before)
        self.assertEqual(validate_replay_cases({}, set()), [])

    def test_invalid_cases(self):
        for field, value in [('id', '../bad'), ('role', ''), ('scenario', 'arbitrary'),
                             ('pages', ['missing']), ('requirement_ids', ['FR-404']),
                             ('status', 'released'), ('state', {'role': 'admin'}),
                             ('state', {'x': 'a' * 32769}), ('state', {'x': float('nan')})]:
            with self.subTest(field=field, value=str(value)[:30]):
                spec = copy.deepcopy(self.spec)
                spec['replay_cases'][0][field] = value
                self.assertTrue(validate_replay_cases(spec, {'list'}))
        self.spec['replay_cases'] *= 2
        self.assertTrue(validate_replay_cases(self.spec, {'list'}))
