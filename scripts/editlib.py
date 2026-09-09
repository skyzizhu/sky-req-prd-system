"""Local PRD editing with optimistic concurrency, staged validation and recoverable saves."""
import copy
import datetime
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import uuid
import fcntl

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read, write, safe, hashes, pages, validate, compile_project, HTMLCheck, property_errors
import prdlib
import attachmentlib
import notelib


class Conflict(ValueError):
    pass


def diff(before, after, path=''):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        return [item for key in sorted(before.keys() | after.keys())
                for item in diff(before.get(key), after.get(key), path + '/' + key)]
    if isinstance(before, list) and isinstance(after, list) and all(isinstance(x, dict) and isinstance(x.get('id'), str) for x in before + after):
        return diff({x['id']: x for x in before}, {x['id']: x for x in after}, path)
    return [{'path': path, 'before': before, 'after': after}]


def revision(root):
    # Includes generated files, metadata, manually edited sources, and frozen snapshots.
    result = {}
    for base in ('project.json', 'config.md', 'versions', 'site', 'outcomes', 'attachments'):
        p = root / base
        if p.is_symlink():
            raise ValueError('编辑项目不支持符号链接：' + base)
        if p.is_file():
            result[base] = hashlib.sha256(p.read_bytes()).hexdigest()
        elif p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_symlink():
                    raise ValueError('编辑项目不支持符号链接：' + str(f.relative_to(root)))
                if f.is_file() and '__pycache__' not in f.parts:
                    result[str(f.relative_to(root))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()


def state(root, vid):
    project = read(root / 'project.json')
    version = next((v for v in project['versions'] if v['id'] == vid), None)
    if not version:
        raise ValueError('版本不存在')
    vr = safe(root, 'versions/' + vid)
    manifest = read(vr / 'content/manifest.json')
    documents = {p['file']: safe(vr / 'content', p['file']).read_text(encoding='utf-8')
                 for p in pages(manifest) if p['type'] == 'markdown'}
    registry = prdlib.registry(vr / 'content')
    if registry:
        for section in registry['sections']:
            for source in section['sources']:
                documents[source] = safe(vr / 'content', source).read_text(encoding='utf-8')
    specfile = vr / 'content/spec.json'
    prototype_elements = {}
    prototype_previews = {}
    for p in pages(manifest):
        if p['type'] == 'prototype':
            parser = HTMLCheck()
            file = safe(vr / 'content', p['file'])
            html = file.read_text(encoding='utf-8')
            parser.feed(html)
            prototype_elements[p['id']] = parser.elements
            css = []
            for ref in parser.refs:
                if ref.endswith('.css') and not ref.startswith(('http:', 'https:', '//')):
                    css.append(safe(vr / 'content', str(file.parent.relative_to(vr / 'content') / ref)).read_text(encoding='utf-8'))
            prototype_previews[p['id']] = {'html': html, 'css': '\n'.join(css)}
    return {'project': project['name'], 'version': vid, 'editable': version['status'] == 'planning',
            'attachments': attachmentlib.for_version(root, project, vid), 'prd_registry': registry,
            'revision': revision(root), 'spec': read(specfile) if specfile.exists() else None,
            'documents': documents, 'prototype_elements': prototype_elements, 'prototype_previews': prototype_previews}


def impact(before, after, docs_before, docs_after):
    old = {r['id']: r for r in (before or {}).get('requirements', [])}
    new = {r['id']: r for r in (after or {}).get('requirements', [])}
    changed = {rid for rid in old.keys() | new.keys() if old.get(rid) != new.get(rid)}
    old_it = {i['id']: i for i in (before or {}).get('interactions', [])}
    new_it = {i['id']: i for i in (after or {}).get('interactions', [])}
    changed_it = {iid for iid in old_it.keys() | new_it.keys() if old_it.get(iid) != new_it.get(iid)}
    changed.update(rid for iid in changed_it for it in (old_it.get(iid, {}), new_it.get(iid, {})) for rid in it.get('requirement_ids', []))
    specs = [before or {}, after or {}]
    changed_docs = sorted(k for k in docs_before.keys() | docs_after.keys() if docs_before.get(k) != docs_after.get(k))
    # A document change has no reliable structured graph; conservatively request review of every page.
    affected = lambda item: bool(changed_docs or set(item.get('requirement_ids', [])) & changed)
    return {'changes': diff(before, after) + diff(docs_before, docs_after, '/documents'),
            'requirements': sorted(changed),
            'review_pages': sorted({p['id'] for s in specs for p in s.get('pages', []) if affected(p)}),
            'review_interactions': sorted({i['id'] for s in specs for i in s.get('interactions', []) if affected(i)}),
            'review_acceptance': sorted({a['id'] for r in list(old.values()) + list(new.values()) if changed_docs or r['id'] in changed for a in r.get('acceptance', [])}),
            'documents': changed_docs,
            'notice': 'PRD 和原型需求数据在保存后重新编译；原型业务脚本、独立测试文档及实际行为需按影响清单复核。正文变化按全页面保守复核。未自动 checkpoint。'}


def candidate(current, payload):
    spec = copy.deepcopy(payload.get('spec', current['spec']))
    documents = payload.get('documents', current['documents'])
    if not isinstance(documents, dict) or documents.keys() != current['documents'].keys() or any(not isinstance(v, str) for v in documents.values()):
        raise ValueError('只能编辑 manifest 已登记的 Markdown 文件正文')
    if spec != current['spec']:
        if not isinstance(spec, dict) or not isinstance(current['spec'], dict):
            raise ValueError('请先通过需求工作流建立结构化 PRD')
        # Only declarative properties/targets of existing interactions are editable.
        for key in spec.keys() | current['spec'].keys():
            if key not in {'requirements', 'interactions', 'review_notes'} and spec.get(key) != current['spec'].get(key):
                raise ValueError('此编辑器仅修改需求，页面与交互结构请走原型变更流程')
        notelib.validate(spec.get('review_notes',{}),spec)
        old_interactions = current['spec'].get('interactions', [])
        interactions = spec.get('interactions', [])
        if not isinstance(interactions, list) or [i['id'] for i in interactions] != [i['id'] for i in old_interactions]:
            raise ValueError('属性编辑不新增/删除/重排交互')
        affected = set()
        for old_it, it in zip(old_interactions, interactions):
            if old_it == it:
                continue
            if any(old_it.get(k) != it.get(k) for k in old_it.keys() | it.keys() if k not in {'properties', 'target'}):
                raise ValueError('只允许编辑 properties 和 target，不能改写交互标识与关联')
            if old_it.get('target') != it.get('target') and it['action'] not in {'navigate', 'dialog', 'close', 'toggle'}:
                raise ValueError('此交互类型不支持目标编辑')
            element = current['prototype_elements'].get(it['page'], {}).get(it['selector'][1:], {})
            errors = property_errors(it, element)
            if errors:
                raise ValueError('\n'.join(errors))
            affected.update(it['requirement_ids'])
        old = {r['id']: r for r in current['spec']['requirements']}
        for r in spec['requirements']:
            previous = old.get(r['id'])
            if previous != r or r['id'] in affected:
                r['status'] = 'pending'
                oldrules = {x['id']: x for x in (previous or {}).get('rule_details', [])}
                for rule in r.get('rule_details', []):
                    if oldrules.get(rule['id']) != rule or r['id'] in affected:
                        rule['status'] = 'pending'
    return spec, documents


def prepare(root, vid, payload):
    for journal in (root / '.editing').glob('*.json'):
        if read(journal).get('status') == 'prepared':
            raise Conflict('存在中断的保存记录，请先检查 .editing 备份与项目状态')
    current = state(root, vid)
    if not current['editable']:
        raise Conflict('历史版本只读，请在规划版本编辑')
    if payload.get('revision') != current['revision']:
        raise Conflict('项目已被其他操作修改；请重新载入并合并草稿，未覆盖任何内容')
    spec, documents = candidate(current, payload)
    if spec and current['spec']:
        for old, new in zip(current['spec'].get('interactions', []), spec.get('interactions', [])):
            if old.get('properties') != new.get('properties'):
                resource = safe(root, f'versions/{vid}/content/prototype/assets/prototype-runtime.js')
                if not resource.exists() or 'PS_PROPERTY_RUNTIME_V1' not in resource.read_text(encoding='utf-8'):
                    raise ValueError('此版本原型运行时尚不支持属性编辑；先在规划版本升级共享 runtime 并验证')
    return current, spec, documents, impact(current['spec'], spec, current['documents'], documents)


def save(root, vid, payload, restore=False):
    folder = safe(root, '.editing')
    folder.mkdir(exist_ok=True)
    with (folder / 'write.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return _save(root, vid, payload, restore)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _save(root, vid, payload, restore=False):
    current, spec, documents, report = prepare(root, vid, payload)
    if restore:
        spec = payload['spec']
        report = impact(current['spec'], spec, current['documents'], documents)
    if not report['changes']:
        return {'state': current, 'impact': report, 'saved': False}
    errors, _ = validate(root)
    if errors:
        raise ValueError('请先修复项目检查错误：\n' + '\n'.join(errors))
    with tempfile.TemporaryDirectory(prefix='sky-prd-edit-') as tmp:
        stage = pathlib.Path(tmp) / 'project'
        stage.mkdir()
        for name in ('project.json', 'versions', 'site'):
            p = root / name
            if p.is_dir():
                shutil.copytree(p, stage / name)
            else:
                shutil.copy2(p, stage / name)
        if (root / 'outcomes').exists():
            shutil.copytree(root / 'outcomes', stage / 'outcomes')
        if (root / 'attachments').exists():
            shutil.copytree(root / 'attachments', stage / 'attachments')
        vr = stage / 'versions' / vid / 'content'
        if spec is not None:
            write(vr / 'spec.json', spec)
        for path, content in documents.items():
            safe(vr, path).write_text(content, encoding='utf-8')
        compile_project(stage)
        if revision(root) != current['revision']:
            raise Conflict('验证期间项目发生变化，请重新载入；未保存')
        # Only copy source and generated outputs that actually differ.
        staged = {**{'versions/' + k: v for k, v in hashes(stage / 'versions').items()},
                  **{'site/' + k: v for k, v in hashes(stage / 'site').items()}}
        targets = [key for key, digest in staged.items() if not safe(root, key).exists() or hashlib.sha256(safe(root, key).read_bytes()).hexdigest() != digest]
        backups = {key: safe(root, key).read_bytes().hex() if safe(root, key).exists() else None for key in targets}
        jid = uuid.uuid4().hex
        journal = safe(root, '.editing/' + jid + '.json')
        record = {'id': jid, 'version': vid, 'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'status': 'prepared', 'before_revision': current['revision'], 'backup_hex': backups,
                  'before_spec': current['spec'], 'before_documents': current['documents'], 'impact': report}
        write(journal, record)
        try:
            for key in targets:
                dest = safe(root, key)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=dest.parent, suffix='.editing-tmp', delete=False) as handle:
                    temp = pathlib.Path(handle.name)
                    handle.write(safe(stage, key).read_bytes())
                try:
                    temp.replace(dest)
                finally:
                    temp.unlink(missing_ok=True)
            record.update(status='saved', after_revision=revision(root))
            write(journal, record)
        except OSError:
            for key, content in backups.items():
                dest = safe(root, key)
                if content is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.write_bytes(bytes.fromhex(content))
            record['status'] = 'rolled-back'
            write(journal, record)
            raise
    return {'state': state(root, vid), 'impact': report, 'saved': True, 'undo_id': jid}


def undo(root, vid, payload):
    jid = payload.get('undo_id', '')
    if not isinstance(jid, str) or len(jid) != 32 or any(c not in '0123456789abcdef' for c in jid):
        raise ValueError('无效撤销记录')
    record = read(safe(root, '.editing/' + jid + '.json'))
    if record['version'] != vid or record['status'] != 'saved' or record['after_revision'] != revision(root) or payload.get('revision') != record['after_revision']:
        raise Conflict('保存后已有其他变更，不能直接撤销；请合并处理')
    return save(root, vid, {'revision': payload['revision'], 'spec': record['before_spec'], 'documents': record['before_documents']}, restore=True)
