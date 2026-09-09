#!/usr/bin/env python3
"""Read-only, evidence-limited rule completeness audit. Never marks a project ready."""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read, safe

SCRIPT_SRC = re.compile(r'<script[^>]+src="([^"]+)"')
BINDING_PRIMITIVE = re.compile(r'addEventListener\s*\(|\.on(?:click|submit|change|input)\s*=')


def page_script_text(version_dir):
    """按原型页面汇总其引用的本地 JS 文本（排除编译生成的 spec-data，避免声明本身造成假阳性）。"""
    manifest = read(version_dir / 'content/manifest.json')
    result = {}
    for module in manifest.get('modules', []):
        for page in module.get('pages', []):
            if page.get('type') != 'prototype':
                continue
            html_path = version_dir / 'content' / page['file']
            chunks = []
            for src in SCRIPT_SRC.findall(html_path.read_text(encoding='utf-8')):
                name = src.split('#')[0].split('?')[0]
                if name.endswith('spec-data.js'):
                    continue
                target = html_path.parent / name
                if target.is_file():
                    chunks.append(target.read_text(encoding='utf-8'))
            result[page['id']] = '\n'.join(chunks)
    return result


def audit(spec, version_dir=None):
    issues = []
    seen = set()

    def issue(path, message):
        issues.append({'path': path, 'message': message})

    requirements = spec.get('requirements', [])
    if not isinstance(requirements, list):
        raise ValueError('requirements 必须为数组')
    if not requirements:
        issue('requirements', '没有需求可检查')
    for index, req in enumerate(requirements):
        if not isinstance(req, dict):
            issue(f'requirements/{index}', '需求必须为对象')
            continue
        path = str(req.get('id', index))
        details = req.get('rule_details')
        if not isinstance(details, list) or not details:
            issue(path, '缺少 rule_details：尚不能检查规则级实例及验收关联')
            continue
        acceptance = req.get('acceptance', [])
        ac_ids = {a.get('id') for a in acceptance if isinstance(a, dict) and isinstance(a.get('id'), str)} if isinstance(acceptance, list) else set()
        for n, rule in enumerate(details):
            rp = f'{path}/rule_details/{n}'
            if not isinstance(rule, dict):
                issue(rp, '规则必须为对象')
                continue
            rid = rule.get('id')
            if not isinstance(rid, str) or not rid.strip():
                issue(rp, '缺少规则 ID')
            elif rid in seen:
                issue(rp, f'规则 ID 重复：{rid}')
            else:
                seen.add(rid)
            for field in ('category', 'statement'):
                if not isinstance(rule.get(field), str) or not rule[field].strip():
                    issue(rp, f'缺少 {field}')
            if rule.get('source') not in ('origin', 'ai-inferred'):
                issue(rp, '缺少合法来源')
            if rule.get('status') not in ('pending', 'confirmed'):
                issue(rp, '缺少合法确认状态')
            elif rule['status'] == 'pending':
                issue(rp, '规则尚待确认')
            examples = rule.get('examples')
            if not isinstance(examples, list) or not examples:
                issue(rp, '缺少具体实例')
            else:
                for e in examples:
                    if not isinstance(e, dict) or not all(isinstance(e.get(k), str) and e[k].strip() for k in ('input', 'expected')):
                        issue(rp, '实例需要非空 input 和 expected')
            refs = rule.get('acceptance_ids')
            if not isinstance(refs, list) or not refs:
                issue(rp, '缺少验收关联')
            elif any(not isinstance(ref, str) or ref not in ac_ids for ref in refs):
                issue(rp, '验收关联必须指向当前需求的验收 ID')
    # PS_DECLARATION_CHECK_V1：声明由页面 JS 实现的控件，必须在页面脚本中留有绑定痕迹；
    # 字符串级检查只能提示，不能证明行为正确（装饰性按钮靠它兜底，最终仍需浏览器实测）。
    if version_dir is not None:
        try:
            scripts = page_script_text(version_dir)
        except (OSError, ValueError, KeyError, TypeError):
            scripts = None
        if scripts is not None:
            for it in spec.get('interactions', []):
                if not isinstance(it, dict) or it.get('action') not in ('custom', 'submit', 'input'):
                    continue
                selector = it.get('selector') or ''
                element_id = selector[1:] if selector.startswith('#') else ''
                page_scripts = scripts.get(it.get('page'))
                if not element_id or page_scripts is None:
                    continue
                if element_id not in page_scripts:
                    issue(str(it.get('id') or selector),
                          f'声明了 {it.get("action")} 动作，但页面脚本未见对 #{element_id} 的任何引用（需人工确认，避免装饰性控件）')
                elif not BINDING_PRIMITIVE.search(page_scripts):
                    issue(str(it.get('id') or selector),
                          f'页面脚本引用了 #{element_id}，但整个页面未见事件绑定原语（addEventListener/on*），需人工确认行为是否实现')
    return {'requirements_checked': len(requirements), 'rules_checked': len(seen),
            'issues': issues, 'scope': '仅检查已记录规则的结构、实例和关联（含声明/实现绑定提示）；不证明业务正确、交互通过或开发就绪'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=pathlib.Path)
    parser.add_argument('--version')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        project = read(root / 'project.json')
        vid = args.version or project['current_version']
        if vid not in [v['id'] for v in project['versions']]:
            raise ValueError('版本不存在')
        report = audit(read(safe(root, f'versions/{vid}/content/spec.json')), safe(root, f'versions/{vid}'))
        report.update(project=project['id'], version=vid)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(args.strict and bool(report['issues']))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'检查失败：{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
