import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'template'))
from audit_quality import audit
from projectlib import spec_markdown


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.spec = {'requirements': [{'id': 'FR-1', 'title': '名称', 'source': 'origin', 'status': 'confirmed',
            'acceptance': [{'id': 'AC-1', 'given': '空名称', 'when': '提交', 'then': '拒绝'}],
            'rule_details': [{'id': 'RULE-1', 'category': 'validation', 'statement': '名称不能为空',
                'source': 'origin', 'status': 'confirmed', 'examples': [{'input': '空字符串', 'expected': '拒绝'}],
                'acceptance_ids': ['AC-1']}]}]}

    def test_complete_audit_is_read_only_and_rendered(self):
        before = copy.deepcopy(self.spec)
        self.assertFalse(audit(self.spec)['issues'])
        self.assertEqual(self.spec, before)
        rendered = spec_markdown(self.spec)
        self.assertIn('名称不能为空', rendered)
        self.assertIn('空字符串', rendered)
        self.assertIn('AC-1', rendered)

    def test_missing_examples_and_wrong_reference(self):
        rule = self.spec['requirements'][0]['rule_details'][0]
        rule.update(examples=[], acceptance_ids=['AC-NOT-HERE'], status='pending')
        self.assertEqual(len(audit(self.spec)['issues']), 3)

    def test_duplicate_rule_and_malformed_example(self):
        rules = self.spec['requirements'][0]['rule_details']
        rules.append(copy.deepcopy(rules[0]))
        rules[1]['examples'] = [None]
        self.assertEqual(len(audit(self.spec)['issues']), 2)

    def test_legacy_report_without_mutation(self):
        del self.spec['requirements'][0]['rule_details']
        self.assertEqual(len(audit(self.spec)['issues']), 1)
        self.assertIn('FR-1', spec_markdown(self.spec))


if __name__ == '__main__':
    unittest.main()
