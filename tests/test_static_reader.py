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

    def test_required_element_cannot_point_to_another_state(self):
        spec=read(self.file)
        spec['pages'][0]['states'][1]['elements'][0]['selector']='#default-name'
        write(self.file,spec)
        self.assertTrue(any('必要元素缺失或不属于该状态' in error for error in validate(self.root)[0]))
