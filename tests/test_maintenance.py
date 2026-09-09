import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from maintain import catalog,patch_document
from save_notes import publish
from editlib import state,save,undo,Conflict
from projectlib import read,hashes,check_build
import materiallib
import notelib

class MaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=tempfile.TemporaryDirectory();cls.base=pathlib.Path(cls.fixture.name)/'base'
        subprocess.run([sys.executable,str(ROOT/'scripts/create_demo.py'),str(cls.base)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.fixture.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)/'project';shutil.copytree(self.base,self.root)
    def tearDown(self):self.temp.cleanup()
    def note(self):
        return dict(schema_version=2,project=read(self.root/'project.json')['id'],version='v1.1',page='order-list',hidden=[],overrides=[],reviews=[],custom=[dict(id='manual-test',selector='#create',description='评审说明',level='info',x=.5,y=.5)])
    def test_exact_block_patch_undo_and_conflict(self):
        s=state(self.root,'v1.1');s['documents']['prd/risks.md']='<!-- material: RISK-1 -->\n# 风险一\n原文\n<!-- material: RISK-2 -->\n# 风险二\n原文'
        save(self.root,'v1.1',s);s,items=catalog(self.root,'v1.1')
        self.assertTrue(any(i['key']=='block:prd/risks.md#RISK-1' for i in items))
        frozen=hashes(self.root/'versions/v1.0')
        result=patch_document(self.root,'v1.1','prd/risks.md','RISK-1','原文','修改',s['revision'],True)
        self.assertTrue(result['saved']);self.assertEqual(state(self.root,'v1.1')['documents']['prd/risks.md'].count('原文'),1)
        self.assertEqual(frozen,hashes(self.root/'versions/v1.0'))
        with self.assertRaises(Conflict):patch_document(self.root,'v1.1','prd/risks.md',None,'原文','x',s['revision'],True)
        undo(self.root,'v1.1',dict(undo_id=result['undo_id'],revision=state(self.root,'v1.1')['revision']))
        self.assertEqual(state(self.root,'v1.1')['documents'],s['documents'])
        with self.assertRaises(ValueError):materiallib.replace('重复 重复',None,'重复','x')
    def test_shared_notes_save_undo_and_formal_protection(self):
        before=state(self.root,'v1.1');frozen=hashes(self.root/'versions/v1.0')
        result=publish(self.root,'v1.1',self.note(),before['revision'])
        self.assertTrue(result['saved']);self.assertEqual(result['state']['spec']['requirements'],before['spec']['requirements'])
        self.assertEqual(frozen,hashes(self.root/'versions/v1.0'));self.assertEqual(check_build(self.root),[])
        bad=self.note();bad['hidden']=['INT-CREATE']
        with self.assertRaises(ValueError):publish(self.root,'v1.1',bad,result['state']['revision'])
        with self.assertRaises(Conflict):publish(self.root,'v1.1',self.note(),before['revision'])
        undo(self.root,'v1.1',dict(undo_id=result['undo_id'],revision=result['state']['revision']))
        self.assertEqual(before['spec'],state(self.root,'v1.1')['spec'])
    def test_append_version_preserves_identity_and_old_links(self):
        script=str(ROOT/'scripts/project.py');before=read(self.root/'project.json');history=hashes(self.root/'versions/v1.0');entry=self.root/'site/index.html';shell=entry.read_bytes()
        args=[sys.executable,script,'new-version',str(self.root),'--version','v1.2']
        rejected=subprocess.run(args,capture_output=True);self.assertNotEqual(rejected.returncode,0);self.assertFalse((self.root/'versions/v1.2').exists())
        subprocess.run(args+['--from-version','v1.1'],check=True,capture_output=True)
        after=read(self.root/'project.json');self.assertEqual(before['id'],after['id']);self.assertEqual(after['current_version'],'v1.2')
        self.assertEqual(history,hashes(self.root/'versions/v1.0'));self.assertEqual(shell,entry.read_bytes());self.assertEqual(check_build(self.root),[])
        self.assertTrue((self.root/'versions/v1.0/content/prototype/list.html').is_file())
    def test_stale_export_cannot_replace_saved_notes(self):
        first=publish(self.root,'v1.1',self.note(),state(self.root,'v1.1')['revision'])
        stale=self.note();stale['custom'][0]['description']='旧草稿覆盖'
        with self.assertRaises(Conflict):publish(self.root,'v1.1',stale,first['state']['revision'])
        fresh=self.note();fresh['base_revision']=notelib.digest(first['state']['spec']['review_notes']['order-list']);fresh['custom'][0]['description']='已核对后修改'
        result=publish(self.root,'v1.1',fresh,first['state']['revision'])
        self.assertEqual(result['state']['spec']['review_notes']['order-list']['custom'][0]['description'],'已核对后修改')
    def test_table_row_index_and_invalid_shared_notes(self):
        items=materiallib.index({'modules':[]},{},{'test.md':'| 编号 | 说明 |\n| --- | --- |\n| TC-001 | 必填校验 |'})
        self.assertTrue(any(i['key']=='row:test.md#TC-001' for i in items))
        bad=self.note();del bad['custom']
        with self.assertRaises(ValueError):notelib.validate({'order-list':bad},state(self.root,'v1.1')['spec'])
