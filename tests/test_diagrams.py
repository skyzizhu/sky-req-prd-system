import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'template'))
from create_static_demo import example_spec
from diagramlib import evaluate,mermaid,markdown

class DiagramTests(unittest.TestCase):
    def setUp(self):
        _,self.spec=example_spec()
        self.diagrams=self.spec['diagrams']
    def codes(self):return {i['code'] for i in evaluate(self.spec) if i['severity']=='error'}
    def test_complete_hierarchy_is_read_only(self):
        before=copy.deepcopy(self.spec)
        self.assertEqual(self.codes(),set());self.assertEqual(self.spec,before)
        self.assertIn('stateDiagram-v2',mermaid(self.diagrams[2]))
        self.assertIn('上层流程',markdown(self.diagrams[1],self.diagrams))
    def test_state_labels_preserve_full_meaning_in_transition_table(self):
        state=self.diagrams[2]
        state['edges'][0].update(label='提交且输入无效，需要保留全部内容并定位错误字段',condition='名称为空',effect='显示字段错误，不发起请求')
        svg_source=mermaid(state)
        self.assertIn(': T01',svg_source)
        self.assertNotIn('提交且输入无效',svg_source)
        doc=markdown(state,self.diagrams)
        self.assertIn('提交且输入无效，需要保留全部内容并定位错误字段',doc)
        self.assertIn('条件：名称为空',doc)
        self.assertIn('显示字段错误，不发起请求',doc)
        self.assertIn('| --- | --- | --- | --- |\n| T01 |',doc)
        self.assertNotIn('| --- | --- | --- | --- |\n\n',doc)

    def test_flow_shapes_and_decision_exits_are_checked(self):
        flow=self.diagrams[1]
        next(n for n in flow['nodes'] if n['id']=='check')['type']='decision'
        next(n for n in flow['nodes'] if n['id']=='done')['type']='end'
        self.assertIn('{"校验名称"}',mermaid(flow))
        self.assertIn('(["创建成功，返回列表"])',mermaid(flow))
        self.assertEqual(self.codes(),set())
        branches=[e for e in flow['edges'] if e['from']=='check']
        branches[1]['label']=branches[0]['label']
        self.assertIn('diagram_decision_labels',self.codes())
        flow['edges']=[e for e in flow['edges'] if e is not branches[1]]
        self.assertIn('diagram_decision_branches',self.codes())

    def test_flow_terminal_cannot_continue(self):
        self.diagrams[1]['edges'].append({'from':'done','to':'fill','label':'再试'})
        self.assertIn('diagram_terminal_outgoing',self.codes())

    def test_module_overview_cannot_be_replaced_with_detail_diagrams(self):
        self.spec['diagrams']=self.diagrams[1:]
        self.assertTrue({'module_flow_missing','diagram_parent'}<=self.codes())
    def test_required_subdiagram_cannot_be_removed(self):
        self.spec['diagrams']=self.diagrams[:2]
        self.assertIn('detail_diagram_missing',self.codes())
    def test_wrong_parent_node_and_cycle_are_rejected(self):
        self.diagrams[1]['parent_node']='missing'
        self.assertIn('diagram_parent',self.codes())
        self.diagrams[1].update(parent_id='STATE-CREATE',parent_node='idle')
        self.diagrams[2].update(parent_id='FLOW-CREATE',parent_node='fill')
        self.assertIn('diagram_cycle',self.codes())
    def test_transition_condition_and_endpoints_are_checked(self):
        self.diagrams[2]['edges'][0]['label']=''
        self.diagrams[1]['edges'][0]['to']='missing'
        self.assertTrue({'diagram_condition','diagram_edge'}<=self.codes())
    def test_failure_branch_cannot_end_without_recovery_or_handoff(self):
        self.diagrams[1]['edges']=[e for e in self.diagrams[1]['edges'] if e['from']!='fail']
        self.assertIn('diagram_deadend',self.codes())

    def test_process_changes_affect_function_list_but_confirmation_does_not(self):
        import prdlib
        before=copy.deepcopy(self.spec)
        self.diagrams[1]['status']='confirmed'
        self.assertEqual(prdlib.feature_list(self.spec,before)[0]['change'],'沿用')
        self.diagrams[1]['edges'][0]['label']='更改后的业务条件'
        self.assertEqual(prdlib.feature_list(self.spec,before)[0]['change'],'修改')

    def test_unreachable_island_is_rejected(self):
        self.diagrams[1]['nodes'] += [{'id':'x','label':'孤岛A'},{'id':'y','label':'孤岛B'}]
        self.diagrams[1]['edges'] += [{'from':'x','to':'y','label':'无入口路径'}]
        self.assertIn('diagram_unreachable',self.codes())
    def test_missing_feature_mapping_and_prototype_state_are_checked(self):
        self.diagrams[0]['nodes'][1].pop('requirement_ids')
        self.diagrams[2]['nodes'][0]['prototype']['state']='missing'
        self.assertTrue({'module_feature_unmapped','diagram_prototype_state'}<=self.codes())
    def test_simple_feature_may_omit_child_diagrams_with_reasons(self):
        self.spec['diagrams']=self.diagrams[:1]
        self.spec['requirements'][0]['diagram_review']={kind:{'status':'not_applicable','reason':'只读本地字段展示，无分支及状态切换。'} for kind in ('flow','state')}
        self.assertEqual(self.codes(),set())
        self.spec['requirements'][0]['diagram_review']['state']['reason']=''
        self.assertIn('diagram_na_reason',self.codes())
    def test_no_process_and_no_transitions_need_no_diagrams(self):
        self.spec['diagrams']=[]
        self.spec['quality']['module_reviews'][0]['flow']={'status':'not_applicable','reason':'本次仅改静态说明。'}
        self.spec['requirements'][0]['rule_details']=[]
        self.spec['requirements'][0]['diagram_review']={kind:{'status':'not_applicable','reason':'仅静态说明，无流程或状态流转。'} for kind in ('flow','state')}
        self.assertEqual(self.codes(),set())

    def test_state_only_feature_needs_no_invented_parent_process(self):
        state=self.diagrams[2];state.pop('parent_id');state.pop('parent_node')
        self.spec['diagrams']=[state]
        self.spec['quality']['module_reviews'][0]['flow']={'status':'not_applicable','reason':'本次仅维护既有对象状态，无模块操作流程变更。'}
        self.spec['requirements'][0]['diagram_review']['flow']={'status':'not_applicable','reason':'本次仅定义状态流转。'}
        self.assertEqual(self.codes(),set())

    def test_continuous_state_machine_needs_no_invented_terminal(self):
        state=self.diagrams[2]
        for node in state['nodes']:node.pop('terminal',None)
        state['edges'].append({'from':'success','to':'idle','label':'开始另一笔创建'})
        self.assertEqual(self.codes(),set())

    def test_generated_bundle_and_export_keep_same_three_graphs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'project'
            subprocess.run([sys.executable,str(ROOT/'scripts/create_static_demo.py'),str(root)],capture_output=True,check=True)
            data=json.loads((root/'site/js/data.js').read_text().split(' = ',1)[1].rstrip(';\n'))['versions']['v0.1']
            user=next(s for s in data['prd_sections'] if s['id']=='users')
            self.assertIn('FLOW-ORDER',user['markdown'])
            self.assertNotIn('stateDiagram-v2',user['markdown'])
            self.assertEqual(data['full_prd_markdown'].count('```mermaid'),3)
            self.assertEqual(len(data['diagrams']),3)
            self.assertIn('STATE-CREATE',data['full_prd_markdown'])

if __name__=='__main__':unittest.main()
