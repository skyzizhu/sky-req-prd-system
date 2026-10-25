import copy
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'template'))
from prdlib import feature_list, scope_with_features

class VersionFeatureListTests(unittest.TestCase):
    def test_new_modified_removed_and_retained_are_distinct(self):
        base={'requirements':[{'id':'A','title':'创建','description':'创建记录'},{'id':'B','title':'查阅','description':'查看详情'},{'id':'C','title':'导出','description':'导出文件'}]}
        current=copy.deepcopy(base)
        current['requirements'][0]['description']='创建后返回列表'
        current['requirements'].pop()
        current['requirements'].append({'id':'D','title':'搜索','description':'按名称搜索'})
        rows=feature_list(current,base)
        self.assertEqual({row['id']:row['change'] for row in rows},{'A':'修改','B':'沿用','C':'移除','D':'新增'})
        self.assertEqual(next(row['summary'] for row in rows if row['id']=='A'),'创建后返回列表')

    def test_confirming_a_rule_does_not_add_function_scope(self):
        base={'requirements':[{'id':'A','title':'创建','status':'pending','rule_details':[{'id':'R','statement':'必填','source':'ai-inferred','status':'pending'}]}]}
        current=copy.deepcopy(base)
        current['requirements'][0]['status']='confirmed'
        current['requirements'][0]['rule_details'][0]['status']='confirmed'
        self.assertEqual(feature_list(current,base)[0]['change'],'沿用')
        self.assertEqual(base['requirements'][0]['status'],'pending')

    def test_first_version_lists_all_functions(self):
        rows=feature_list({'requirements':[{'id':'A','module':'订单','title':'创建','description':'创建订单','priority':'P0'}]})
        self.assertEqual(rows[0]['change'],'新增')
        self.assertEqual(rows[0]['module'],'订单')
        self.assertEqual(rows[0]['priority'],'P0')

    def test_pending_rule_is_visible_even_if_feature_is_confirmed(self):
        spec={'requirements':[{'id':'A','title':'创建','status':'confirmed','rule_details':[{'id':'R','statement':'上限待定','status':'pending'}]}]}
        self.assertEqual(feature_list(spec)[0]['status'],'pending')


class ScopeReadingOrderTests(unittest.TestCase):
    def test_background_subsections_stay_together_before_feature_list(self):
        body='### 背景与目标\n背景说明\n\n#### 成功目标\n目标说明\n\n```md\n### 示例标题\n```\n\n### 本次做\n范围说明'
        result=scope_with_features(body,'### 本版功能清单\n清单内容')
        self.assertLess(result.index('目标说明'),result.index('本版功能清单'))
        self.assertLess(result.index('示例标题'),result.index('本版功能清单'))
        self.assertLess(result.index('本版功能清单'),result.index('本次做'))
        self.assertEqual(result.count('背景说明'),1)

    def test_background_moves_ahead_of_existing_metadata(self):
        result=scope_with_features('### 基本信息\n负责人待定\n\n### 背景与目标\n目标说明\n\n### 本次不做\n排除项','### 本版功能清单')
        self.assertTrue(result.startswith('### 背景与目标'))
        self.assertLess(result.index('本版功能清单'),result.index('基本信息'))
        self.assertIn('排除项',result)

    def test_missing_background_is_not_fabricated(self):
        result=scope_with_features('简短说明\n\n### 范围\n范围说明','### 本版功能清单')
        self.assertEqual(result,'简短说明\n\n### 本版功能清单\n\n### 范围\n范围说明')
        self.assertNotIn('背景与目标',result)
