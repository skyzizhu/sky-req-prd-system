"""Authenticated editor upload backend. Append unique files; never overwrite history."""
import base64
import binascii
import datetime
import fcntl
import hashlib
import io
import json
import pathlib
import tempfile
import uuid
import zipfile

from editlib import Conflict, revision, state
from projectlib import read, write, safe, validate, compile_project
import attachmentlib


def verify_type(name, raw):
    if not isinstance(name, str) or not 1 <= len(name) <= 180 or any(c in name for c in '/\\\x00\r\n') or name in ('.','..'):
        raise ValueError('附件文件名无效')
    ext = pathlib.Path(name).suffix.lower()
    if ext not in attachmentlib.EXTENSIONS: raise ValueError('不支持此附件类型；禁止 HTML、脚本、SVG、压缩包和可执行文件')
    if not 0 < len(raw) <= attachmentlib.MAX_BYTES: raise ValueError('附件大小需为 1 字节～10MB')
    signatures = {'.pdf':b'%PDF-', '.png':b'\x89PNG\r\n\x1a\n', '.jpg':b'\xff\xd8\xff', '.jpeg':b'\xff\xd8\xff'}
    if ext in signatures and not raw.startswith(signatures[ext]): raise ValueError('附件内容与扩展名不匹配')
    if ext in ('.txt','.md','.csv'):
        text = raw.decode('utf-8-sig')
        if '\x00' in text: raise ValueError('文本附件含二进制内容')
    if ext in ('.docx','.xlsx','.pptx'):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                entries=z.infolist(); names={x.filename for x in entries}
                expected={'.docx':'word/document.xml','.xlsx':'xl/workbook.xml','.pptx':'ppt/presentation.xml'}[ext]
                if len(entries)>10000 or sum(x.file_size for x in entries)>100*1024*1024 or '[Content_Types].xml' not in names or expected not in names or any(x.flag_bits&1 or 'vbaproject' in x.filename.lower() for x in entries):
                    raise ValueError('Office 附件格式、宏、加密或解压规模不符合限制')
        except zipfile.BadZipFile: raise ValueError('Office 文件内容无效')
    return ext


def upload(root, vid, payload):
    if payload.get('share_ack') is not True: raise ValueError('请确认附件会随项目分享，且不含未授权敏感资料')
    description = payload.get('description')
    if not isinstance(description,str) or not description.strip() or len(description)>2000: raise ValueError('请填写 1～2000 字附件说明')
    encoded = payload.get('data')
    if not isinstance(encoded,str) or len(encoded)>14_000_000: raise ValueError('附件编码过大或无效')
    try: raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error): raise ValueError('附件编码无效')
    ext=verify_type(payload.get('name'),raw)
    folder=safe(root,'.editing'); folder.mkdir(exist_ok=True)
    lock_path=folder/'write.lock'
    if lock_path.is_symlink(): raise ValueError('编辑锁不能为符号链接')
    with lock_path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if payload.get('revision') != revision(root): raise Conflict('项目已有变更，请重新载入后上传，未写入附件')
        for journal in folder.glob('*.json'):
            if read(journal).get('status') == 'prepared': raise Conflict('存在中断保存记录，请先恢复')
        errors,_=validate(root)
        if errors: raise ValueError('\n'.join(errors))
        project=read(root/'project.json'); version=next((v for v in project['versions'] if v['id']==vid),None)
        if not version: raise ValueError('版本不存在')
        content=safe(root,'versions/'+vid+'/content')
        spec=read(content/'spec.json') if (content/'spec.json').exists() else {}
        ids=payload.get('requirement_ids',[])
        if not isinstance(ids,list) or any(not isinstance(i,str) or i not in {r['id'] for r in spec.get('requirements',[])} for i in ids): raise ValueError('附件关联需求不存在')
        aid=uuid.uuid4().hex
        meta={'id':aid,'name':payload['name'],'description':description,'requirement_ids':ids,
              'version':vid,'project':project['id'],'post_freeze':version['status']!='planning',
              'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'stored_name':'file'+ext,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        destination=safe(root,'attachments'); destination.mkdir(exist_ok=True)
        if (root/'attachments').is_symlink(): raise ValueError('附件目录不能是符号链接')
        with tempfile.TemporaryDirectory(prefix='attachment-',dir=folder) as temp:
            staging=pathlib.Path(temp)/aid; staging.mkdir()
            (staging/meta['stored_name']).write_bytes(raw); write(staging/'meta.json',meta)
            staging.rename(destination/aid)
        # An interruption before refs leaves an unreferenced immutable file, never a broken old link.
        if not meta['post_freeze']:
            linked=attachmentlib.refs(content); linked[aid]=meta['sha256']; write(content/'attachment-refs.json',linked)
        build_error=None
        try: compile_project(root)
        except (ValueError,OSError,KeyError,TypeError) as error: build_error=str(error)
        return {'saved':True,'attachment':meta,'build_error':build_error,'state':state(root,vid)}
