import base64
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from editlib import state, save, Conflict
from attachments import upload, verify_type
from projectlib import hashes, check_build, validate, read
import prdlib


class StandardPRDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.base = pathlib.Path(cls.fixture.name) / 'base'
        subprocess.run([sys.executable, str(ROOT/'scripts/create_demo.py'), str(cls.base)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)/'project'
        shutil.copytree(self.base, self.root)

    def tearDown(self): self.temp.cleanup()

    def payload(self, version='v1.1'):
        return dict(name='需求说明.txt', description='访谈依据', requirement_ids=[], share_ack=True,
                    data=base64.b64encode('参考资料'.encode()).decode(), revision=state(self.root, version)['revision'])

    def test_standard_sources_save_and_export(self):
        draft = state(self.root, 'v1.1')
        self.assertEqual(len(draft['prd_registry']['sections']), 9)
        draft['documents']['prd/tracking.md'] = '<!-- prd-status: provided -->\n\n# 数据与埋点\n\n点击提交成功后记录订单提交事件。'
        save(self.root, 'v1.1', draft)
        self.assertEqual(check_build(self.root), [])
        data=(self.root/'site/js/data.js').read_text()
        for word in ('点击提交成功后', '非功能需求', '里程碑与计划', '风险与待决策'):
            self.assertIn(word, data)
        self.assertIn('prd/tracking.md', state(self.root,'v1.1')['documents'])

    def test_status_and_single_function_source(self):
        with self.assertRaises(ValueError): prdlib.document('<!-- prd-status: not_applicable -->\n正文')
        with self.assertRaises(ValueError): prdlib.document('<!-- prd-status: provided -->\n# 标题')
        self.assertEqual(prdlib.document('旧版正文')['status'], 'pending')
        self.assertEqual(prdlib.document('<!-- prd-status: not_applicable -->\n<!-- prd-reason: 无外部依赖 -->')['status'], 'not_applicable')

    def test_upload_unique_persistent_and_survives_edit(self):
        first=upload(self.root, 'v1.1', self.payload())
        second=upload(self.root, 'v1.1', self.payload())
        self.assertNotEqual(first['attachment']['id'],second['attachment']['id'])
        self.assertEqual(len(second['state']['attachments']),2)
        file=self.root/'attachments'/first['attachment']['id']/'file.txt'
        self.assertEqual(file.read_text(),'参考资料')
        draft=second['state']; draft['documents']['prd/appendix.md']='# 附录\n\n补充依据说明'
        save(self.root,'v1.1',draft)
        self.assertEqual(len(state(self.root,'v1.1')['attachments']),2)
        self.assertEqual(check_build(self.root),[])

    def test_frozen_append_does_not_modify_snapshot(self):
        before=hashes(self.root/'versions/v1.0')
        result=upload(self.root,'v1.0',self.payload('v1.0'))
        self.assertTrue(result['state']['attachments'][0]['late_addition'])
        self.assertEqual(before,hashes(self.root/'versions/v1.0'))
        self.assertEqual(validate(self.root)[0],[])

    def test_rejections_and_integrity(self):
        p=self.payload(); p['share_ack']=False
        with self.assertRaises(ValueError): upload(self.root,'v1.1',p)
        for name,raw in [('x.html',b'<html>'),('../x.txt',b'x'),('x.pdf',b'not pdf'),('x.txt',b'')]:
            with self.assertRaises(ValueError): verify_type(name,raw)
        p=self.payload(); result=upload(self.root,'v1.1',p)
        with self.assertRaises(Conflict): upload(self.root,'v1.1',p)
        file=self.root/'attachments'/result['attachment']['id']/'file.txt'
        file.write_text('篡改')
        self.assertTrue(validate(self.root)[0])
