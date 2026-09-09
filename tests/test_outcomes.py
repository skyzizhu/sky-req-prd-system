import copy
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'template'))
sys.path.insert(0, str(ROOT / 'scripts'))
from record_outcome import append
from outcomelib import report
from projectlib import read, write, hashes, compile_project, check_build, validate


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name) / 'demo'
        subprocess.run([sys.executable, str(ROOT / 'scripts/create_demo.py'), str(self.root)], check=True, capture_output=True)
        self.p = {'kind':'execution','version':'v1.0','requirement_id':'FR-ORDER-001','acceptance_id':'AC-ORDER-001',
                  'scope':'prototype','result':'passed','environment':'离线演示','build':'合成原型',
                  'actor':'测试工具（合成记录）','observed_at':'2026-09-09T12:00:00+08:00','evidence':['测试示例，无真实验收'],
                  'notes':'合成记录','follow_up':{'target_version':'v1.1','owner':'产品（示例）','action':'复核空输入'}}

    def test_frozen_append_correction_and_build(self):
        before = hashes(self.root / 'versions/v1.0')
        record = append(self.root, self.p)
        self.assertTrue(check_build(self.root))
        compile_project(self.root)
        self.assertEqual(check_build(self.root), [])
        correction = copy.deepcopy(self.p); correction.update(supersedes=record['id'], result='failed')
        append(self.root, correction)
        values = report(self.root, read(self.root/'project.json'))
        self.assertTrue(values[0]['superseded'])
        self.assertFalse(values[1]['stale'])
        self.assertEqual(before, hashes(self.root / 'versions/v1.0'))
        with self.assertRaises(ValueError): append(self.root, correction)

    def test_invalid_no_write(self):
        for changes in [{'evidence':[]}, {'scope':'real-ish'}, {'acceptance_id':'AC-MISSING'},
                        {'observed_at':'2026-09-09'}, {'follow_up':{'target_version':'v1.0','owner':'p','action':'x'}}]:
            value = copy.deepcopy(self.p); value.update(changes)
            with self.assertRaises(ValueError): append(self.root, value)
        self.assertFalse(list((self.root/'outcomes').glob('*.json')))

    def test_stale_and_editor_preserves_observations(self):
        from editlib import state, save
        self.p['version']='v1.1'; self.p.pop('follow_up')
        append(self.root,self.p); compile_project(self.root)
        current = state(self.root,'v1.1')
        spec = copy.deepcopy(current['spec']); spec['requirements'][0]['title']='已修订标题'
        save(self.root,'v1.1',{'revision':current['revision'],'spec':spec,'documents':current['documents']})
        self.assertTrue(report(self.root,read(self.root/'project.json'))[0]['stale'])
        self.assertIn('合成记录', (self.root/'site/js/data.js').read_text())
        self.assertEqual(check_build(self.root), [])
        self.assertEqual(validate(self.root)[0], [])

    def test_measurement_and_not_run(self):
        p = {'kind':'measurement','version':'v1.0','goal':'提高创建成功率','metric':'成功次数/尝试次数',
             'baseline':'待补','target':'待确认','actual':'尚无样本','window':'上线后七日（示例）',
             'data_source':'示例报表','decision':'inconclusive','actor':'产品','observed_at':self.p['observed_at'],
             'evidence':['样本不足说明'],'notes':'不能据此宣称提升'}
        append(self.root,p)
        self.p.update(result='not_run',evidence=[])
        append(self.root,self.p)
        self.assertEqual(len(report(self.root, read(self.root/'project.json'))),2)
