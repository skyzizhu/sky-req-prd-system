#!/usr/bin/env python3
"""Print user-facing local delivery locations without changing project material."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, urlunsplit, quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'template'))
from projectlib import read, safe, check_build


def delivery_info(root, base_url, page_id=None):
    root=Path(root).resolve();project=read(root/'project.json');vid=project['current_version']
    entry=root/'site/index.html'
    if not entry.is_file():raise ValueError('缺少本地Web入口，请先构建项目')
    errors=check_build(root)
    if errors:raise ValueError('构建未更新：'+'；'.join(errors))
    url=urlsplit(base_url)
    if url.scheme not in ('http','https') or url.hostname not in ('localhost','127.0.0.1','::1') or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
        raise ValueError('url须为本机服务根地址，例如http://localhost:8795，不含路径或令牌')
    route='/v/'+quote(vid,safe='')+'/_prd/scope'
    if page_id:
        manifest=read(safe(root,'versions/'+vid+'/content/manifest.json'))
        matches=[(m,p) for m in manifest['modules'] for p in m['pages'] if p['id']==page_id]
        if len(matches)!=1:raise ValueError('页面编号不存在或不唯一')
        module,page=matches[0];route='/v/'+quote(vid,safe='')+'/'+quote(module['id'],safe='')+'/'+quote(page['id'],safe='')
    return {'localhost_url':urlunsplit((url.scheme,url.netloc,'/site/index.html','',route)),
            'local_web_entry':str(entry),'package_root':str(root),'version':vid,
            'package_note':'静态交付包包含完整site、versions及存在时的attachments、outcomes，保持相对目录；查看不需要.py。只发送入口HTML或site目录会缺物料。',
            'maintenance_note':'保留project.json、版本content源文件及构建工具，供后续局部修改。',
            'limits':'本命令只核对本地入口与构建状态，未探测服务HTTP状态，未打包或发送文件；交付前另确认入口返回200。'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--url',required=True);p.add_argument('--page')
    args=p.parse_args()
    try:print(json.dumps(delivery_info(args.project,args.url,args.page),ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as error:print(str(error),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
