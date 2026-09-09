#!/usr/bin/env python3
"""Serve a token-protected local PRD editor. Bind only to loopback."""
import argparse
import json
import pathlib
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

from editlib import Conflict, state, prepare, save, undo

ASSETS = pathlib.Path(__file__).resolve().parents[1] / 'assets/editor'


def server(root, vid, port=0):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body, kind='application/json; charset=utf-8'):
            content = json.dumps(body, ensure_ascii=False).encode() if not isinstance(body, bytes) else body
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(content)

        def authorized(self):
            host = '127.0.0.1:' + str(self.server.server_port)
            origin = self.headers.get('Origin')
            return (self.headers.get('Host') == host and (origin is None or origin == 'http://' + host)
                    and secrets.compare_digest(self.headers.get('X-Editor-Token', ''), token))

        def do_GET(self):
            route = urlsplit(self.path).path
            if route == '/api/state':
                if not self.authorized():
                    return self.reply(403, {'error': '编辑会话无效，请使用启动命令输出的链接'})
                try:
                    return self.reply(200, state(root, vid))
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    return self.reply(400, {'error': str(exc)})
            assets = {'/': ('index.html', 'text/html'), '/editor.js': ('editor.js', 'text/javascript'), '/editor.css': ('editor.css', 'text/css')}
            if route not in assets:
                return self.reply(404, {'error': '不存在'})
            name, mime = assets[route]
            self.reply(200, (ASSETS / name).read_bytes(), mime + '; charset=utf-8')

        def do_POST(self):
            if not self.authorized():
                return self.reply(403, {'error': '无效编辑会话或跨站请求'})
            try:
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('需要 JSON 请求')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4_000_000:
                    raise ValueError('请求大小无效（最多 4MB）')
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('请求必须为对象')
                route = urlsplit(self.path).path
                if route == '/api/preview':
                    result = {'impact': prepare(root, vid, payload)[3]}
                elif route == '/api/save':
                    result = save(root, vid, payload)
                elif route == '/api/undo':
                    result = undo(root, vid, payload)
                else:
                    return self.reply(404, {'error': '不存在'})
                self.reply(200, result)
            except Conflict as exc:
                self.reply(409, {'error': str(exc)})
            except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
                self.reply(400, {'error': str(exc)})

    service = HTTPServer(('127.0.0.1', port), Handler)
    service.timeout = 10
    return service, f'http://127.0.0.1:{service.server_port}/#token={token}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=pathlib.Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--action', choices=['serve', 'state', 'preview', 'save', 'undo'], default='serve')
    parser.add_argument('--payload', type=pathlib.Path, help='preview/save/undo 的 JSON 修改包')
    args = parser.parse_args()
    root = args.project.resolve()
    state(root, args.version)
    pending = [p.name for p in (root / '.editing').glob('*.json') if json.loads(p.read_text()).get('status') == 'prepared']
    if pending:
        parser.error('存在中断的保存记录，请先检查 .editing 备份与项目状态：' + ', '.join(pending))
    if args.action != 'serve':
        if args.action == 'state':
            result = state(root, args.version)
        else:
            if not args.payload:
                parser.error('此操作需要 --payload')
            payload = json.loads(args.payload.read_text(encoding='utf-8'))
            if args.action == 'preview':
                result = {'impact': prepare(root, args.version, payload)[3]}
            else:
                result = (save if args.action == 'save' else undo)(root, args.version, payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    service, url = server(root, args.version, args.port)
    print('本机 PRD 编辑器：' + url, flush=True)
    print('关闭此进程即结束编辑服务；仅当前电脑可访问。', flush=True)
    try:
        service.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.server_close()


if __name__ == '__main__':
    main()
