import copy
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from editlib import state, save, undo, prepare, Conflict, revision
from edit_project import server
from projectlib import read, write, hashes, check_build


class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.base = pathlib.Path(cls.fixture.name) / 'base'
        subprocess.run([sys.executable, str(ROOT / 'scripts/create_demo.py'), str(cls.base)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / 'project'
        shutil.copytree(self.base, self.root)
        self.draft = state(self.root, 'v1.1')
        self.draft['spec']['requirements'][0]['title'] = '编辑后的创建订单'

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_save_undo_preserves_history_and_baseline(self):
        history = hashes(self.root / 'versions/v1.0')
        baseline = (self.root / 'versions/v1.1/.baseline.json').read_bytes()
        original = state(self.root, 'v1.1')
        report = prepare(self.root, 'v1.1', self.draft)[3]
        self.assertIn('order-list', report['review_pages'])
        self.assertEqual(original, state(self.root, 'v1.1'))
        result = save(self.root, 'v1.1', self.draft)
        self.assertEqual(result['state']['spec']['requirements'][0]['status'], 'pending')
        self.assertEqual(check_build(self.root), [])
        self.assertEqual(history, hashes(self.root / 'versions/v1.0'))
        self.assertEqual(baseline, (self.root / 'versions/v1.1/.baseline.json').read_bytes())
        restored = undo(self.root, 'v1.1', {'undo_id': result['undo_id'], 'revision': result['state']['revision']})
        self.assertEqual(original['spec'], restored['state']['spec'])
        self.assertEqual(check_build(self.root), [])

    def test_stale_source_and_frozen_rejected(self):
        file = self.root / 'versions/v1.1/content/overview/index.md'
        file.write_text('用户手工修改', encoding='utf-8')
        with self.assertRaises(Conflict): save(self.root, 'v1.1', self.draft)
        self.assertEqual(file.read_text(), '用户手工修改')
        with self.assertRaises(Conflict): save(self.root, 'v1.0', state(self.root, 'v1.0'))

    def test_invalid_candidate_does_not_touch_live_files(self):
        before = revision(self.root)
        self.draft['spec']['requirements'][0]['acceptance'] = []
        with self.assertRaises(ValueError): save(self.root, 'v1.1', self.draft)
        self.assertEqual(before, revision(self.root))

    def test_markdown_and_path_limit(self):
        self.assertTrue(self.draft['editable'])
        self.draft['documents']['overview/index.md'] = '# 修改后的版本目标'
        result = save(self.root, 'v1.1', self.draft)
        self.assertIn('order-detail', result['impact']['review_pages'])
        self.assertIn('修改后的版本目标', (self.root / 'site/js/data.js').read_text())
        candidate = result['state']
        candidate['documents']['../../../outside.md'] = 'no'
        with self.assertRaises(ValueError): save(self.root, 'v1.1', candidate)

    def test_rule_diff_and_unknown_fields_preserved(self):
        self.draft['spec']['requirements'][0]['custom'] = {'owner': 'PM'}
        result = save(self.root, 'v1.1', self.draft)
        draft = copy.deepcopy(result['state'])
        draft['spec']['requirements'][0]['rule_details'][0]['statement'] = '最多 60 字'
        result = save(self.root, 'v1.1', draft)
        self.assertTrue(any('RULE-NAME-INPUT/statement' in c['path'] for c in result['impact']['changes']))
        self.assertEqual(result['state']['spec']['requirements'][0]['custom'], {'owner': 'PM'})

    def test_undo_refuses_intervening_change(self):
        result = save(self.root, 'v1.1', self.draft)
        (self.root / 'versions/v1.1/content/overview/index.md').write_text('后续人工修改')
        with self.assertRaises(Conflict): undo(self.root, 'v1.1', {'undo_id': result['undo_id'], 'revision': result['state']['revision']})

    def test_write_failure_rolls_back(self):
        before = revision(self.root)
        original = pathlib.Path.replace
        def fail(path, target):
            if path.name.endswith('.editing-tmp'):
                raise OSError('模拟磁盘写入失败')
            return original(path, target)
        with patch.object(pathlib.Path, 'replace', fail):
            with self.assertRaises(OSError): save(self.root, 'v1.1', self.draft)
        self.assertEqual(before, revision(self.root))

    def test_http_token_and_origin(self):
        service, url = server(self.root, 'v1.1')
        thread = threading.Thread(target=service.serve_forever, daemon=True)
        thread.start()
        base, token = url.split('/#token=')
        try:
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(base + '/api/state')
            self.assertEqual(denied.exception.code, 403)
            req = urllib.request.Request(base + '/api/state', headers={'X-Editor-Token': token})
            with urllib.request.urlopen(req) as response:
                self.assertEqual(json.load(response)['version'], 'v1.1')
            req = urllib.request.Request(base + '/api/save', data=json.dumps(self.draft).encode(), headers={'X-Editor-Token': token, 'Content-Type': 'application/json', 'Origin': 'https://example.com'})
            with self.assertRaises(urllib.error.HTTPError) as denied: urllib.request.urlopen(req)
            self.assertEqual(denied.exception.code, 403)
        finally:
            service.shutdown(); service.server_close(); thread.join()

    def test_freeze_after_load_and_interrupted_save_blocked(self):
        project = read(self.root / 'project.json')
        project['versions'][0]['status'] = 'frozen'
        write(self.root / 'project.json', project)
        with self.assertRaises(Conflict): save(self.root, 'v1.1', self.draft)
        project['versions'][0]['status'] = 'planning'
        write(self.root / 'project.json', project)
        write(self.root / '.editing/interrupted.json', {'status': 'prepared'})
        with self.assertRaises(Conflict): save(self.root, 'v1.1', state(self.root, 'v1.1'))

    def test_cli_state_and_preview(self):
        command = [sys.executable, str(ROOT / 'scripts/edit_project.py'), str(self.root), '--version', 'v1.1']
        loaded = json.loads(subprocess.run(command + ['--action', 'state'], check=True, capture_output=True, text=True).stdout)
        loaded['spec']['requirements'][0]['title'] = 'CLI 修改草稿'
        package = pathlib.Path(self.temp.name) / 'draft.json'
        write(package, loaded)
        output = json.loads(subprocess.run(command + ['--action', 'preview', '--payload', str(package)], check=True, capture_output=True, text=True).stdout)
        self.assertTrue(output['impact']['changes'])
        self.assertNotEqual(state(self.root, 'v1.1')['spec']['requirements'][0]['title'], 'CLI 修改草稿')

    def test_prototype_properties_save_undo_and_invalid(self):
        draft = state(self.root, 'v1.1')
        name = next(i for i in draft['spec']['interactions'] if i['id'] == 'INT-NAME')
        name['properties'] = {'maxLength': 60, 'placeholder': '输入新名称', 'width': 'full'}
        before = state(self.root, 'v1.1')
        result = save(self.root, 'v1.1', draft)
        self.assertIn('INT-NAME', result['impact']['review_interactions'])
        self.assertIn('"maxLength": 60', (self.root / 'versions/v1.1/content/prototype/assets/spec-data.js').read_text())
        self.assertEqual(result['state']['spec']['requirements'][0]['status'], 'pending')
        restored = undo(self.root, 'v1.1', {'revision': result['state']['revision'], 'undo_id': result['undo_id']})
        self.assertEqual(before['spec'], restored['state']['spec'])
        for properties in ({'onclick': 'alert(1)'}, {'maxLength': -1}, {'maxLength': True}, {'width': '999px'}, {'text': '破坏输入框'}):
            draft = state(self.root, 'v1.1')
            next(i for i in draft['spec']['interactions'] if i['id'] == 'INT-NAME')['properties'] = properties
            with self.assertRaises(ValueError): save(self.root, 'v1.1', draft)

    def test_prototype_invalid_target_and_old_runtime(self):
        draft = state(self.root, 'v1.1')
        next(i for i in draft['spec']['interactions'] if i['id'] == 'INT-CREATE')['target'] = 'does-not-exist'
        before = revision(self.root)
        with self.assertRaises(ValueError): save(self.root, 'v1.1', draft)
        self.assertEqual(before, revision(self.root))
        runtime = self.root / 'versions/v1.1/content/prototype/assets/prototype-runtime.js'
        runtime.write_text('/* old version */')
        draft = state(self.root, 'v1.1')
        next(i for i in draft['spec']['interactions'] if i['id'] == 'INT-NAME')['properties'] = {'maxLength': 60}
        with self.assertRaisesRegex(ValueError, '尚不支持'): prepare(self.root, 'v1.1', draft)

    def test_review_reconciles_actual_edit_record(self):
        from review_notes import reconcile
        result=save(self.root,'v1.1',self.draft)
        notes={'schema_version':1,'project':read(self.root/'project.json')['id'],'version':'v1.1','page':'order-list',
               'reviews':[{'id':'INT-CREATE','status':'completed','requirement_ids':['FR-ORDER-001'],'change_ref':result['undo_id'],'evidence':'人工验证记录'}]}
        report=reconcile(self.root,notes)
        self.assertTrue(report['reviews'][0]['change_record_verified'])
        notes['reviews'][0]['change_ref']='external-ticket'
        self.assertFalse(reconcile(self.root,notes)['reviews'][0]['change_record_verified'])
        notes['project']='other'
        with self.assertRaises(ValueError): reconcile(self.root,notes)


if __name__ == '__main__': unittest.main()
