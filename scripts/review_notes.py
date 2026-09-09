#!/usr/bin/env python3
"""Read-only reconciliation of exported annotations against PRD and edit journals."""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read, safe


def reconcile(root, notes):
    project=read(root/'project.json')
    vid=notes.get('version')
    if notes.get('schema_version') not in (1,2) or notes.get('project') != project['id'] or vid not in [v['id'] for v in project['versions']]:
        raise ValueError('批注项目或版本不匹配')
    spec=read(safe(root, 'versions/'+vid+'/content/spec.json'))
    page=next((p for p in spec['pages'] if p['id']==notes.get('page')),None)
    if not page: raise ValueError('批注页面不存在')
    results=[]
    if not isinstance(notes.get('reviews',[]),list): raise ValueError('reviews 必须为数组')
    note_ids={i['id'] for i in spec['interactions'] if i['page']==page['id']} | {i['id'] for i in notes.get('custom',[]) if isinstance(i,dict) and isinstance(i.get('id'),str)}
    for review in notes.get('reviews',[]):
        refs=review.get('requirement_ids',[])
        issues=[]
        if review.get('id') not in note_ids: issues.append('批注 ID 不存在于本页')
        if review.get('status') not in ('pending','accepted','rejected','completed'): issues.append('处理状态无效')
        if not isinstance(refs,list) or any(not isinstance(r,str) or r not in page['requirement_ids'] for r in refs): raise ValueError('需求关联格式无效')
        if not refs and review.get('status') in ('accepted','completed'): issues.append('缺少有效的本页需求关联')
        change=review.get('change_ref','')
        verified=False
        if change:
            if isinstance(change,str) and re.fullmatch('[a-f0-9]{32}',change):
                path=safe(root,'.editing/'+change+'.json')
                if path.is_file():
                    record=read(path)
                    verified=record.get('status')=='saved' and record.get('version')==vid and bool(refs) and set(refs).issubset(record.get('impact',{}).get('requirements',[]))
            if not verified: issues.append('无法核实修改记录与本页关联需求；外部记录需人工核对')
        elif review.get('status')=='completed': issues.append('完成记录缺少正式修改 ID')
        if review.get('status')=='completed' and not review.get('evidence','').strip(): issues.append('完成记录缺少验证说明')
        results.append({'note_id':review.get('id'), 'status':review.get('status'), 'change_record_verified':verified,'issues':issues})
    return {'project':project['id'],'version':vid,'page':page['id'],'reviews':results,
            'notice':'只核对本地需求和保存记录；验证说明仍是评审人填写，不证明实际产品已通过测试。不修改 PRD 或批注。'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=pathlib.Path);p.add_argument('notes',type=pathlib.Path);a=p.parse_args()
    try: print(json.dumps(reconcile(a.project.resolve(),read(a.notes)),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as e: p.exit(1,str(e)+'\n')
