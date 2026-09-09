#!/usr/bin/env python3
"""Read-only, evidence-limited rule completeness audit. Never marks a project ready."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read, safe


def audit(spec):
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
    return {'requirements_checked': len(requirements), 'rules_checked': len(seen),
            'issues': issues, 'scope': '仅检查已记录规则的结构、实例和关联；不证明业务正确、交互通过或开发就绪'}


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
        report = audit(read(safe(root, f'versions/{vid}/content/spec.json')))
        report.update(project=project['id'], version=vid)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(args.strict and bool(report['issues']))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'检查失败：{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
