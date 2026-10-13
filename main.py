#!/usr/bin/env python3
"""Bible verses and song lyrics for GodwinMix: the service process.

JSON-RPC 2.0 with the core, one object per line: requests arrive on stdin,
everything this process says goes to stderr. stdout is never written to.
Standard library only.

`health` is answered on the reader thread from what is already known, so it
is never held up behind an import. Tool calls run in order on one worker
thread, except imports and network lookups, which get a thread each so the
operator's Next is never kept waiting behind a 10 MB OSIS file.
"""
import json
import os
import queue
import sys
import threading
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from scripture import mirror  # noqa: E402
from scripture.importers.common import ImportError_  # noqa: E402
from scripture.refparse import RefError  # noqa: E402
from scripture.service import Service, ToolError  # noqa: E402
from scripture.songs import SongError  # noqa: E402
from scripture.styles import StyleError  # noqa: E402
from scripture.tools import SLOW, TOOLS, summarise  # noqa: E402

API = 1
NAME = "scripture"
VERSION = "1.0.0"
# The core speaks UTF-8 both ways. Windows would otherwise read and write the
# pipes in the local code page, and one curly quote in a hymn would stop a reply.
for _stream in (sys.stdin, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
OUT = sys.stderr
WRITE = threading.Lock()


def send(obj):
    line = json.dumps(obj, separators=(",", ":"))
    with WRITE:
        OUT.write(line + "\n")
        OUT.flush()


def log(level, message):
    send({"jsonrpc": "2.0", "method": "log", "params": {"level": level, "message": message}})


def reply(rid, result):
    send({"jsonrpc": "2.0", "id": rid, "result": result})


def fail(rid, code, message, data=None):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message,
                                                   "data": dict(data or {}, retryable=False)}})


class Plugin:
    def __init__(self):
        self.svc = None
        self.work = queue.Queue()
        self.health = {"state": "ok", "detail": "starting"}

    def handshake(self, result):
        canvas = result.get("canvas") or {}
        params = result.get("params") or {}
        self.svc = Service(ROOT, canvas, params)
        self.health = {"state": "ok", "detail": "ready; data in %s" % self.svc.data_dir}
        log("info", "scripture %s ready at %dx%d, data in %s" % (
            VERSION, canvas.get("width", 0), canvas.get("height", 0), self.svc.data_dir))
        try:
            where = mirror.panel(ROOT, NAME)
            if where:
                log("info", "panel files copied to %s so the mixer's page finds them" % where)
        except OSError as e:
            log("warn", "could not copy the panel beside the plugin: %s" % e)

    def call_tool(self, rid, params):
        name = params.get("name", "")
        name = name.split("/")[-1]
        fn = TOOLS.get(name)
        if fn is None:
            return fail(rid, -32601, "scripture has no tool '%s'. It has: %s." % (
                name, ", ".join(sorted(TOOLS))), {"tool": name, "tools": sorted(TOOLS)})
        try:
            result = fn(self.svc, params.get("arguments") or {})
        except (ToolError, RefError, SongError, StyleError, ImportError_) as e:
            data = getattr(e, "data", {}) or {}
            return reply(rid, {"content": [{"type": "text", "text": str(e)}], "isError": True,
                               "structuredContent": {"error": str(e), "data": data}})
        except Exception as e:  # a bug: say so, keep running
            log("error", "tool %s failed: %s" % (name, traceback.format_exc()))
            return fail(rid, -32603, "scripture's %s tool failed: %s. This is a bug; the log has "
                        "the trace." % (name, e), {"tool": name})
        text = summarise(name, result)
        reply(rid, {"content": [{"type": "text", "text": text or json.dumps(result)[:2000]}],
                    "structuredContent": result})

    def handle(self, msg):
        method, rid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
        if method == "tool.call":
            return self.call_tool(rid, params)
        if method == "configure":
            return reply(rid, self.svc.configure(params.get("params") or {}))
        if method in ("start", "stop", "keyframe"):
            return reply(rid, {} if method != "start" else {"latency_ms": 0})
        if method == "shutdown":
            if self.svc and self.svc.stage:
                self.svc.stage.stop()
            reply(rid, {})
            os._exit(0)
        if rid is not None:
            fail(rid, -32601, "scripture does not implement '%s'. It is a service: it answers "
                 "health, configure, tool.call and shutdown." % method, {"method": method})

    def worker(self):
        while True:
            msg = self.work.get()
            if msg is None:
                return
            try:
                self.handle(msg)
            except Exception:
                log("error", traceback.format_exc())

    def run(self):
        send({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "plugin": NAME, "version": VERSION, "api": API, "transports": [],
            "provides": [{"kind": "service", "id": "service", "capabilities": ["health"],
                          "settings": "schemas/service.json"}]}})
        worker = threading.Thread(target=self.worker, name="worker", daemon=True)
        worker.start()
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                log("debug", "ignored a non JSON line on stdin")
                continue
            if "method" not in msg:
                if msg.get("id") == 0 and "result" in msg:
                    self.handshake(msg["result"])
                    send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
                elif msg.get("id") == 0:
                    log("error", "the core refused the handshake: %s" % msg.get("error"))
                    return
                continue
            if msg["method"] == "health":
                reply(msg.get("id"), self.health)
                continue
            if self.svc is None:
                fail(msg.get("id"), -32001, "scripture is still starting. Wait for initialized.",
                     {"state": "starting"})
                continue
            tool_name = (msg.get("params") or {}).get("name", "").split("/")[-1]
            if msg["method"] == "tool.call" and tool_name in SLOW:
                threading.Thread(target=self.handle, args=(msg,), daemon=True).start()
            else:
                self.work.put(msg)
        # stdin closed: the core has gone. Finish what was asked, then leave.
        self.work.put(None)
        worker.join(10)


if __name__ == "__main__":
    Plugin().run()
