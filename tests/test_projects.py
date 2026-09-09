import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'template'))
from projectlib import read, write, validate, compile_project, check_build, hashes


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = pathlib.Path(cls.temp.name) / 'base'
        subprocess.run([sys.executable, str(ROOT / 'scripts/create_demo.py'), str(cls.base)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / 'project'
        shutil.copytree(self.base, self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_two_versions_and_freshness(self):
        self.assertEqual(validate(self.root)[0], [])
        self.assertEqual(check_build(self.root), [])
        file = self.root / 'versions/v1.1/content/overview/index.md'
        file.write_text('changed', encoding='utf-8')
        self.assertTrue(check_build(self.root))
        compile_project(self.root)
        self.assertEqual(check_build(self.root), [])

    def test_frozen_tamper_rejected(self):
        file = self.root / 'versions/v1.0/content/prototype/assets/demo.css'
        file.write_text('changed', encoding='utf-8')
        self.assertTrue(any('快照' in e for e in validate(self.root)[0]))
        with self.assertRaises(ValueError):
            compile_project(self.root)

    def test_build_preserves_history(self):
        before = hashes(self.root / 'versions/v1.0')
        compile_project(self.root)
        self.assertEqual(before, hashes(self.root / 'versions/v1.0'))

    def test_broken_interaction_and_requirement_rejected(self):
        path = self.root / 'versions/v1.1/content/spec.json'
        spec = read(path)
        spec['interactions'][0]['selector'] = '#missing'
        spec['interactions'][0]['requirement_ids'] = ['FR-MISSING']
        write(path, spec)
        errors = validate(self.root)[0]
        self.assertTrue(any('元素不存在' in e for e in errors))
        self.assertTrue(any('需求未关联' in e for e in errors))

    def test_missing_acceptance_rejected(self):
        path = self.root / 'versions/v1.1/content/spec.json'
        spec = read(path); spec['requirements'][0]['acceptance'] = []
        write(path, spec)
        self.assertTrue(any('验收口径' in e for e in validate(self.root)[0]))

    def test_cross_requirement_rule_reference_rejected(self):
        path = self.root / 'versions/v1.1/content/spec.json'
        spec = read(path)
        spec['interactions'][0]['rule_ids'] = ['RULE-NAME-INPUT']
        write(path, spec)
        self.assertTrue(any('控件规则关联无效' in e for e in validate(self.root)[0]))

    def test_readonly_business_value_requires_mapping(self):
        path = self.root / 'versions/v1.1/content/spec.json'
        spec = read(path)
        spec['interactions'] = [i for i in spec['interactions'] if i['id'] != 'INT-FEEDBACK']
        write(path, spec)
        self.assertTrue(any('feedback' in e for e in validate(self.root)[0]))

    def test_inline_attributes_rejected(self):
        path = self.root / 'versions/v1.1/content/prototype/list.html'
        path.write_text(path.read_text().replace('<main ', "<main STYLE='color:red' "), encoding='utf-8')
        self.assertTrue(any('内联' in e for e in validate(self.root)[0]))

    def test_path_escape_rejected(self):
        path = self.root / 'versions/v1.1/content/manifest.json'
        m = read(path); m['modules'][0]['pages'][0]['file'] = '../../../../project.json'
        write(path, m)
        self.assertTrue(any('路径越界' in e for e in validate(self.root)[0]))

    def test_blocker_cannot_freeze(self):
        path = self.root / 'versions/v1.1/content/spec.json'
        spec = read(path); spec['requirements'][0].update(status='pending', blocking=True)
        write(path, spec)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/project.py'), 'freeze', str(self.root)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(read(self.root / 'project.json')['versions'][0]['status'], 'planning')

    def test_migration_preserves_legacy_content_and_backup(self):
        legacy = pathlib.Path(self.temp.name) / 'legacy'
        shutil.copytree(self.root / 'versions/v1.0/content', legacy / 'content')
        shutil.copytree(ROOT / 'template/site', legacy / 'site')
        original = hashes(legacy / 'content')
        subprocess.run([sys.executable, str(ROOT / 'scripts/project.py'), 'migrate', str(legacy)], check=True, capture_output=True)
        self.assertEqual(original, hashes(legacy / 'content'))
        self.assertEqual(original, hashes(legacy / 'migration-backup/content'))
        self.assertEqual(validate(legacy)[0], [])

    def test_legacy_duplicate_page_ids_across_modules(self):
        legacy = pathlib.Path(self.temp.name) / 'old'
        (legacy / 'content').mkdir(parents=True)
        (legacy / 'content/a.md').write_text('# Old document', encoding='utf-8')
        page = {'id': 'index', 'title': 'Index', 'type': 'markdown', 'file': 'a.md', 'source': 'origin', 'status': 'confirmed'}
        write(legacy / 'content/manifest.json', {'product': {'name': 'old', 'form': 'web'}, 'modules': [
            {'id': 'overview', 'title': 'Overview', 'pages': [page]},
            {'id': 'testing', 'title': 'Testing', 'pages': [page]}]})
        shutil.copytree(ROOT / 'template/site', legacy / 'site')
        subprocess.run([sys.executable, str(ROOT / 'scripts/project.py'), 'migrate', str(legacy)], check=True, capture_output=True)
        self.assertEqual(validate(legacy)[0], [])

    def test_impact_detects_revision_after_checkpoint(self):
        path = self.root / 'versions/v1.1/content/spec.json'
        spec = read(path); spec['requirements'][0]['rules']['输入与校验'] = '最多 60 字'
        write(path, spec)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/project.py'), 'impact', str(self.root)], check=True, capture_output=True, text=True)
        self.assertIn('changed_since_checkpoint', result.stdout)
        self.assertIn('FR-ORDER-001', result.stdout)


if __name__ == '__main__':
    unittest.main()
