import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'template'))
sys.path.insert(0,str(ROOT/'scripts'))
from qualitylib import evaluate, markdown, PROFILES
from prdlib import case_scenario
from projectlib import spec_markdown, compile_project

class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)/'demo'
        subprocess.run([sys.executable,str(ROOT/'scripts/create_static_demo.py'),str(cls.root)],check=True,capture_output=True)
        cls.content=cls.root/'versions/v0.1/content'
        cls.original=json.loads((cls.content/'spec.json').read_text())
        for check in cls.original['requirements'][0]['review']['checks']:
            if check['status']=='pending':
                check.update(impact='editorial',blocking=False,question='测试夹具只校对显示名称，既有约束不变。')
        (cls.content/'spec.json').write_text(json.dumps(cls.original,ensure_ascii=False))
        compile_project(cls.root)

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

    def test_small_element_needs_its_own_state_applicable_annotation(self):
        self.spec['interactions']=[it for it in self.spec['interactions'] if it['id']!='INT-ORDER-REMARK']
        self.assertIn('element_annotation_missing',self.codes())
        # A form-level annotation still cannot stand in for the missing field.
        self.spec['interactions'][0]['selector']='#order-canvas'
        self.assertIn('element_annotation_missing',self.codes())

    def test_common_element_annotation_must_apply_to_each_state(self):
        it=next(it for it in self.spec['interactions'] if it['id']=='INT-ORDER-AMOUNT')
        it['state_ids']=['default']
        report=self.report()
        paths=[i['path'] for i in report['issues'] if i['code']=='element_annotation_missing']
        self.assertIn('create-order/failed/#failed-amount',paths)
        self.assertNotIn('create-order/default/#default-amount',paths)

    def test_common_field_mapping_is_a_precise_visual_target(self):
        self.req['rule_details'][0]['presentation']={'mode':'prototype','targets':[{'page':'create-order','state':'failed','selector':'#failed-name'}]}
        self.assertEqual(self.codes(),set())

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
                self.req['review']={'types':[kind],'checks':[{'dimension':key,'status':'pending','question':'本次是否涉及'+label+'？','impact':'editorial','blocking':False} for key,label in profile['dimensions'].items()]}
                self.assertEqual(self.codes(),set())

    def test_text_only_scope_does_not_force_prototype_or_acceptance(self):
        self.spec['quality']['scope']={'prd':True,'prototype':False,'acceptance':False}
        self.spec['pages']=[];self.spec['interactions']=[]
        for rule in self.req['rule_details']:
            rule['presentation']={'mode':'text','reason':'本次仅交付规则说明。'};rule.pop('acceptance_ids')
        self.req['boundary_cases']=[case_scenario(c,self.req) for c in self.req['boundary_cases']]
        self.req['acceptance']=[]
        for diagram in self.spec.get('diagrams',[]):
            for scene in diagram.get('path_reviews',[]):scene.pop('acceptance_ids',None)
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

    def test_validate_writes_same_report_and_rejects_incomplete_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix=Path(directory)/'report'
            cmd=[sys.executable,str(ROOT/'scripts/validate.py'),str(self.root),'--report',str(prefix)]
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            good=json.loads(prefix.with_suffix('.json').read_text())
            self.assertEqual(good['status'],'review_required')
            file=self.content/'spec.json'; before=file.read_bytes()
            try:
                spec=copy.deepcopy(self.original);spec.pop('quality');file.write_text(json.dumps(spec))
                subprocess.run([sys.executable,str(self.root/'build.py')],check=True,capture_output=True)
                self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,1)
                self.assertEqual(json.loads(prefix.with_suffix('.json').read_text())['status'],'incomplete')
                self.assertTrue(prefix.with_suffix('.md').is_file())
            finally:
                file.write_bytes(before)
                subprocess.run([sys.executable,str(self.root/'build.py')],check=True,capture_output=True)

    def test_input_critical_literal_cannot_disappear_from_rule(self):
        self.req['rule_details'][0]['statement']='名称必填，去除首尾空格。'
        self.assertIn('input_literal_missing',self.codes())
        self.spec['quality']['input_items'][0].pop('constraints')
        self.assertIn('input_constraints_missing',self.codes())

    def test_numeric_literal_does_not_match_a_larger_number(self):
        constraint=self.spec['quality']['input_items'][0]['constraints'][0]
        constraint.update(quote='名称最多40字',literals=['40字'])
        self.req['rule_details'][0]['statement']='名称最多140字'
        self.assertIn('input_literal_missing',self.codes())
        self.req['rule_details'][0]['statement']='名称最多40\n字'
        self.assertNotIn('input_literal_missing',self.codes())

    def test_state_review_is_required_and_must_include_every_authored_state(self):
        page=self.spec['pages'][0];page.pop('state_review')
        self.assertIn('state_review_missing',self.codes())
        page['state_review']=[{'dimension':'初始','status':'covered','state_ids':['default']}]
        self.assertIn('state_review_uncovered',self.codes())

    def test_empty_boundary_cannot_reference_failure_scenario_of_same_rule(self):
        case=self.req['boundary_cases'][0]
        case['acceptance_ids']=['AC-ORDER-FAILURE']
        next(r for r in self.req['rule_details'] if r['id']=='RULE-ORDER-INVALID')['acceptance_ids'].append('AC-ORDER-FAILURE')
        self.assertIn('case_acceptance_kind',self.codes())

    def test_implementation_decision_cannot_be_marked_nonblocking(self):
        check=self.req['review']['checks'][0]
        check.update(status='pending',impact='implementation',blocking=False,question='金额是否必填？')
        self.assertIn('decision_nonblocking',self.codes())
        self.assertIn('阻塞开发：是',spec_markdown(self.spec))
        check.update(impact='editorial',question='仅校对字段显示名称，不改含义与约束。')
        self.assertEqual(self.codes(),set())

    def test_reference_case_has_one_canonical_gwt_and_rejects_broken_reference(self):
        case=self.req['boundary_cases'][1]
        resolved=case_scenario(case,self.req)
        ac=next(a for a in self.req['acceptance'] if a['id']==case['acceptance_ids'][0])
        self.assertEqual(resolved['expected'],ac['then'])
        self.assertEqual(spec_markdown(self.spec).count('预期：'+ac['then']),1)
        ac['then']='长度等于上限时校验通过（修订）'
        self.assertEqual(case_scenario(case,self.req)['expected'],ac['then'])
        case['acceptance_ids']=['MISSING']
        self.assertIn('case_incomplete',self.codes())

    def test_public_demo_keeps_implementation_questions_blocking(self):
        from create_static_demo import example_spec
        _,spec=example_spec()
        report=evaluate(spec,self.content)
        self.assertEqual(report['status'],'incomplete')
        self.assertEqual({i['code'] for i in report['issues'] if i['severity']=='error'},{'feature_decision'})

    def test_open_implementation_question_blocks_freeze_and_handoff_even_with_confirmed_parent(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'project';shutil.copytree(self.root,root)
            file=root/'versions/v0.1/content/spec.json';spec=json.loads(file.read_text())
            req=spec['requirements'][0];req['status']='confirmed'
            for rule in req['rule_details']:rule['status']='confirmed'
            req['review']['checks'][0].update(status='pending',impact='implementation',blocking=False,question='哪些角色可创建？')
            file.write_text(json.dumps(spec));compile_project(root)
            for command in [('freeze',),('handoff','--revision','r1')]:
                args=[sys.executable,str(ROOT/'scripts/project.py'),command[0],str(root),*command[1:]]
                self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
                project=json.loads((root/'project.json').read_text())
                self.assertEqual(project['versions'][0]['status'],'planning')
                self.assertEqual(len(project['versions']),1)

if __name__=='__main__':unittest.main()


class MobileDeliveryChecksTests(unittest.TestCase):
    setUpClass=classmethod(QualityTests.setUpClass.__func__)
    tearDownClass=classmethod(QualityTests.tearDownClass.__func__)
    setUp=QualityTests.setUp
    report=QualityTests.report
    codes=QualityTests.codes

    def test_mobile_platform_requires_all_applicability_dimensions(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            content=Path(directory)/'content';shutil.copytree(self.content,content)
            manifest=json.loads((content/'manifest.json').read_text());manifest['product']['form']='mobile';(content/'manifest.json').write_text(json.dumps(manifest))
            codes={i['code'] for i in evaluate(self.spec,content)['issues']}
            self.assertIn('mobile_review_missing',codes);self.assertIn('mobile_check_missing',codes)

    def test_declared_mobile_checks_need_related_evidence_and_real_applicability(self):
        rule=self.req['rule_details'][0];ac=rule['acceptance_ids'][0]
        self.spec['quality']['mobile_review']=[{'dimension':d,'status':'covered','rule_ids':[rule['id']],'acceptance_ids':[ac]} for d in ['platform','navigation','interruption','authorization','network','components']]
        self.assertFalse({c for c in self.codes() if c.startswith('mobile_')})
        check=self.spec['quality']['mobile_review'][1];check['acceptance_ids']=['missing'];self.assertTrue(any(i['severity']=='error' and '移动验收' in i['message'] for i in self.report()['issues']))
        check.update(status='not_applicable',reason='');self.assertIn('mobile_applicability_invalid',self.codes())
        check.update(status='pending',question='返回时保留什么？',impact='implementation',blocking=False);self.assertIn('decision_nonblocking',self.codes())
