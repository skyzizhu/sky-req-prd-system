#!/usr/bin/env python3
"""serve.py —— 启动局域网共享服务，打印本机与局域网访问地址

用法：
    python3 serve.py [端口=8000] [方案目录=当前目录]

行为：
    - 绑定 0.0.0.0，同一路由器/局域网下的同事可通过本机 IP 访问
    - 端口被占用时自动向后尝试（最多 +20）
    - 自动探测本机局域网 IP（UDP connect 技巧，不实际发包，跨平台）
"""

import http.server
import pathlib
import socket
import socketserver
import sys


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def pick_port(want):
    for port in range(want, want + 21):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"端口 {want}~{want + 20} 均被占用，请指定其他端口")


def main():
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    root = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
    port = pick_port(want)
    ip = lan_ip()

    print(f"方案目录：{root}")
    print(f"本机访问：http://localhost:{port}/site/index.html")
    print(f"局域网共享（同一路由器下同事可访问）：http://{ip}:{port}/site/index.html")
    print("Ctrl+C 停止服务", flush=True)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务已停止", flush=True)


if __name__ == "__main__":
    main()
