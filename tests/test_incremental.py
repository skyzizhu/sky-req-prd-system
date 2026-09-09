import copy
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from revise_item import locate, lookup, patch, page_context
from editlib import state, save, Conflict
from projectlib import hashes, spec_markdown


class IncrementalTests(unittest.TestCase):
    def test_html_and_precise_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'demo'
            subprocess.run([sys.executable,str(ROOT/'scripts/create_demo.py'),str(root)],check=True,capture_output=True)
            html=root/'versions/v1.1/content/prototype/list.html'
            self.assertEqual(locate(str(html)),(root.resolve(),'v1.1'))
            self.assertEqual(locate((root/'site/index.html').as_uri()+'#/v/v1.1/prototype/order-list')[1],'v1.1')
            with self.assertRaises(ValueError): locate(str(html),'v1.0')
            with self.assertRaises(ValueError): locate(str(root))
            old=state(root,'v1.1'); frozen=hashes(root/'versions/v1.0')
            self.assertEqual(page_context(root,'v1.1','order-list')['html'],str(html.resolve()))
            scoped=lookup(old,'','order-detail')
            self.assertTrue(any(x['item']['id']=='INT-BACK' for x in scoped))
            self.assertFalse(any(x['item']['id']=='INT-CREATE' for x in scoped))
            with self.assertRaises(ValueError): page_context(root,'v1.1','missing')
            rejected=subprocess.run([sys.executable,str(ROOT/'scripts/revise_item.py'),str(root),'--version','v1.1','--page','order-detail','--id','INT-CREATE','--save'],capture_output=True,text=True)
            self.assertNotEqual(rejected.returncode,0)
            self.assertIn('不属于指定页面',rejected.stderr)
            self.assertTrue(lookup(old,'RULE-NAME-INPUT'))
            payload=patch(old,'FR-ORDER-001','rule_details/RULE-NAME-INPUT/statement','名称校验规则已局部修订')
            saved=save(root,'v1.1',payload)
            new=state(root,'v1.1')
            self.assertTrue(saved['saved'])
            self.assertEqual(old['spec']['requirements'][1:],new['spec']['requirements'][1:])
            self.assertEqual(old['spec']['interactions'],new['spec']['interactions'])
            self.assertEqual(old['documents'],new['documents'])
            self.assertEqual(frozen,hashes(root/'versions/v1.0'))
            save(root,'v1.1',patch(new,'INT-NAME','properties/maxLength',60))
            controls=state(root,'v1.1')['spec']['interactions']
            self.assertEqual(next(i for i in controls if i['id']=='INT-NAME')['properties']['maxLength'],60)
            self.assertEqual([i for i in old['spec']['interactions'] if i['id']!='INT-NAME'],[i for i in controls if i['id']!='INT-NAME'])
            with self.assertRaises(Conflict): save(root,'v1.1',payload)
            for field in ('id','rule_details','rule_details/0/statement'):
                with self.assertRaises(ValueError): patch(new,'FR-ORDER-001',field,'bad')
            with self.assertRaises(Conflict): save(root,'v1.0',patch(state(root,'v1.0'),'FR-ORDER-001','description','bad'))

    def test_business_first_export(self):
        spec={'requirements':[{'id':'FR-1','title':'创建订单','description':'业务正文','source':'origin','status':'pending','rules':{'输入校验':'必须填写名称'},'acceptance':[{'id':'AC-1','given':'已登录','when':'提交','then':'列表新增'}]}], 'pages':[], 'interactions':[]}
        before=copy.deepcopy(spec); md=spec_markdown(spec)
        self.assertIn('## 创建订单',md)
        self.assertNotIn('## FR-1',md)
        for text in ('业务正文','必须填写名称','前提：已登录','操作：提交','预期：列表新增','FR-1','AC-1'): self.assertIn(text,md)
        self.assertEqual(before,spec)
