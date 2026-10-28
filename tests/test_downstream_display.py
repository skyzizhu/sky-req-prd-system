import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
import projectlib
import prdlib


class DownstreamDisplayTests(unittest.TestCase):
    def test_display_preserves_false_empty_and_option_values(self):
        self.assertEqual(projectlib.property_display('required', False), '否')
        self.assertEqual(projectlib.property_display('defaultValue', ''), '空')
        self.assertEqual(projectlib.property_display('options', [{'label':'邮件','value':'email'}]), '邮件（值：email）')
        self.assertEqual(projectlib.property_display('width', 'full'), '占满可用宽度')
        self.assertEqual(projectlib.property_display('pattern', '[0-9]+'), '[0-9]+')

    def test_projection_keeps_source_and_state_location(self):
        spec={'pages':[{'id':'settings','title':'通知设置','states':[{'id':'default','title':'首次进入'}]}],
              'interactions':[{'id':'INT-CHANNEL','page':'settings','description':'推送渠道','requirement_ids':['FR-1'],'state_ids':['default'],'properties':{'defaultValue':'','required':False}}]}
        before=copy.deepcopy(spec)
        item=projectlib.control_supplements(spec)[0]
        self.assertEqual(item['states'], '首次进入')
        self.assertEqual(item['items'], [{'label':'默认值','value':'空'},{'label':'必填','value':'否'}])
        self.assertEqual(spec,before)

    def test_shared_pending_differs_from_reading_reference(self):
        own={'id':'A','title':'预约','status':'confirmed','rule_details':[{'id':'RULE-A','status':'confirmed','related_rule_ids':['RULE-SHARED']}],'shared_rule_ids':[]}
        common={'id':'B','title':'权限','status':'confirmed','rule_details':[{'id':'RULE-SHARED','status':'pending'}]}
        spec={'requirements':[own,common]}
        self.assertEqual(prdlib.feature_list(spec)[0]['status'],'confirmed')
        baseline=copy.deepcopy(spec)
        own['shared_rule_ids']=['RULE-SHARED']
        self.assertEqual(prdlib.feature_list(spec,baseline)[0]['status'],'pending')
        self.assertEqual(prdlib.feature_list(spec,baseline)[0]['change'],'修改')
        self.assertEqual(own['status'],'confirmed')
