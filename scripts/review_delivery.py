#!/usr/bin/env python3
"""Read-only delivery review: reuse quality checks, inspect native controls, record semantic evidence."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read, safe, validate, check_build
from audit_quality import project_report

DIMENSIONS = {
    'input_scope': '对照原始方案逐条核对纳入、排除、依赖与独立约束，不能仅复核生成台账',
    'rule_closure': '按功能核对对象、前提、条件、行为、结果、适用边界及异常恢复，无依据的取舍保持待确认',
    'consistency': '核对输入、规则、控件数据、状态、流程图与验收的业务含义一致；自动断言也需核对来源',
    'flow_paths': '从原始方案和GWT逐条走图：校验拒绝、失败后修正再重试、未知与核实；核对条件、去向、副作用，不从现有连线反推完整性，无流程时说明不适用',
    'annotation_scope': '逐控件/操作及状态核对必要规则：基础约束、当前可操作性、禁用原因、结果及恢复；区分关闭/确认/背景限制，不能按整个功能批量绑定',
    'redundancy': '查找重复正文、泛化标注和无关说明；保留必要的上下文投影及独立边界',
    'acceptance': '逐分支核对具体验收的前提、触发、预期，不以编号关联代替语义覆盖',
    'mobile_delivery': '涉及移动App/H5/小程序时，对照原方案核对平台、导航返回、中断恢复、系统授权及组件状态；从规则追至画板和验收，不以窄屏测试替代；非移动项目说明不适用',
    'browser': '实际查看独立页、iframe、状态及局部变化、编号与控件、键盘和窄屏；对照基础页查漏控件，核对多个界面的独立画板、标题/间隔、触发关系与控件保留；记录观察证据',
}
BOOLEAN = {'required', 'disabled', 'multiple', 'checked', 'readonly'}
ATTRIBUTES = {'type', 'min', 'max', 'step', 'maxlength', 'minlength', 'pattern', 'placeholder'}
PROPERTIES = BOOLEAN | ATTRIBUTES | {'value', 'options'}


class Controls(HTMLParser):
    """Authored HTML only. CSS visibility and live interaction require browser evidence."""
    VOID = {'input', 'img', 'br', 'hr', 'meta', 'link', 'source', 'area', 'base', 'col', 'embed', 'param', 'track', 'wbr'}

    def __init__(self):
        super().__init__(); self.stack = []; self.nodes = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        parent = self.stack[-1] if self.stack else None
        node = {'tag': tag, 'attrs': a, 'text': '', 'children': [],
                'state': a.get('data-ps-state', parent['state'] if parent else None),
                'hidden': 'hidden' in a or bool(parent and parent['hidden']),
                'option_disabled': 'disabled' in a or bool(parent and parent['tag']=='optgroup' and parent['option_disabled']),
                'snapshot': 'sr-snapshot' in a.get('class', '').split() or bool(parent and parent['snapshot'])}
        if parent: parent['children'].append(node)
        self.nodes.append(node)
        if tag not in self.VOID: self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]; break

    def handle_data(self, data):
        for node in self.stack: node['text'] += data

    def values(self, node):
        a = node['attrs']; result = {k: k in a for k in BOOLEAN}
        result.update({k: a.get(k) for k in ATTRIBUTES})
        if node['tag'] == 'select':
            options = [n for n in descendants(node) if n['tag'] == 'option']
            result['options'] = [{'value': o['attrs'].get('value', o['text'].strip()), 'label': o['attrs'].get('label', o['text'].strip())} for o in options]
            selected = [o for o in options if 'selected' in o['attrs']]
            if 'multiple' not in a:
                try: size = int(a.get('size', '1'))
                except ValueError: size = 1
                selected = selected[-1:] or ([o for o in options if not o['option_disabled']][:1] if size <= 1 else [])
            values = [o['attrs'].get('value', o['text'].strip()) for o in selected]
            result['value'] = values if 'multiple' in a else (values[0] if values else '')
        elif node['tag'] == 'textarea': result['value'] = node['text']
        else: result['value'] = a.get('value', 'on' if a.get('type') in ('radio', 'checkbox') else '')
        return result


def descendants(node):
    for child in node['children']:
        yield child
        yield from descendants(child)


def surface_review(spec, pages):
    """Check independent delivery artboards and preserved controls; CSS needs browser review."""
    findings = []
    inventories = {(p['id'], s['id']): s.get('elements', []) for p in spec.get('pages', []) for s in p.get('states', [])}
    contains = lambda parent, child: any(n is child for n in descendants(parent))
    for pid, parser in pages.items():
        for section in [n for n in parser.nodes if n['attrs'].get('data-ps-state')]:
            sid=section['state']; path=pid+'/'+sid+'/surface'
            def issue(code,message): findings.append(dict(code=code,path=path,message=message))
            current=[n for n in descendants(section) if n['snapshot']]
            cards=[n for n in current if 'sr-artboard' in n['attrs'].get('class','').split()]
            dialogs=[n for n in current if n['attrs'].get('data-ps-surface') in ('dialog','drawer') or n['tag']=='dialog' or n['attrs'].get('role') in ('dialog','alertdialog')]
            if not cards and not dialogs: continue
            stacks=[n for n in current if 'data-ps-artboards' in n['attrs'] and 'sr-snapshot' in n['attrs'].get('class','').split()]
            if len(cards)<2 or not any(all(any(c is card for c in stack['children']) for card in cards) for stack in stacks):
                issue('surface_artboards_missing','多个界面须在同一画布中用至少两个上下排列的独立sr-artboard展示')
            for card in cards:
                if any(contains(other,card) for other in cards if other is not card):issue('surface_embedded','界面画板不能嵌入另一画板的白色容器')
                for cls in ('sr-artboard-title','sr-artboard-body'):
                    matches=[n for n in card['children'] if cls in n['attrs'].get('class','').split()]
                    if len(matches)!=1 or (cls.endswith('title') and not matches[0]['text'].strip()):issue('surface_structure_missing','每个画板需独立标题和内容容器：'+cls)
                if 'inert' in card['attrs'] or card['attrs'].get('aria-modal')=='true':issue('surface_artboard_inactive','交付画板须可独立阅读，不按真实模态封锁其他画板')
            for dialog in dialogs:
                if not any(dialog is card for card in cards):
                    issue('surface_dialog_embedded','弹窗/抽屉须作为独立画板呈现，不能使用页面内嵌或覆盖效果');continue
                trigger=dialog['attrs'].get('data-ps-trigger')
                targets=[n for n in parser.nodes if n['snapshot'] and '#'+n['attrs'].get('id','')==trigger]
                if len(targets)!=1 or targets[0]['tag'] not in ('button','a','input') or targets[0]['hidden'] or 'disabled' in targets[0]['attrs'] or contains(dialog,targets[0]):
                    issue('surface_trigger_invalid','弹窗画板须关联外部真实可用的触发控件data-ps-trigger')
                if not any('sr-artboard-caption' in n['attrs'].get('class','').split() and n['text'].strip() for n in dialog['children']):issue('surface_trigger_description_missing','弹窗画板需直接可读的触发关系说明')
            base=section['attrs'].get('data-ps-base-state')
            if not base: continue
            if base==sid or (pid,base) not in inventories:
                issue('surface_base_invalid','基础状态data-ps-base-state无效');continue
            base_nodes=[n for n in parser.nodes if n['state']==base and n['snapshot']]
            copies=[n for card in cards if card['attrs'].get('data-ps-surface')=='page' for n in descendants(card)]
            required={e['selector'] for e in inventories[(pid,base)] if isinstance(e,dict) and e.get('selector')}
            required.update('#'+n['attrs']['id'] for n in base_nodes if not n['hidden'] and n['tag'] in ('button','input','select','textarea','a') and n['attrs'].get('id'))
            for origin in sorted(required):
                preserved=[n for n in copies if n['attrs'].get('data-ps-origin')==origin]
                originals=[n for n in base_nodes if '#'+n['attrs'].get('id','')==origin]
                if len(preserved)!=1 or len(originals)!=1 or preserved[0]['tag']!=originals[0]['tag'] or preserved[0]['hidden']:
                    issue('surface_control_missing','关联页面遗漏或替换基础元素：'+origin+'；保留真实控件并用data-ps-origin关联')
    return findings


def control_review(spec, content):
    pages = {}; findings = []; comparisons = []; checked = set()
    manifest = read(content/'manifest.json')
    for module in manifest.get('modules', []):
        for page in module.get('pages', []):
            if page.get('type') != 'prototype': continue
            parser = Controls(); parser.feed(safe(content, page['file']).read_text(encoding='utf-8'))
            pages[page['id']] = parser
    if manifest.get('product',{}).get('form') in ('mobile','h5','miniapp'):
        for pid,parser in pages.items():
            for snapshot in [n for n in parser.nodes if 'sr-snapshot' in n['attrs'].get('class','').split()]:
                boards=[n for n in descendants(snapshot) if 'sr-artboard' in n['attrs'].get('class','').split()]
                targets=boards or [snapshot]
                if any(n['attrs'].get('data-ps-platform')!='mobile' for n in targets):
                    findings.append(dict(code='mobile_canvas_missing',path=pid+'/'+str(snapshot['state']),message='移动产品画板需显式data-ps-platform=mobile；窄屏阅读器不能代替移动画布'))
    rules = {r['id'] for req in spec.get('requirements', []) for r in req.get('rule_details', [])}
    for i, check in enumerate(spec.get('quality', {}).get('control_checks', [])):
        path = 'quality.control_checks/'+str(i)
        expected = check.get('expected', {})
        refs = check.get('rule_ids', [])
        if not refs or any(r not in rules for r in refs) or not expected or set(expected)-PROPERTIES:
            findings.append(dict(code='control_contract_invalid', path=path, message='需有效规则引用及支持的 expected 属性')); continue
        if any(type(expected[k]) is not bool for k in BOOLEAN & expected.keys()):
            findings.append(dict(code='control_contract_invalid', path=path, message='布尔属性须为 true/false')); continue
        parser = pages.get(check.get('page'))
        matches = [n for n in parser.nodes if n['snapshot'] and n['state'] == check.get('state') and '#'+n['attrs'].get('id', '') == check.get('selector')] if parser else []
        if len(matches) != 1 or matches[0]['tag'] not in ('input', 'select', 'textarea', 'button'):
            findings.append(dict(code='control_target_invalid', path=path, message='控件目标须为对应状态内唯一原生控件 ID')); continue
        actual = parser.values(matches[0])
        node = matches[0]
        annotations = [it for it in spec.get('interactions', []) if it.get('page') == check['page']
                       and (not it.get('state_ids') or check['state'] in it['state_ids'])
                       and (it.get('selector') == check['selector'] or it.get('id') == node['attrs'].get('data-rule-ref'))]
        bound = {rid for it in annotations for rid in it.get('rule_ids', [])}
        missing = sorted(set(refs)-bound)
        if missing:
            findings.append(dict(code='control_annotation_mismatch', path=path,
                                 message='控件属性所依据的规则未在当前状态标注中完整关联',
                                 evidence=dict(page=check['page'], state=check['state'], selector=check['selector'],
                                               expected=refs, actual=sorted(bound), missing=missing)))
        checked.add((check['page'], check['state'], check['selector']))
        for key, value in expected.items():
            row = dict(path=path, page=check['page'], state=check['state'], selector=check['selector'], rule_ids=refs, property=key, expected=value, actual=actual.get(key))
            comparisons.append(row)
            if value != actual.get(key):
                findings.append(dict(code='control_mismatch', path=path, message='原型控件与规则派生断言不一致', evidence=row))
    unchecked = [dict(page=pid, state=n['state'], selector='#'+n['attrs']['id']) for pid, parser in pages.items() for n in parser.nodes if n['snapshot'] and n['tag'] in ('input', 'select', 'textarea', 'button') and n['attrs'].get('id') and (pid, n['state'], '#'+n['attrs']['id']) not in checked]
    findings.extend(surface_review(spec,pages))
    return dict(findings=findings, comparisons=comparisons, unchecked_controls=unchecked)


def fingerprint(root, version, inputs):
    for file in inputs:
        if not file.is_file(): raise ValueError('原始输入文件不存在：'+str(file))
    files = [root/'project.json'] + sorted(root.glob('*.py')) + sorted((root/'site').rglob('*')) + sorted((safe(root, 'versions/'+version)/'content').rglob('*')) + list(inputs)
    digest = hashlib.sha256()
    for file in files:
        if file.is_file():
            digest.update(str(file.resolve()).encode()); digest.update(b'\0'); digest.update(file.read_bytes()); digest.update(b'\0')
    return digest.hexdigest()


def review(root, version=None, inputs=(), evidence=None, rubric=None):
    project = read(root/'project.json'); vid = version or project['current_version']
    if vid not in [v['id'] for v in project['versions']]: raise ValueError('版本不存在')
    content = safe(root, 'versions/'+vid)/'content'; spec = read(content/'spec.json')
    errors, warnings = validate(root); errors += check_build(root)
    quality = project_report(root, vid)
    controls = control_review(spec, content) if spec.get('quality', {}).get('scope', {}).get('prototype') else dict(findings=[], comparisons=[], unchecked_controls=[])
    token = hashlib.sha256((fingerprint(root, vid, inputs) + json.dumps(rubric, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    questions = dict(DIMENSIONS)
    if rubric:
        for item in rubric['checks']:
            if item['id'] in questions: raise ValueError('评测核对项 ID 重复')
            questions[item['id']] = item['expectation']
    evidence = evidence or {}
    if evidence and evidence.get('fingerprint') != token: raise ValueError('复核证据已过期或不属于本次源文件，请重新审查')
    records = evidence.get('checks', {})
    if set(records)-questions.keys(): raise ValueError('未知复核项')
    semantic = []
    for key, question in questions.items():
        item = records.get(key, {'verdict':'unverified'})
        if item.get('verdict') not in ('pass', 'fail', 'not_applicable', 'unverified'): raise ValueError('无效复核结论')
        if item['verdict'] != 'unverified':
            if not item.get('evidence') or not isinstance(item['evidence'], list) or not all(isinstance(e, str) and e.strip() for e in item['evidence']): raise ValueError('已复核结论必须提供非空定位及观察证据')
            if item['verdict'] == 'fail' and (item.get('impact') not in ('blocker','suggestion','business_question') or not item.get('recommendation')): raise ValueError('问题须说明影响级别及具体修改建议')
        if key == 'input_scope' and not inputs and item['verdict'] in ('pass','not_applicable'): raise ValueError('未提供原始方案文件，不能声称输入核对通过或不适用')
        semantic.append(dict(id=key, question=question, **item))
    failed = bool(errors or quality['counts']['errors'] or controls['findings'] or any(s['verdict']=='fail' for s in semantic))
    pending = any(s['verdict']=='unverified' for s in semantic) or any(i['severity']=='decision' for i in quality['issues'])
    return dict(schema_version=1, project=project['id'], version=vid, fingerprint=token,
                status='issues_found' if failed else 'review_required' if pending else 'review_recorded',
                structure=dict(errors=errors, warnings=warnings), quality=quality, controls=controls,
                semantic=semantic, inputs=[str(p) for p in inputs],
                flow_paths=[dict(diagram=d['id'], **path) for d in spec.get('diagrams',[]) for path in d.get('path_reviews',[]) if isinstance(path,dict)],
                limitations=['自动断言是规则的派生核对证据，不是第二套业务规则；未登记属性不推定一致。', '静态 HTML 不证明 CSS 可见性、运行时联动、流程图语义或业务确认；复核证据为 Agent/人工记录，并非脚本独立证明。'])


def save(report, prefix):
    prefix = Path(prefix); prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(str(prefix)+'.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 交付审查', '', '结论：'+report['status'], '', '源指纹：'+report['fingerprint'], '', '## 自动检测', '']
    lines += ['- '+s for s in report['structure']['errors']]
    lines += ['- 警告：'+s for s in report['structure']['warnings']]
    lines += ['- '+i['path']+'：'+i['message'] for i in report['quality']['issues']]
    lines += ['- '+i['path']+'：'+i['message']+'；证据：'+json.dumps(i.get('evidence',{}),ensure_ascii=False) for i in report['controls']['findings']]
    lines += ['', '已登记场景路径：'+str(len(report['flow_paths']))]
    lines += ['', '控件属性断言：'+str(len(report['controls']['comparisons']))+'；未登记控件：'+str(len(report['controls']['unchecked_controls'])), '', '## 语义与实际界面复核', '']
    for row in report['semantic']:
        lines += ['- '+row['id']+' · '+row['verdict']+'：'+row['question']]
        lines += ['  - '+e for e in row.get('evidence', [])]
        if row.get('impact'): lines += ['  - '+row['impact']+'：'+row.get('recommendation','')]
    lines += ['', *report['limitations']]
    Path(str(prefix)+'.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path); parser.add_argument('--version')
    parser.add_argument('--input', type=Path, action='append', default=[])
    parser.add_argument('--evidence', type=Path); parser.add_argument('--rubric', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        root=args.project.resolve()
        targets = [Path(str(args.report)+suffix).resolve() for suffix in ('.json','.md')]
        protected = {p.resolve() for p in args.input + [p for p in (args.evidence,args.rubric) if p]}
        if any(p.is_relative_to(root) or p in protected for p in targets): raise ValueError('报告必须放在项目外，且不能覆盖原始输入、复核证据或评测标准')
        report = review(root, args.version, [p.resolve() for p in args.input], read(args.evidence) if args.evidence else None, read(args.rubric) if args.rubric else None)
        save(report, args.report); print(report['status'])
        return 1 if report['status']=='issues_found' else 3 if report['status']=='review_required' else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('审查失败：'+str(error), file=sys.stderr); return 2


if __name__ == '__main__': sys.exit(main())
