#!/usr/bin/env python3
"""Create an executable two-version reference project in an empty output directory."""
import pathlib
import shutil
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'template'))
from projectlib import read, write


def command(root, *args):
    subprocess.run([sys.executable, str(SKILL / 'scripts/project.py'), args[0], str(root), *args[1:]], check=True)


def requirement(rid, title, description, rules, given, when, then):
    return {'id': rid, 'title': title, 'description': description, 'source': 'ai-inferred', 'status': 'confirmed',
            'blocking': False, 'rules': rules, 'acceptance': [{'id': rid.replace('FR', 'AC'), 'given': given, 'when': when, 'then': then}]}


def generate(root):
    command(root, 'init', '--name', '订单管理 · 交付演示', '--form', 'web', '--version', 'v1.0')
    vr = root / 'versions/v1.0/content'
    assets = vr / 'prototype/assets'
    assets.mkdir(parents=True)
    for name in ('prototype-runtime.js', 'prototype-runtime.css', 'annotation-store.js'):
        shutil.copy2(SKILL / 'assets' / name, assets / name)
    for name in ('list.html', 'detail.html'):
        shutil.copy2(SKILL / 'examples/order-demo' / name, vr / 'prototype' / name)
    for name in ('demo.js', 'demo.css'):
        shutil.copy2(SKILL / 'examples/order-demo' / name, assets / name)
    m = read(vr / 'manifest.json')
    def page(pid, title, kind, file=None):
        result = {'id': pid, 'title': title, 'type': kind, 'source': 'ai-inferred', 'status': 'confirmed'}
        if file: result['file'] = file
        return result
    m['modules'] += [
        {'id': 'requirements', 'title': '需求文档', 'layout': 'continuous', 'pages': [page('spec', '页面需求与验收', 'spec')]},
        {'id': 'prototype', 'title': '交互原型', 'pages': [page('order-list', '订单列表', 'prototype', 'prototype/list.html'), page('order-detail', '订单详情', 'prototype', 'prototype/detail.html')]},
        {'id': 'testing', 'title': '验收与测试', 'pages': [page('testing', '关键路径测试', 'markdown', 'testing/index.md')]},
        {'id': 'launch', 'title': '上线计划', 'pages': [page('launch', '上线范围与回退', 'markdown', 'launch/index.md')]}
    ]
    m['modules'][0]['pages'][0]['status'] = 'confirmed'
    write(vr / 'manifest.json', m)
    (vr / 'overview/index.md').write_text('# V1.0 · 基础订单\n\n本示例为合成演示数据，确认状态仅用于测试版本冻结，并非真实产品决策。\n\n目标：开发能够操作创建、查阅订单的完整流程。\n\n范围：订单列表、搜索、创建与详情。排除：真实支付、接口、用户登录。\n\n> 🤖 **AI 推断**：本示例用于检验工具能力。\n', encoding='utf-8')
    for folder, content in {
        'testing': '# 关键路径\n\n- TC-001：创建订单 → 列表出现 → 打开详情 → 返回列表。\n- TC-002：空名称不能提交；提交失败保留输入；重试只创建一条。\n- TC-003：无权限时不能创建；切换正常状态恢复。\n- TC-004：打开需求面板 → 拖拽 → 定位元素 → 停靠 → 收起。\n',
        'launch': '# 上线范围与回退\n\n本项目仅为交互演示，不连接真实业务系统。\n\n- [ ] 开发与产品完成关键路径评审\n- [ ] 待决策规则已明确\n- [ ] 实际上线前另行确认部署、监控与回退负责人\n'
    }.items():
        (vr / folder).mkdir()
        (vr / folder / 'index.md').write_text(content, encoding='utf-8')
    reqs = [
        requirement('FR-ORDER-001', '创建订单', '用户从列表创建订单，并立即查看新记录。', {'显示规则': '正常、空数据、请求失败场景可创建；加载中及无权限时禁用。', '输入与校验': '订单名称必填，去除首尾空格后 1～40 字；提交时校验，错误定位字段。', '提交反馈': '提交中禁用按钮；成功关闭弹框、刷新列表；重复点击不重复创建。', '异常与边界': '请求失败保留输入并可重试；权限失效阻止提交。'}, '处于正常场景且名称有效', '提交订单', '列表增加一笔订单并可进入详情'),
        requirement('FR-ORDER-002', '查阅订单', '用户搜索订单并打开详情，返回时保留演示数据。', {'显示规则': '默认按演示数据顺序排列，新订单位于首行；列表滚动查看。', '跳转': '详情按钮打开首笔订单；详情返回订单列表。', '筛选规则': '按名称进行不区分大小写的包含匹配。', '异常与边界': '空态、加载、错误、无权限通过场景选择器演示；无数据时详情按钮禁用。'}, '已有订单', '打开详情后返回', '详情显示首笔订单，返回后订单仍存在')
    ]
    interactions = []
    def interaction(iid, pid, selector, rid, action, description, target=None):
        it = {'id': iid, 'page': pid, 'selector': '#' + selector, 'requirement_ids': [rid], 'action': action, 'description': description, 'level': 'crit' if action in {'submit', 'dialog'} else 'info'}
        if target: it['target'] = target
        interactions.append(it)
    interaction('INT-SEARCH', 'order-list', 'search', 'FR-ORDER-002', 'input', '输入名称即时筛选订单')
    interaction('INT-CREATE', 'order-list', 'create', 'FR-ORDER-001', 'dialog', '打开创建弹框，加载及无权限时禁用', 'create-dialog')
    interaction('INT-NAME', 'order-list', 'order-name', 'FR-ORDER-001', 'input', '必填 1～40 字，空白名称不可提交')
    interaction('INT-CANCEL', 'order-list', 'cancel', 'FR-ORDER-001', 'close', '取消并关闭弹框', 'create-dialog')
    interaction('INT-SUBMIT', 'order-list', 'submit', 'FR-ORDER-001', 'submit', '校验、提交、禁重复；失败保留输入')
    interaction('INT-DETAIL', 'order-list', 'detail', 'FR-ORDER-002', 'navigate', '打开第一笔订单详情', 'order-detail')
    interaction('INT-BACK', 'order-detail', 'back', 'FR-ORDER-002', 'navigate', '返回列表并保留订单', 'order-list')
    # V1.0 excludes the future batch action, visibly disabled if inspected.
    html = (vr / 'prototype/list.html').read_text(encoding='utf-8').replace('id="batch" type="button" hidden', 'id="batch" type="button" hidden disabled data-out-of-scope="V1.1 批量完成"')
    (vr / 'prototype/list.html').write_text(html, encoding='utf-8')
    spec = {'requirements': reqs, 'pages': [
        {'id': 'order-list', 'title': '订单列表', 'purpose': '查阅并创建订单。', 'requirement_ids': ['FR-ORDER-001', 'FR-ORDER-002']},
        {'id': 'order-detail', 'title': '订单详情', 'purpose': '查阅当前订单，返回列表。', 'requirement_ids': ['FR-ORDER-002']}
    ], 'interactions': interactions}
    reqs[0]['rules']['角色权限（合成演示）'] = 'operator 可创建；viewer 仅查看，不可创建或批量修改；guest 使用无权限场景。非真实产品权限决策。'
    spec['replay_cases'] = [
        {'id': cid, 'title': title, 'role': role, 'scenario': scenario,
         'pages': ['order-list', 'order-detail'], 'requirement_ids': ['FR-ORDER-002'],
         'source': 'ai-inferred', 'status': 'pending',
         'state': {'orders': orders, 'filter': ''}}
        for cid, title, role, scenario, orders in [
            ('operator-ready', '待处理订单', 'operator', 'normal', [{'name': '合成订单 A', 'status': '待处理'}]),
            ('viewer-ready', '只读查看', 'viewer', 'normal', [{'name': '合成订单 A', 'status': '待处理'}]),
            ('operator-empty', '空数据', 'operator', 'empty', []),
            ('operator-error', '请求失败', 'operator', 'error', []),
            ('guest-denied', '无权限', 'guest', 'forbidden', [])
        ]
    ]
    write(vr / 'spec.json', spec)
    command(root, 'build')
    command(root, 'checkpoint')
    command(root, 'freeze')
    command(root, 'status', '--state', 'developing')
    command(root, 'status', '--state', 'released')
    command(root, 'new-version', '--version', 'v1.1', '--name', '批量完成')
    vr = root / 'versions/v1.1/content'
    spec['requirements'].append(requirement('FR-ORDER-003', '批量完成订单', '一键完成当前演示数据中的全部待处理订单。', {'显示规则': '仅 V1.1 显示；无待处理订单、非正常场景时禁用。', '操作规则': '点击后全部待处理订单变为已完成，刷新列表并提示结果。', '范围': '本示例操作全部订单，不包含逐条勾选；真实产品需评审批量范围。'}, '有待处理订单', '点击批量完成', '订单全部完成且按钮禁用'))
    batch_req = spec['requirements'][-1]
    batch_req['rule_details'] = [{'id': 'RULE-BATCH-COMPLETE', 'category': 'state',
        'statement': batch_req['rules'].pop('操作规则'), 'source': 'ai-inferred', 'status': 'pending',
        'examples': [{'input': '正常场景下有两条待处理订单', 'expected': '两条订单均变为已完成，批量按钮禁用'}],
        'acceptance_ids': ['AC-ORDER-003']}]
    spec['pages'][0]['requirement_ids'].append('FR-ORDER-003')
    interaction('INT-BATCH', 'order-list', 'batch', 'FR-ORDER-003', 'custom', '完成全部待处理订单，刷新状态并禁用按钮')
    interactions[-1]['rule_ids'] = ['RULE-BATCH-COMPLETE']
    name_req = spec['requirements'][0]
    name_req['rule_details'] = [{'id': 'RULE-NAME-INPUT', 'category': '字段与校验',
        'statement': name_req['rules'].pop('输入与校验'), 'source': 'ai-inferred', 'status': 'pending',
        'examples': [{'input': '仅含空格', 'expected': '拒绝提交并定位名称字段'}], 'acceptance_ids': ['AC-ORDER-001']}]
    next(i for i in interactions if i['id'] == 'INT-NAME')['rule_ids'] = ['RULE-NAME-INPUT']
    interaction('INT-FEEDBACK', 'order-list', 'feedback', 'FR-ORDER-002', 'inspect', '列表状态提示（只读）')
    write(vr / 'spec.json', spec)
    html = (vr / 'prototype/list.html').read_text(encoding='utf-8').replace(' hidden disabled data-out-of-scope="V1.1 批量完成"', '').replace('id="feedback"', 'id="feedback" data-business-value')
    (vr / 'prototype/list.html').write_text(html, encoding='utf-8')
    (vr / 'overview/index.md').write_text('# V1.1 · 批量完成\n\n新增：FR-ORDER-003 批量完成全部待处理订单。\n\n继承：V1.0 创建、查阅、搜索、异常场景。\n\n不做：逐条勾选、真实接口。\n\n> 🤖 **AI 推断**：合成演示，非真实产品需求。\n', encoding='utf-8')
    command(root, 'build')
    command(root, 'impact')
    command(root, 'checkpoint')
    return root


if __name__ == '__main__':
    generate(pathlib.Path(sys.argv[1]).resolve())
