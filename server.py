"""本地 API + 静态服务：给 Lively 壁纸提供数据与交互回传。

零三方依赖（只用标准库 http.server）。
- GET  /                -> 壁纸静态文件（wallpaper/ 目录，默认 index.html）
- GET  /api/reminders   -> 未完成提醒的 JSON 列表
- POST /api/done?id=N   -> 把第 N 条标记为完成
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

import store

WALLPAPER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallpaper")
_CTYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
           ".css": "text/css; charset=utf-8"}


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")          # 允许壁纸跨源访问
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/reminders":
            self._json(store.upcoming(20))
            return
        rel = unquote(path).lstrip("/") or "index.html"
        fp = os.path.normpath(os.path.join(WALLPAPER_DIR, rel))
        # 用 commonpath 而不是 startswith：后者会放行 wallpaper_xxx 这类同前缀目录
        try:
            inside = os.path.commonpath([WALLPAPER_DIR, fp]) == WALLPAPER_DIR
        except ValueError:  # 不同盘符等
            inside = False
        if not inside or not os.path.isfile(fp):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        ext = os.path.splitext(fp)[1].lower()
        with open(fp, "rb") as f:
            self._send(200, f.read(), _CTYPES.get(ext, "application/octet-stream"))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/done":
            rid = parse_qs(u.query).get("id", [None])[0]
            if rid is None:                                            # 也支持 JSON body
                length = int(self.headers.get("Content-Length", 0) or 0)
                if length:
                    try:
                        rid = json.loads(self.rfile.read(length)).get("id")
                    except Exception:
                        rid = None
            try:
                store.mark_done(int(rid))
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 400)
            return
        self._json({"ok": False, "error": "bad request"}, 400)

    def log_message(self, *args):   # 静默，不刷屏
        pass


def start_in_thread(port=8765):
    """后台线程启动 HTTP 服务，返回 server 对象。"""
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
