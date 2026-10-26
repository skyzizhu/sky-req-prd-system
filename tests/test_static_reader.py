import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'template'))
from projectlib import read, write, validate, spec_markdown, compile_project, hashes

class StaticReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = pathlib.Path(cls.temp.name)/'base'
        subprocess.run([sys.executable, str(ROOT/'scripts/create_static_demo.py'), str(cls.base)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.work.name)/'project'
        shutil.copytree(self.base, self.root)
        self.file = self.root/'versions/v0.1/content/spec.json'

    def tearDown(self):
        self.work.cleanup()

    def test_states_match_and_export_keeps_module_hierarchy(self):
        self.assertEqual(validate(self.root)[0], [])
        spec = read(self.file)
        exported = spec_markdown(spec)
        self.assertIn('## 订单管理\n\n### 创建订单', exported)
        for rule in spec['requirements'][0]['rule_details']:
            self.assertEqual(exported.count('- '+rule['statement']), 1)

    def test_export_deduplicates_controls_but_retains_configured_properties(self):
        spec=read(self.file)
        duplicate=dict(spec['interactions'][0],id='extra-state-control',selector='#extra',properties={})
        spec['interactions'].extend([duplicate,dict(duplicate,id='configured',properties={'maxLength':37})])
        exported=spec_markdown(spec)
        self.assertNotIn('技术定位：',exported)
        self.assertNotIn('只读展示',exported)
        self.assertIn('最大长度：37',exported)
        self.assertIn('configured',exported)
        self.assertNotIn('extra-state-control',exported)
        self.assertEqual(exported.count('#### 关联原型'),1)

    def test_structured_field_table_and_open_question_survive_export(self):
        spec=read(self.file)
        rule=spec['requirements'][0]['rule_details'][0]
        rule['table']={'columns':['字段','来源'], 'rows':[['名称','身份|手填\n待明确']]}
        check=spec['requirements'][0]['review']['checks'][0]
        check.update(status='pending',question='初始值是什么？',blocking=True)
        write(self.file,spec)
        self.assertEqual(validate(self.root)[0],[])
        compile_project(self.root)
        exported=spec_markdown(spec)
        self.assertIn('| 名称 | 身份｜手填 待明确 |',exported)
        self.assertIn('待明确的实现口径',exported)
        self.assertIn('初始值是什么？（影响实现/验收，需先明确）',exported)
        self.assertIn('阻塞开发：是',exported)

    def test_rule_subject_and_clauses_survive_export_and_validation(self):
        spec=read(self.file)
        rule=spec['requirements'][0]['rule_details'][0]
        rule['title']='订单名称'
        rule['clauses']=[{'label':'默认值','text':'新建为空；修改带入已有名称'},{'label':'校验时机','text':'提交时校验，错误保留输入'}]
        write(self.file,spec)
        self.assertEqual(validate(self.root)[0],[])
        exported=spec_markdown(spec)
        self.assertIn('##### 订单名称',exported)
        for row in rule['clauses']:self.assertEqual(exported.count(row['label']+'：'+row['text']),1)
        from qualitylib import evaluate
        for clauses in ([{'label':'默认值','text':''}], '正文'):
            rule['clauses']=clauses
            write(self.file,spec)
            self.assertTrue(any('说明项' in error for error in validate(self.root)[0]))
            self.assertIn('rule_content_invalid',{i['code'] for i in evaluate(spec,self.file.parent)['issues']})

    def test_malformed_rule_table_is_rejected(self):
        from qualitylib import evaluate
        spec=read(self.file)
        spec['requirements'][0]['rule_details'][0]['table']={'columns':['字段','来源'],'rows':[['少一列']]}
        write(self.file,spec)
        self.assertTrue(any('等宽' in error for error in validate(self.root)[0]))
        self.assertIn('rule_table_invalid',{i['code'] for i in evaluate(spec,self.file.parent)['issues']})

    def test_missing_state_canvas_and_unknown_rule_state_rejected(self):
        spec = read(self.file)
        spec['pages'][0]['states'][0]['id'] = 'missing'
        spec['interactions'][0]['state_ids'] = ['unknown']
        write(self.file, spec)
        errors = validate(self.root)[0]
        self.assertTrue(any('静态状态声明与画布不一致' in e for e in errors))
        self.assertTrue(any('静态规则关联不存在的状态' in e for e in errors))

    def test_static_page_cannot_declare_executable_action(self):
        spec = read(self.file)
        spec['interactions'][0]['action'] = 'submit'
        write(self.file, spec)
        self.assertTrue(any('静态原型只允许 inspect' in e for e in validate(self.root)[0]))

    def test_handoff_types_and_schema_rejection(self):
        spec=read(self.file)
        spec['pages'][0]['handoff']['dependencies']='not-an-array'
        spec['schema_version']=1
        write(self.file,spec)
        errors=validate(self.root)[0]
        self.assertTrue(any('schema_version=2' in error for error in errors))
        self.assertTrue(any('handoff.dependencies' in error for error in errors))

    def test_full_prd_has_one_title_and_one_copy_of_acceptance_prose(self):
        import json
        js=(self.root/'site/js/data.js').read_text()
        data=json.loads(js.split(' = ',1)[1].rstrip(';\n'))
        bundle=data['versions']['v0.1']
        self.assertEqual(len(bundle['prd_sections']),9)
        markdown=bundle['full_prd_markdown']
        self.assertEqual(len([line for line in markdown.splitlines() if line.startswith('# ')]),1)
        for ac in read(self.file)['requirements'][0]['acceptance']:
            self.assertEqual(markdown.count('预期：'+ac['then']),1)

    def test_removed_entry_is_rejected(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/project.py'),'migrate',str(self.root)],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        project_file=self.root/'project.json'
        project=read(project_file);project['schema_version']=2;write(project_file,project)
        self.assertTrue(any('schema_version=3' in error for error in validate(self.root)[0]))
        before=hashes(self.root)
        with self.assertRaisesRegex(ValueError,'schema_version=3'):compile_project(self.root)
        self.assertEqual(before,hashes(self.root))

    def test_native_control_can_reuse_precise_common_annotation(self):
        html=self.file.parent/'prototype/create-order.html'
        text=html.read_text()
        self.assertIn('<input type="text" aria-label="订单名称" id="failed-name"',text)
        self.assertIn('data-rule-ref="INT-ORDER-NAME"',text)
        self.assertIn('<textarea aria-label="备注"',text)
        self.assertEqual(validate(self.root)[0],[])
        from qualitylib import evaluate
        self.assertEqual(evaluate(read(self.file),self.file.parent)['counts']['errors'],0)

    def test_required_element_cannot_point_to_another_state(self):
        spec=read(self.file)
        spec['pages'][0]['states'][1]['elements'][0]['selector']='#default-name'
        write(self.file,spec)
        self.assertTrue(any('必要元素缺失或不属于该状态' in error for error in validate(self.root)[0]))

    def test_page_and_local_state_review_references_are_checked(self):
        from qualitylib import evaluate
        spec=read(self.file)
        page=spec['pages'][0]
        page['state_review']=[
            {'dimension':'初始与校验','status':'covered','state_ids':['default','invalid']},
            {'dimension':'本地填写','status':'local','selectors':['#default-name'],'reason':'输入后切换Tab核对恢复预设值'},
            {'dimension':'取消结果','status':'not_applicable','reason':'本案例只负责创建订单，取消返回为已有页面交接'}]
        self.assertNotIn('state_review_invalid',{i['code'] for i in evaluate(spec,self.file.parent)['issues']})
        page['state_review'][0]['state_ids']=['missing']
        self.assertIn('state_review_invalid',{i['code'] for i in evaluate(spec,self.file.parent)['issues']})
        page['state_review'][0]['state_ids']=['default']
        page['state_review'][1]['selectors']=['#missing']
        self.assertIn('state_review_invalid',{i['code'] for i in evaluate(spec,self.file.parent)['issues']})

    def test_state_review_rejects_invalid_or_unexplained_classification(self):
        from qualitylib import evaluate
        spec=read(self.file)
        for row in [
            {'dimension':'错误','status':'covered','state_ids':[{}]},
            {'dimension':'错误','status':'local','selectors':['#default-name']},
            {'dimension':'错误','status':'not_applicable'}]:
            spec['pages'][0]['state_review']=[row]
            self.assertIn('state_review_invalid',{i['code'] for i in evaluate(spec,self.file.parent)['issues']})
