#!/usr/bin/env python3
"""Lightweight lookup and exact text patches. No model call, no new project/version."""
import argparse
import json
import pathlib
from revise_item import locate
from editlib import state, prepare, save, Conflict
from projectlib import read
import materiallib

def catalog(root, vid):
    current=state(root,vid)
    manifest=read(root/'versions'/vid/'content/manifest.json')
    return current,materiallib.index(manifest,current['spec'],current['documents'])

def patch_document(root,vid,source,anchor,before,after,revision,commit=False):
    current=state(root,vid)
    if revision!=current['revision']: raise Conflict('项目发生变化，请重新查询')
    if source not in current['documents']: raise ValueError('目标不是已登记的可编辑正文')
    current['documents'][source]=materiallib.replace(current['documents'][source],anchor,before,after)
    if commit:
        result=save(root,vid,current)
        return {k:result[k] for k in ('saved','impact','undo_id') if k in result}
    return {'impact':prepare(root,vid,current)[3]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('location');p.add_argument('--version');p.add_argument('--query',default='');p.add_argument('--key');p.add_argument('--patch',type=pathlib.Path);p.add_argument('--revision');p.add_argument('--save',action='store_true')
    a=p.parse_args();root,vid=locate(a.location,a.version)
    current,items=catalog(root,vid)
    if a.patch:
        change=read(a.patch)
        result=patch_document(root,vid,change['source'],change.get('anchor'),change['before'],change['after'],a.revision,a.save)
    else:
        matches=[i for i in items if (i['key']==a.key if a.key else a.query.lower() in json.dumps(i,ensure_ascii=False).lower())]
        result={'project_root':str(root),'version':vid,'editable':current['editable'],'revision':current['revision'],'total':len(matches),'items':matches[:50]}
        if a.key and len(matches)==1 and matches[0]['source'] in current['documents']:
            item=matches[0];body=current['documents'][item['source']]
            if item.get('anchor'):
                b=next(b for b in materiallib.blocks(body) if b['id']==item['anchor']);body=body[b['start']:b['end']]
            elif item['kind']=='table-row':
                import re
                body=next(line for line in body.splitlines() if re.match(r'^\s*\|\s*'+re.escape(item['id'])+r'\s*\|',line))
            result['text']=body
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError) as error: raise SystemExit(str(error))
