#!/usr/bin/env python3
"""Save exported prototype review notes through the shared staged editor."""
import argparse
import json
import pathlib
from editlib import state,save,Conflict
from projectlib import read
import notelib

def publish(root,vid,notes,revision):
    current=state(root,vid)
    if current['revision']!=revision: raise Conflict('项目已变化，请重新载入并检查批注差异')
    project=read(root/'project.json')
    if notes.get('project')!=project['id'] or notes.get('version')!=vid: raise ValueError('批注不属于当前项目/版本')
    existing=(current['spec'].get('review_notes') or {}).get(notes.get('page'))
    if notes.get('base_revision')!=notelib.digest(existing): raise Conflict('项目批注已在导出后变化；请比较并合并，不覆盖其他人的批注')
    notelib.validate({notes.get('page'):notes},current['spec'])
    clean=dict(notes);clean.pop('base_revision',None)
    current['spec'].setdefault('review_notes',{})[notes['page']]=clean
    return save(root,vid,current)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=pathlib.Path);p.add_argument('notes',type=pathlib.Path);p.add_argument('--version',required=True);p.add_argument('--revision',required=True);a=p.parse_args()
    result=publish(a.project.resolve(),a.version,read(a.notes),a.revision)
    print(json.dumps({k:result[k] for k in ('saved','undo_id','impact') if k in result},ensure_ascii=False,indent=2))
