#!/usr/bin/env python3
"""Locate an existing item from project/HTML; preview or save one stable-ID field."""
import argparse
import copy
import json
import pathlib
from urllib.parse import unquote, urlsplit
from editlib import state, prepare, save, Conflict
from projectlib import read, safe, pages, HTMLCheck


def locate(location, version=None):
    parsed = urlsplit(str(location))
    if parsed.scheme not in ('', 'file'):
        raise ValueError('在线 HTML 请先定位对应本地项目源目录，不从展示页重建项目')
    path = pathlib.Path(unquote(parsed.path)).resolve()
    root = next((p for p in [path, *path.parents] if (p / 'project.json').is_file()), None)
    if root is None:
        raise ValueError('找不到项目源数据；保留 HTML，先询问源目录，不自动重新生成')
    relative = path.relative_to(root).parts
    inferred = relative[1] if len(relative) > 1 and relative[0] == 'versions' else None
    route = parsed.fragment.split('?')[0].split('/')
    if len(route) > 2 and route[1] == 'v': inferred = unquote(route[2])
    if version and inferred and version != inferred:
        raise ValueError('指定版本与 HTML 所属版本冲突')
    vid = version or inferred
    if not vid:
        raise ValueError('固定入口未指定版本，请提供 --version 或带版本的页面链接')
    return root, vid


def page_context(root, vid, pid):
    content = safe(root, 'versions/' + vid + '/content')
    matches = [p for p in pages(read(content / 'manifest.json')) if p['id'] == pid and p['type'] == 'prototype']
    if len(matches) != 1:
        raise ValueError('页面编号不存在或不是原型页，不自动选择其他页面')
    page = matches[0]
    file = safe(content, page['file'])
    parser = HTMLCheck(); parser.feed(file.read_text(encoding='utf-8'))
    return {'page_id': pid, 'title': page['title'], 'html': str(file), 'resource_refs': parser.refs}


def lookup(current, query, page_id=None):
    spec = current['spec'] or {}
    result = []
    for kind in ('requirements', 'interactions', 'pages'):
        for item in spec.get(kind, []):
            mapping = next((p for p in spec.get('pages', []) if p['id'] == page_id), {})
            in_page = not page_id or (item['id'] == page_id if kind == 'pages' else item.get('page') == page_id if kind == 'interactions' else item['id'] in mapping.get('requirement_ids', []))
            if in_page and query.lower() in json.dumps(item,ensure_ascii=False).lower():
                result.append({'kind':kind,'item':item})
    return result


def patch(current, iid, field, value):
    payload = {'revision':current['revision'],'spec':copy.deepcopy(current['spec']),'documents':current['documents']}
    spec = payload['spec'] or {}
    matches = [(kind,item) for kind in ('requirements','interactions') for item in spec.get(kind,[]) if item['id']==iid]
    if len(matches) != 1: raise ValueError('必须提供唯一需求或控件 ID，不使用模糊匹配保存')
    kind,item = matches[0]; parts = field.split('/')
    if kind == 'interactions':
        if parts[0] not in ('properties','target') or len(parts)>2 or parts[0]=='target' and len(parts)!=1:
            raise ValueError('控件仅支持 properties/属性名 或 target；布局/行为由 Agent 局部修改源文件')
        if parts[0]=='properties' and 'properties' not in item: item['properties']={}
    elif parts[0] not in ('title','description','rules','rule_details','acceptance'):
        raise ValueError('不可通过单项编辑修改稳定 ID、来源或确认状态')
    node=item
    for part in parts[:-1]:
        if isinstance(node,list):
            found=[x for x in node if isinstance(x,dict) and x.get('id')==part]
            if len(found)!=1: raise ValueError('子规则/验收必须用稳定 ID 定位')
            node=found[0]
        elif isinstance(node,dict) and part in node: node=node[part]
        else: raise ValueError('字段路径不存在')
    if not isinstance(node,dict) or parts[-1] in ('id','source','status','requirement_ids','rule_ids','acceptance_ids'):
        raise ValueError('字段路径不支持；不修改关联和稳定 ID')
    if kind=='requirements' and (parts[-1] not in node or len(parts)==1 and parts[0] in ('rules','rule_details','acceptance')):
        raise ValueError('只修改已有叶字段，不能替换整个规则或验收集合')
    node[parts[-1]]=value
    return payload


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('location'); parser.add_argument('--version'); parser.add_argument('--query',default='')
    parser.add_argument('--page',help='精确原型页面编号，例如 order-list')
    parser.add_argument('--id'); parser.add_argument('--field'); parser.add_argument('--value',type=pathlib.Path,help='包含 JSON 值的文件')
    parser.add_argument('--revision'); parser.add_argument('--save',action='store_true')
    args=parser.parse_args()
    try:
        root,vid=locate(args.location,args.version); current=state(root,vid)
        context = page_context(root, vid, args.page) if args.page else None
        if not args.id:
            result={'root':str(root),'version':vid,'editable':current['editable'],'revision':current['revision'],'page':context,'matches':lookup(current,args.query,args.page)}
        else:
            if args.page and args.id not in [x['item']['id'] for x in lookup(current, '', args.page)]:
                raise ValueError('目标编号不属于指定页面，未修改')
            if not args.field or not args.value or args.revision!=current['revision']:
                raise Conflict('需提供 field/value 和刚刚定位得到的 revision；指纹变化时重新读取，不覆盖')
            payload=patch(current,args.id,args.field,read(args.value))
            result=save(root,vid,payload) if args.save else {'impact':prepare(root,vid,payload)[3],'saved':False}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error: parser.exit(1,str(error)+'\n')
