import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'template'))
from qualitylib import evaluate, markdown, PROFILES
from projectlib import spec_markdown

class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)/'demo'
        subprocess.run([sys.executable,str(ROOT/'scripts/create_static_demo.py'),str(cls.root)],check=True,capture_output=True)
        cls.content=cls.root/'versions/v0.1/content'
        cls.original=json.loads((cls.content/'spec.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):self.spec=copy.deepcopy(self.original);self.req=self.spec['requirements'][0]
    def report(self):return evaluate(self.spec,self.content)
    def codes(self):return {i['code'] for i in self.report()['issues'] if i['severity']=='error'}

    def test_review_draft_is_read_only_and_does_not_claim_ready(self):
        before=copy.deepcopy(self.spec);report=self.report()
        self.assertEqual(report['counts']['errors'],0)
        self.assertEqual(report['status'],'review_required')
        self.assertEqual(self.spec,before)
        self.assertIn('BC-ORDER-MAX',markdown(report))
        self.assertIn('40 字',spec_markdown(self.spec))

    def test_removing_all_element_declarations_is_rejected(self):
        for state in self.spec['pages'][0]['states']:state.pop('elements')
        self.assertTrue({'elements_missing','visual_target_missing'}<=self.codes())

    def test_removing_precise_rule_links_is_rejected(self):
        for item in self.spec['interactions']:item.pop('rule_ids')
        self.assertTrue({'invalid_精确规则','visual_rule_unlinked'}<=self.codes())

    def test_deleting_failure_state_and_annotation_cannot_hide_requirement(self):
        self.spec['pages'][0]['states']=[s for s in self.spec['pages'][0]['states'] if s['id']!='failed']
        self.spec['interactions']=[i for i in self.spec['interactions'] if i['id']!='INT-ORDER-FAILURE']
        self.assertIn('visual_target_missing',self.codes())

    def test_wrong_target_and_unrelated_acceptance_are_rejected(self):
        self.req['boundary_cases'][0]['acceptance_ids']=['AC-ORDER-SUCCESS']
        self.req['rule_details'][-1]['presentation']['targets'][0]['selector']='#default-name'
        self.assertTrue({'case_acceptance_mismatch','visual_target_missing'}<=self.codes())

    def test_html_element_must_belong_to_visible_snapshot(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            content=Path(directory)/'content';shutil.copytree(self.content,content)
            file=content/'prototype/create-order.html'
            file.write_text(file.read_text().replace('id="failed-focus"','hidden id="failed-focus"'))
            self.assertIn('element_not_visible',{i['code'] for i in evaluate(self.spec,content)['issues']})

    def test_profile_checks_cannot_be_skipped(self):
        self.req['review']['checks']=[]
        self.assertIn('check_missing',self.codes())
        self.req['review']['checks']=[{'dimension':k,'status':'not_applicable','reason':'本次只评审字段命名，不改此能力。'} for k in PROFILES['form']['dimensions']]
        self.assertEqual(self.codes(),set())
        self.req['review']['checks'][0]['reason']=''
        self.assertIn('not_applicable_reason',self.codes())

    def test_nonblocking_decision_and_blocking_decision_differ(self):
        self.req['review']['checks'][0]['blocking']=True
        self.assertIn('feature_decision',self.codes())

    def test_blocking_requirement_prevents_delivery_pass(self):
        self.req['blocking']=True
        self.assertIn('requirement_blocking',self.codes())

    def test_boundary_cases_can_use_text_without_extra_state(self):
        self.assertEqual(len(self.spec['pages'][0]['states']),5)
        self.assertEqual(self.codes(),set())
        self.req['boundary_cases'][1]['presentation']['reason']=''
        self.assertIn('text_reason_missing',self.codes())

    def test_case_must_cover_dimension_rules(self):
        self.req['review']['checks'][1]['case_ids']=['BC-ORDER-FAIL']
        self.assertTrue({'case_kind_missing','check_case_unrelated'}<=self.codes())

    def test_input_coverage_and_unknown_feature_types(self):
        self.spec['quality']['input_items'][0]['requirement_ids']=[]
        self.req['review']['types']=['unknown']
        self.assertTrue({'requirement_without_input','feature_type_missing'}<=self.codes())

    def test_all_profiles_require_applicable_decisions(self):
        for kind,profile in PROFILES.items():
            with self.subTest(kind=kind):
                self.req['review']={'types':[kind],'checks':[{'dimension':key,'status':'pending','question':'本次是否涉及'+label+'？','blocking':False} for key,label in profile['dimensions'].items()]}
                self.assertEqual(self.codes(),set())

    def test_text_only_scope_does_not_force_prototype_or_acceptance(self):
        self.spec['quality']['scope']={'prd':True,'prototype':False,'acceptance':False}
        self.spec['pages']=[];self.spec['interactions']=[]
        for rule in self.req['rule_details']:
            rule['presentation']={'mode':'text','reason':'本次仅交付规则说明。'};rule.pop('acceptance_ids')
        self.req['acceptance']=[]
        for case in self.req['boundary_cases']:
            case['presentation']={'mode':'text','reason':'本次仅交付规则说明。'};case.pop('acceptance_ids')
        self.assertEqual(self.codes(),set())
        self.spec['quality']['scope']['prd']=True
        self.assertEqual(self.codes(),set())

    def test_cli_strict_rejects_missing_coverage_and_can_write_report(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix=Path(directory)/'report'
            cmd=[sys.executable,str(ROOT/'scripts/audit_quality.py'),str(self.root),'--strict','--report',str(prefix)]
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertTrue(prefix.with_suffix('.md').is_file())
            file=self.content/'spec.json';before=file.read_bytes()
            try:
                spec=copy.deepcopy(self.original);spec.pop('quality');file.write_text(json.dumps(spec))
                self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,1)
            finally:file.write_bytes(before)

if __name__=='__main__':unittest.main()
