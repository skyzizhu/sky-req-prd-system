#!/usr/bin/env python3
"""Append a reviewed observation. No deployment, PRD edits or automatic pass verdict."""
import argparse
import datetime
import fcntl
import json
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from outcomelib import check_payload, fingerprint, load_records
from projectlib import read, validate, ID


def append(root, payload):
    root = root.resolve()
    check_payload(payload)
    errors, _ = validate(root)
    if errors:
        raise ValueError('\n'.join(errors))
    project = read(root / 'project.json')
    versions = {v['id']: v for v in project['versions']}
    vid = payload['version']
    if vid not in versions or not ID.fullmatch(vid):
        raise ValueError('版本不存在')
    follow = payload.get('follow_up')
    if follow and (follow['target_version'] not in versions or versions[follow['target_version']]['status'] != 'planning' or follow['target_version'] == vid):
        raise ValueError('跟进目标必须为已存在的其他规划版本，不自动创建版本')
    content = root / 'versions' / vid / 'content'
    context = {}
    if payload['kind'] == 'execution':
        spec = read(content / 'spec.json')
        req = next((r for r in spec['requirements'] if r['id'] == payload['requirement_id']), None)
        acceptance = next((a for a in (req or {}).get('acceptance', []) if a['id'] == payload['acceptance_id']), None)
        if not acceptance:
            raise ValueError('验收 ID 不属于此版本的指定需求')
        context = {'requirement_title': req['title'], 'acceptance': acceptance}
    directory = root / 'outcomes'
    if not directory.resolve().is_relative_to(root):
        raise ValueError('outcomes 路径越界')
    directory.mkdir(exist_ok=True)
    with (directory / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = load_records(root)
        if payload.get('supersedes'):
            old = next((r for r in records if r['id'] == payload['supersedes']), None)
            identity = ('kind', 'version', 'requirement_id', 'acceptance_id', 'scope', 'goal', 'metric')
            if not old or any(old['payload'].get(k) != payload.get(k) for k in identity) or any(r['payload'].get('supersedes') == old['id'] for r in records):
                raise ValueError('更正必须指向同一对象且尚未被更正的记录')
        record = {'schema_version': 1, 'id': uuid.uuid4().hex, 'project': project['id'],
                  'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'baseline': fingerprint(content), 'context': context, 'payload': payload}
        target = directory / (record['id'] + '.json')
        temp = directory / (record['id'] + '.pending')
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        temp.replace(target)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=pathlib.Path)
    parser.add_argument('record', type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = append(args.root, read(args.record))
        print(json.dumps({'saved': result['id'], 'next': '运行 project.py build <项目> 更新站点；记录已保存，未执行部署或修改 PRD'}, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
