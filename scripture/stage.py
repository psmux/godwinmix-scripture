"""The stage display: a page for the band and the preacher.

It shows the slide on air in large letters, the next one under it, the
section or verse label and a clock. It is served by the plugin on its own
port, and only once someone presses Stage display in the panel (or calls the
`stage` tool): nothing listens until it is asked for.

The page waits on /state?since=<version>, which answers as soon as the slide
changes or after 25 seconds, so a screen on a music stand follows the operator
with no polling and no delay.
"""
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

WAIT_SECONDS = 25


def _slide(s):
    if not s:
        return None
    return {"text": s.get("text", ""), "ref": s.get("ref", ""), "label": s.get("label", "")}


def snapshot(svc):
    st = svc.state(full=False)
    return {
        "version": st["version"],
        "on_air": st["on_air"],
        "blank": st["blank"],
        "title": st["deck"]["title"] if st["deck"] else "",
        "index": st["index"],
        "count": st["deck"]["count"] if st["deck"] else 0,
        "current": _slide(st["current"]),
        "next": _slide(st["next"]),
    }


class StageServer:
    def __init__(self, svc):
        self.svc = svc
        self.httpd = None
        self.thread = None

    def start(self):
        svc = self.svc
        page_path = os.path.join(svc.root, "ui", "stage.html")

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, kind):
                data = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                url = urlparse(self.path)
                if url.path in ("/", "/stage", "/index.html"):
                    with open(page_path, encoding="utf-8") as f:
                        return self._send(200, f.read(), "text/html; charset=utf-8")
                if url.path == "/state":
                    since = int((parse_qs(url.query).get("since") or ["-1"])[0])
                    with svc.changed:
                        if svc.version == since:
                            svc.changed.wait(WAIT_SECONDS)
                    return self._send(200, json.dumps(snapshot(svc)), "application/json")
                return self._send(404, "not found", "text/plain")

        bind = self.svc.settings.get("stage_bind") or "0.0.0.0"
        port = int(self.svc.settings.get("stage_port") or 8091)
        try:
            self.httpd = ThreadingHTTPServer((bind, port), Handler)
        except OSError as e:
            from .service import ToolError
            raise ToolError("the stage display could not listen on %s:%d: %s. Set stage_port to a "
                            "free port in the plugin's settings and reload it." % (bind, port, e),
                            port=port)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="stage", daemon=True)
        self.thread.start()

    def urls(self):
        if not self.httpd:
            return []
        host, port = self.httpd.server_address[:2]
        names = ["127.0.0.1"] if host in ("0.0.0.0", "::") else [host]
        if host in ("0.0.0.0", "::"):
            try:
                names += sorted({a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None)
                                 if a[0] == socket.AF_INET and not a[4][0].startswith("127.")})
            except OSError:
                pass
        return ["http://%s:%d/" % (n, port) for n in names]

    def stop(self):
        if self.httpd:
            with self.svc.changed:
                self.svc.changed.notify_all()
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
