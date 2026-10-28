#!/usr/bin/env python3
"""Review delivery, list agent tasks/business decisions, package static and complete source copies."""
if __name__ == '__main__':
    from project_guard import dispatch
    dispatch(__file__)
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, urlunsplit
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read
import skilllocklib
from review_delivery import review, save
from delivery_info import delivery_info


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('本地入口不应跳转，请检查服务根目录')


def source_files(root, static=False):
    excluded = {'.git', '__pycache__', '.upgrade-backup', '.editing'}
    for file in sorted(root.rglob('*')):
        rel = file.relative_to(root)
        if any(p in excluded for p in rel.parts) or file.name == '.DS_Store' or file.suffix == '.pyc':
            continue
        if static and (rel.parts[0] not in ('site', 'versions', 'attachments', 'outcomes') or any(p.startswith('.') for p in rel.parts) or file.suffix == '.py'):
            continue
        if file.is_symlink():
            raise ValueError('请先将项目符号链接转为实际文件后打包：' + str(rel))
        if file.is_file():
            yield rel.as_posix(), file.read_bytes()


def package(target, entries, status):
    entries = dict(entries)
    if 'delivery-manifest.json' in entries:
        raise ValueError('项目占用了保留文件名 delivery-manifest.json')
    manifest = {'schema_version': 1, 'status': status,
                'files': {key: hashlib.sha256(value).hexdigest() for key, value in entries.items()}}
    # Exclusive creation: a second run never overwrites a prior delivery.
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for key, value in entries.items():
            archive.writestr(key, value)
        archive.writestr('delivery-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))


BUSINESS_CODES = {'input_decision', 'feature_decision', 'mobile_decision', 'diagram_decision',
                  'requirement_blocking', 'rules_pending', 'diagram_pending'}


def split_work(report):
    # Blocking business choices retain their original severity; missing chapters/evidence are Agent work.
    business = [i for i in report['quality']['issues'] if i['code'] in BUSINESS_CODES]
    business += [i for i in report['semantic'] if i.get('impact') == 'business_question']
    agent = [{'path': 'structure', 'message': e} for e in report['structure']['errors']]
    agent += [i for i in report['quality']['issues'] if i['code'] not in BUSINESS_CODES]
    agent += report['controls']['findings']
    agent += [i for i in report['semantic'] if i['verdict'] == 'unverified' or (i['verdict'] == 'fail' and i.get('impact') != 'business_question')]
    return agent, business


def prepare(root, base_url, out, inputs=(), evidence_file=None, draft=False, rubric_file=None):
    root, out = Path(root).resolve(), Path(out).resolve()
    inputs = [Path(p).resolve() for p in inputs]
    if out == root or out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError('交付目录须在项目外，不能是项目的父目录')
    if out.exists() and any(out.iterdir()):
        raise ValueError('交付目录须为空，避免覆盖已有报告或物料')
    protected = inputs + [Path(p).resolve() for p in (evidence_file, rubric_file) if p]
    if any(p.is_relative_to(out) for p in protected):
        raise ValueError('输出目录不能包含输入或复核证据')
    errors = skilllocklib.verify(root)
    if not skilllocklib.load(root):
        errors.append('正式打包前须明确采用并锁定技能版本')
    if errors:
        raise ValueError('\n'.join(errors))
    info = delivery_info(root, base_url)
    # Check the exact local entry; prohibit proxy/redirect and compare it to the saved artifact.
    url = urlsplit(info['localhost_url'])
    request_url = urlunsplit((url.scheme, url.netloc, url.path, '', ''))
    with build_opener(ProxyHandler({}), NoRedirect()).open(request_url, timeout=5) as response:
        if response.status != 200 or response.read() != (root / 'site/index.html').read_bytes():
            raise ValueError('本地服务入口未返回200或不是本项目的HTML')
    source_entries = list(source_files(root))
    external_entries = [(file, file.read_bytes()) for file in protected]
    report = review(root, inputs=inputs, evidence=read(evidence_file) if evidence_file else None,
                    rubric=read(rubric_file) if rubric_file else None)
    if source_entries != list(source_files(root)) or any(file.read_bytes() != data for file, data in external_entries):
        raise ValueError('审查期间源项目或输入/证据发生变化，请重新审查；未生成交付包')
    agent, decisions = split_work(report)
    ready = report['status'] == 'review_recorded'
    summary = dict(info, status='ready' if ready else 'review_draft', review_status=report['status'],
                   skill_version=skilllocklib.load(root)['version'], agent_todo=agent, business_decisions=decisions,
                   packages={}, limitations=report['limitations'])
    summary['limits'] = '已核对本机入口200及HTML身份；未发布或发送。复核记录不等于真实产品验收。'
    out.mkdir(parents=True, exist_ok=True)
    save(report, out / 'delivery-review')
    if ready or draft:
        label = 'ready' if ready else 'review-draft'
        extras = [('delivery-review.json', json.dumps(report, ensure_ascii=False, indent=2).encode())]
        # Source backup contains original inputs/evidence even when they live outside the project.
        source_extra = list(extras)
        mapping = []
        for index, (file, data) in enumerate(external_entries):
            key = 'delivery-sources/' + str(index + 1) + '-' + file.name
            source_extra.append((key, data))
            mapping.append({'original': str(file), 'archived': key})
        source_extra.append(('delivery-sources/index.json', json.dumps(mapping, ensure_ascii=False, indent=2).encode()))
        for kind, static, extra in [('static', True, extras), ('source', False, source_extra)]:
            target = out / (kind + '-' + label + '.zip')
            entries = [(key, data) for key, data in source_entries if not static or (key.split('/')[0] in ('site', 'versions', 'attachments', 'outcomes') and not any(part.startswith('.') for part in Path(key).parts) and Path(key).suffix != '.py')]
            if set(k for k, _ in entries) & set(k for k, _ in extra):
                raise ValueError('源项目包含与交付报告冲突的保留路径')
            package(target, entries + extra, summary['status'])
            summary['packages'][kind] = str(target)
    (out / 'delivery-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project', type=Path); p.add_argument('--url', required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--input', type=Path, action='append', default=[]); p.add_argument('--evidence', type=Path)
    p.add_argument('--rubric', type=Path); p.add_argument('--draft', action='store_true', help='未就绪时也输出明确标为评审稿的包')
    a = p.parse_args()
    try:
        result = prepare(a.project, a.url, a.out, a.input, a.evidence, a.draft, a.rubric)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'ready' else 3
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('交付准备失败：' + str(error), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
