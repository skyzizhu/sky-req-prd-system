import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from review_delivery import Controls, control_review, review
from review_scope import affected


class ControlConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.content = Path(self.tmp.name)
        (self.content/'manifest.json').write_text(json.dumps({'modules':[{'pages':[{'id':'apply','type':'prototype','file':'page.html'}]}]}))
        (self.content/'page.html').write_text('''<section data-ps-state="default"><div class="sr-snapshot">
<select id="device"><option value="laptop">Laptop</option><option value="monitor" selected>Monitor</option></select>
<select id="parts" multiple><option value="bag" selected>Bag</option><option value="adapter">Adapter</option></select>
<input id="agree" type="checkbox" checked><textarea id="reason" required maxlength="200">keep</textarea>
<input id="submit" type="button" disabled></div></section>
<section data-ps-state="failed"><div class="sr-snapshot"><input id="failed-reason" value="preserved"></div></section>''')
        self.spec = {'requirements':[{'id':'FR','rule_details':[{'id':'RULE'}]}], 'quality':{'control_checks':[]}}
        self.spec['interactions']=[dict(id='INT-'+key,page='apply',selector='#'+key,rule_ids=['RULE'],state_ids=['failed'] if key=='failed-reason' else ['default']) for key in ['device','parts','agree','reason','submit','failed-reason']]

    def tearDown(self):self.tmp.cleanup()

    def check(self, selector, expected, state='default'):
        self.spec['quality']['control_checks']=[dict(page='apply',state=state,selector=selector,rule_ids=['RULE'],expected=expected)]
        return control_review(self.spec,self.content)

    def test_enums_and_default_are_independent_assertions(self):
        report=self.check('#device',{'options':[{'value':'laptop','label':'Laptop'},{'value':'monitor','label':'Monitor'}],'value':'laptop'})
        self.assertEqual(len(report['findings']),1)
        self.assertEqual(report['findings'][0]['evidence']['actual'],'monitor')
        self.assertEqual(report['findings'][0]['evidence']['property'],'value')

    def test_multi_check_required_limit_disabled_and_preservation(self):
        for selector, expected, state in [('#parts',{'value':['bag'],'multiple':True},'default'),('#agree',{'checked':True,'value':'on'},'default'),('#reason',{'required':True,'maxlength':'200','value':'keep'},'default'),('#submit',{'disabled':True},'default'),('#failed-reason',{'value':'preserved'},'failed')]:
            with self.subTest(selector=selector):self.assertFalse(self.check(selector,expected,state)['findings'])

    def test_wrong_enum_count_and_unchecked_are_not_silently_passed(self):
        result=self.check('#device',{'options':[{'value':'laptop','label':'Laptop'}]})
        self.assertEqual(result['findings'][0]['code'],'control_mismatch')
        self.assertTrue(result['unchecked_controls'])

    def test_native_fallback_skips_disabled_options_and_reads_option_label(self):
        parser=Controls();parser.feed('<select><option disabled value="a">A</option><optgroup disabled><option value="b">B</option></optgroup><option value="c" label="Shown">C</option></select>')
        actual=parser.values(parser.nodes[0])
        self.assertEqual(actual['value'],'c')
        self.assertEqual(actual['options'][-1]['label'],'Shown')

    def test_control_contract_detects_missing_current_state_annotation_rule(self):
        self.spec['interactions'][0]['rule_ids']=[]
        finding=self.check('#device',{'value':'monitor'})['findings'][0]
        self.assertEqual(finding['code'],'control_annotation_mismatch')
        self.assertEqual(finding['evidence']['missing'],['RULE'])
        self.spec['interactions'][0].update(rule_ids=['RULE'],state_ids=['failed'])
        self.assertEqual(self.check('#device',{'value':'monitor'})['findings'][0]['code'],'control_annotation_mismatch')

    def test_child_control_can_reference_precise_group_annotation(self):
        self.spec['interactions'][0].update(id='INT-DEVICE',selector='#group')
        p=self.content/'page.html';p.write_text(p.read_text().replace('id="device"','id="device" data-rule-ref="INT-DEVICE"'))
        self.assertFalse(self.check('#device',{'value':'monitor'})['findings'])

    def test_wrong_state_rule_or_property_rejected(self):
        self.assertEqual(self.check('#reason',{'required':True},'failed')['findings'][0]['code'],'control_target_invalid')
        self.assertEqual(self.check('#reason',{'required':'true'})['findings'][0]['code'],'control_contract_invalid')
        self.assertEqual(self.check('#reason',{'unimplemented':True})['findings'][0]['code'],'control_contract_invalid')
        self.spec['quality']['control_checks'][0]['rule_ids']=['MISSING']
        self.assertTrue(control_review(self.spec,self.content)['findings'])

    def test_select_without_selected_uses_native_first_option(self):
        parser=Controls();parser.feed('<select><option value="a">A</option><option value="b">B</option></select>')
        self.assertEqual(parser.values(parser.nodes[0])['value'],'a')


class UnifiedReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'project'
        subprocess.run([sys.executable,str(ROOT/'scripts/create_static_demo.py'),str(cls.root)],check=True,capture_output=True)
        cls.source=Path(cls.tmp.name)/'input.md';cls.source.write_text('Determined product plan: create order.')

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_read_only_and_pending_reviews_remain_explicit(self):
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report=review(self.root,inputs=[self.source])
        self.assertEqual(report['status'],'issues_found')  # known demo business questions
        self.assertTrue(all(s['verdict']=='unverified' for s in report['semantic']))
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_evidence_bound_to_sources_and_rubric(self):
        first=review(self.root,inputs=[self.source]);e={'fingerprint':first['fingerprint'],'checks':{}}
        self.source.write_text(self.source.read_text()+' Changed.')
        with self.assertRaisesRegex(ValueError,'过期'):review(self.root,inputs=[self.source],evidence=e)
        first=review(self.root,inputs=[self.source]);e['fingerprint']=first['fingerprint']
        with self.assertRaisesRegex(ValueError,'过期'):review(self.root,inputs=[self.source],evidence=e,rubric={'checks':[{'id':'case','expectation':'unique'}]})

    def test_review_requires_evidence_and_original_input(self):
        first=review(self.root)
        e={'fingerprint':first['fingerprint'],'checks':{'input_scope':{'verdict':'pass','evidence':['spec ledger only']}}}
        with self.assertRaisesRegex(ValueError,'原始方案'):review(self.root,evidence=e)
        e['checks']={'rule_closure':{'verdict':'pass'}}
        with self.assertRaisesRegex(ValueError,'证据'):review(self.root,evidence=e)

    def test_failed_review_requires_actionable_recommendation(self):
        first=review(self.root);e={'fingerprint':first['fingerprint'],'checks':{'consistency':{'verdict':'fail','evidence':['RULE: mismatch']}}}
        with self.assertRaisesRegex(ValueError,'建议'):review(self.root,evidence=e)
        e['checks']['consistency'].update(impact='blocker',recommendation='Correct mismatched default against input.')
        self.assertEqual(next(s for s in review(self.root,evidence=e)['semantic'] if s['id']=='consistency')['impact'],'blocker')

    def test_impact_scope_contains_states_and_diagrams(self):
        spec=json.loads((self.root/'versions/v0.1/content/spec.json').read_text())
        scope=affected(spec,['FR-ORDER-001'])
        self.assertEqual(len(scope['states']),5)
        self.assertIn('STATE-CREATE',scope['diagrams'])
        self.assertIn('RULE-ORDER-NAME',scope['rules'])
        self.assertEqual(affected(spec,[])['states'],[])

    def test_cli_report_and_read_only_boundary(self):
        output=Path(self.tmp.name)/'review'
        cmd=[sys.executable,str(ROOT/'scripts/review_delivery.py'),str(self.root),'--input',str(self.source),'--report',str(output)]
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertEqual(json.loads(Path(str(output)+'.json').read_text())['status'],'issues_found')
        self.assertIn('unverified',Path(str(output)+'.md').read_text())
        original=(self.root/'project.json').read_bytes()
        result=subprocess.run(cmd[:-1]+[str(self.root/'project')],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertEqual((self.root/'project.json').read_bytes(),original)
        result=subprocess.run(cmd[:-1]+[str(self.source.with_suffix(''))],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)

    def test_scenario_runner_evaluates_candidate_and_preserves_case_rubric(self):
        suite=Path(self.tmp.name)/'suite.json'
        suite.write_text(json.dumps({'scenarios':[{'id':'order','input':'Create order; unresolved roles remain pending.','checks':[{'id':'order-roles','expectation':'Unresolved roles must not be invented.'}]}]}))
        mapping=Path(self.tmp.name)/'one-candidate.json'
        mapping.write_text(json.dumps({'order':{'project':str(self.root)}}))
        output=Path(self.tmp.name)/'one-report'
        result=subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_scenarios.py'),str(mapping),'--suite',str(suite),'--report-dir',str(output)],capture_output=True,text=True)
        self.assertEqual(result.returncode,1,result.stderr)
        report=json.loads((output/'order.json').read_text())
        self.assertEqual(next(s for s in report['semantic'] if s['id']=='order-roles')['verdict'],'unverified')
        self.assertEqual(json.loads((output/'summary.json').read_text())[0]['status'],'issues_found')

    def test_scenario_runner_does_not_claim_unrun_cases_pass(self):
        mapping=Path(self.tmp.name)/'candidates.json';mapping.write_text('{}')
        output=Path(self.tmp.name)/'reports'
        run=subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_scenarios.py'),str(mapping),'--report-dir',str(output)],capture_output=True,text=True)
        self.assertEqual(run.returncode,3,run.stderr)
        self.assertEqual([r['status'] for r in json.loads((output/'summary.json').read_text())],['not_run']*3)
