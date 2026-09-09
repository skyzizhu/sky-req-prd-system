#!/usr/bin/env python3
"""Manage a persistent project; run --help for commands. No network or git operations."""
import argparse
import datetime
import pathlib
import shutil
import sys
import uuid

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'template'))
from projectlib import read, write, safe, hashes, source_hashes, changes, compile_project, validate, check_build, ID


def install(root):
    shutil.copytree(SKILL / 'template/site', root / 'site', dirs_exist_ok=True)
    for name in ('build.py', 'projectlib.py', 'outcomelib.py'):
        shutil.copy2(SKILL / 'template' / name, root / name)


def manifest(name, form, version):
    return {'product': {'name': name, 'form': form, 'version': version, 'tagline': '',
                        'updated': datetime.date.today().isoformat()},
            'modules': [{'id': 'overview', 'title': '本版概览与变更', 'pages': [
                {'id': 'overview', 'title': '本版范围', 'type': 'markdown', 'file': 'overview/index.md',
                 'source': 'ai-inferred', 'status': 'pending'}]}]}


def checkpoint(vr):
    write(vr / '.baseline.json', source_hashes(vr))
    if (vr / 'content/spec.json').exists():
        write(vr / '.requirements-baseline.json', {r['id']: r for r in read(vr / 'content/spec.json')['requirements']})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['init', 'discover', 'new-version', 'build', 'check', 'freeze', 'status', 'impact', 'checkpoint', 'migrate', 'handoff'])
    p.add_argument('root', type=pathlib.Path)
    p.add_argument('--version', default=None)
    p.add_argument('--name')
    p.add_argument('--form', choices=['web', 'desktop', 'mobile', 'h5', 'miniapp', 'tv'])
    p.add_argument('--from-version')
    p.add_argument('--state', choices=['developing', 'released'])
    p.add_argument('--revision', help='交接修订编号，例如 r1')
    a = p.parse_args()
    root = a.root.resolve()
    if a.version and not ID.fullmatch(a.version):
        p.error('版本 ID 仅允许字母、数字、连字符及点')
    if a.command == 'discover':
        for f in sorted(root.rglob('project.json')):
            try:
                d = read(f)
                if d.get('schema_version') == 2:
                    print(d['id'], d['name'], d['current_version'], str(f.parent))
            except (ValueError, KeyError):
                continue
        return
    if a.command in {'init', 'migrate'}:
        if (root / 'project.json').exists():
            p.error('项目已存在，请使用 new-version 或修改当前版本')
        vid = a.version or 'v1.0'
        if a.command == 'init':
            if root.exists() and any(root.iterdir()):
                p.error('初始化目标必须为空目录')
            if not a.name or not a.form:
                p.error('初始化需要 --name 和 --form')
            m = manifest(a.name, a.form, vid)
            vr = root / 'versions' / vid
            write(vr / 'content/manifest.json', m)
            f = vr / 'content/overview/index.md'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('# 本版范围\n\n> ⚠️ **待确认**：请填写问题、目标、范围、排除项和变更。\n', encoding='utf-8')
        else:
            m = read(root / 'content/manifest.json')
            if (root / 'migration-backup').exists():
                p.error('migration-backup 已存在，请先检查上次迁移')
            backup = root / 'migration-backup'
            backup.mkdir()
            for name in ('content', 'site'):
                shutil.copytree(root / name, backup / name)
            if (root / 'build.py').exists():
                shutil.copy2(root / 'build.py', backup / 'build.py')
            vr = root / 'versions' / vid
            shutil.copytree(root / 'content', vr / 'content')
        write(root / 'project.json', {'schema_version': 2, 'id': str(uuid.uuid4()),
              'name': a.name or m['product']['name'], 'current_version': vid,
              'versions': [{'id': vid, 'title': a.name or m['product']['name'], 'status': 'planning', 'base': None}]})
        install(root)
        compile_project(root)
        checkpoint(vr)
        print('项目入口：', root / 'site/index.html')
        return
    project = read(root / 'project.json')
    vid = a.version or project['current_version']
    vr = safe(root, 'versions/' + vid)
    version = next((v for v in project['versions'] if v['id'] == vid), None)
    if a.command == 'new-version':
        if version or vr.exists() or not a.version:
            p.error('请提供未使用的 --version')
        base = a.from_version or project['current_version']
        if base not in [v['id'] for v in project['versions']]:
            p.error('来源版本不存在')
        errors, _ = validate(root)
        if errors:
            raise ValueError('\n'.join(errors))
        shutil.copytree(safe(root, 'versions/' + base) / 'content', vr / 'content')
        m = read(vr / 'content/manifest.json')
        m['product']['version'] = vid
        m['product']['updated'] = datetime.date.today().isoformat()
        write(vr / 'content/manifest.json', m)
        project['versions'].insert(0, {'id': vid, 'title': a.name or vid, 'status': 'planning', 'base': base})
        project['current_version'] = vid
        write(root / 'project.json', project)
        compile_project(root)
        checkpoint(vr)
    elif a.command == 'build':
        print('\n'.join(compile_project(root)))
    elif a.command == 'check':
        errors, warnings = validate(root)
        if not errors:
            errors.extend(check_build(root))
        print('\n'.join(['警告：' + w for w in warnings] + ['错误：' + e for e in errors]) or '验证通过')
        if errors:
            raise SystemExit(1)
    elif not version:
        p.error('版本不存在')
    elif a.command == 'handoff':
        if version['status'] != 'planning' or version.get('handoff_parent'):
            p.error('交接从规划工作版创建，历史快照不可修改')
        if not a.revision or not ID.fullmatch(a.revision):
            p.error('交接需要合法 --revision，例如 r1')
        sid = vid + '.' + a.revision
        target = safe(root, 'versions/' + sid)
        if target.exists() or any(v['id'] == sid for v in project['versions']):
            p.error('该交接编号已存在，不可覆盖')
        compile_project(root)
        from editlib import revision
        fingerprint = revision(root)
        specfile = vr / 'content/spec.json'
        if specfile.exists() and any(r.get('blocking') and (r.get('status') == 'pending' or any(x.get('status') == 'pending' for x in r.get('rule_details', []))) for r in read(specfile)['requirements']):
            p.error('阻塞需求或规则待确认，不能交接')
        # Stage the complete operation before touching live metadata or history.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='sky-handoff-') as tmp:
            stage = pathlib.Path(tmp) / 'project'
            stage.mkdir()
            shutil.copy2(root / 'project.json', stage / 'project.json')
            shutil.copytree(root / 'versions', stage / 'versions')
            shutil.copytree(root / 'site', stage / 'site')
            snapshot = stage / 'versions' / sid
            shutil.copytree(vr / 'content', snapshot / 'content')
            entry = {'id': sid, 'title': a.name or ('交接 ' + a.revision), 'status': 'planning',
                     'base': version.get('current_handoff') or version.get('base'), 'handoff_parent': vid,
                     'revision': a.revision, 'created': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            project['versions'].append(entry)
            version['current_handoff'] = sid
            write(stage / 'project.json', project)
            compile_project(stage)
            write(snapshot / '.snapshot.json', hashes(snapshot))
            entry['status'] = 'frozen'
            write(stage / 'project.json', project)
            compile_project(stage)
            if revision(root) != fingerprint:
                p.error('准备交接时项目发生修改，请重新检查后再交接')
            shutil.copytree(snapshot, target)
            write(root / 'project.json', project)
            compile_project(root)
        print('交接入口：', str(root / 'site/index.html') + '#/v/' + sid + '/_changes/report')
    elif a.command == 'freeze':
        if version['status'] != 'planning':
            p.error('该版本已冻结')
        compile_project(root)
        spec = vr / 'content/spec.json'
        if spec.exists() and any(r.get('blocking') and r['status'] == 'pending' for r in read(spec)['requirements']):
            p.error('存在阻塞开发的待确认需求')
        write(vr / '.snapshot.json', hashes(vr))
        version['status'] = 'frozen'
        write(root / 'project.json', project)
        compile_project(root)
    elif a.command == 'status':
        allowed = {'frozen': 'developing', 'developing': 'released'}
        if not a.state or allowed.get(version['status']) != a.state:
            p.error('仅允许 frozen → developing → released；规划版本先 freeze')
        errors, _ = validate(root)
        if errors:
            raise ValueError('\n'.join(errors))
        version['status'] = a.state
        write(root / 'project.json', project)
        compile_project(root)
    elif a.command == 'checkpoint':
        if version['status'] != 'planning':
            p.error('冻结版本不可更新基线')
        errors, _ = validate(root)
        if errors:
            raise ValueError('\n'.join(errors))
        checkpoint(vr)
    elif a.command == 'impact':
        import json
        from editlib import diff
        before = read(vr / '.baseline.json') if (vr / '.baseline.json').exists() else {}
        result = {'since_checkpoint': changes(before, source_hashes(vr))}
        if (vr / 'content/spec.json').exists():
            current = read(vr / 'content/spec.json')
            old = read(vr / '.requirements-baseline.json') if (vr / '.requirements-baseline.json').exists() else {}
            new = {r['id']: r for r in current['requirements']}
            altered = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
            result['changed_since_checkpoint'] = altered
            result['rule_changes_since_checkpoint'] = diff(old, new)
            result['review_acceptance_since_checkpoint'] = sorted({a['id'] for k in altered for r in (old.get(k, {}), new.get(k, {})) for a in r.get('acceptance', [])})
            result['review_pages_since_checkpoint'] = [p['id'] for p in current['pages'] if set(p['requirement_ids']) & set(altered)]
            result['review_interactions_since_checkpoint'] = [i['id'] for i in current['interactions'] if set(i['requirement_ids']) & set(altered)]
        base = version.get('base')
        if base:
            br = safe(root, 'versions/' + base)
            result['since_base_version'] = changes(source_hashes(br), source_hashes(vr))
            if (vr / 'content/spec.json').exists() and (br / 'content/spec.json').exists():
                old = {r['id']: r for r in read(br / 'content/spec.json')['requirements']}
                current = read(vr / 'content/spec.json')
                new = {r['id']: r for r in current['requirements']}
                altered = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
                result['changed_requirements'] = altered
                result['review_pages'] = [p['id'] for p in current['pages'] if set(p['requirement_ids']) & set(altered)]
                result['review_interactions'] = [i['id'] for i in current['interactions'] if set(i['requirement_ids']) & set(altered)]
                result['review_acceptance'] = [a['id'] for k in altered if k in new for a in new[k].get('acceptance', [])]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    print('完成：', a.command, vid)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
