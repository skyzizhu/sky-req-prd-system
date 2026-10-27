import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from prdlib import rule_reference_errors
from projectlib import spec_markdown


class RuleReferencesTest(unittest.TestCase):
    def setUp(self):
        self.spec = {'requirements': [
            {'id': 'FR-A', 'title': 'Create', 'description': '', 'source': 'origin', 'status': 'confirmed',
             'rule_details': [{'id': 'RULE-A', 'title': 'Submit', 'category': 'behavior', 'statement': 'Unique submit body',
                               'related_rule_ids': ['RULE-B']}], 'shared_rule_ids': ['RULE-B']},
            {'id': 'FR-B', 'title': 'Recover', 'description': '', 'source': 'origin', 'status': 'confirmed',
             'rule_details': [{'id': 'RULE-B', 'title': 'Recovery', 'category': 'recovery', 'statement': 'Unique recovery body'}]}
        ]}

    def test_references_keep_one_body_and_export_target(self):
        original = copy.deepcopy(self.spec)
        self.assertEqual(rule_reference_errors(self.spec), [])
        exported = spec_markdown(self.spec)
        self.assertEqual(exported.count('Unique recovery body'), 1)
        self.assertIn('](#rule-RULE-B)', exported)
        self.assertIn('<a id="rule-RULE-B"></a>', exported)
        self.assertEqual(self.spec, original)

    def test_reject_unknown_duplicate_self_and_local_shared_reference(self):
        for refs in [['MISSING'], ['RULE-B', 'RULE-B'], ['RULE-A'], 'RULE-B', [None]]:
            with self.subTest(refs=refs):
                spec = copy.deepcopy(self.spec)
                spec['requirements'][0]['rule_details'][0]['related_rule_ids'] = refs
                self.assertTrue(rule_reference_errors(spec))
        self.spec['requirements'][0]['shared_rule_ids'] = ['RULE-A']
        self.assertTrue(rule_reference_errors(self.spec))

    def test_optional_fields_do_not_force_relationships(self):
        del self.spec['requirements'][0]['shared_rule_ids']
        del self.spec['requirements'][0]['rule_details'][0]['related_rule_ids']
        self.assertEqual(rule_reference_errors(self.spec), [])


if __name__ == '__main__':
    unittest.main()
