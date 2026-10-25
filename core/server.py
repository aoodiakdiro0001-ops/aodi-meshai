#!/usr/bin/env python3
"""Aodı-MeshAI — core API server (stdlib-first).
نقاط الواجهة:
  GET  /api/health      صحة كل عقد الشبكة (متوازٍ)
  GET  /api/fleet       حالة العقد + الصلاحيات
  POST /api/task        إرسال مهمة {prompt, test_harness?, tier_hint?}
  GET  /api/task/<id>   حالة/نتيجة مهمة
  GET  /api/tasks       آخر المهام
  GET  /api/events      ذيل أحداث (للتقنيات)
  POST /api/nodes       {name,url,model,tags}
  GET  /dashboard       اللوحة
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CORE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CORE)
import config
import ollama_client
import orchestrator
import storage

STATIC = os.path.join(os.path.dirname(CORE), "dashboard")


class Handler(BaseHTTPRequestHandler):
    # HTTP headers must remain ASCII-safe (RFC 7230): keep the Turkish brand "ı"
    # out of the Server: header, it is fine inside JSON bodies (UTF-8).
    server_version = "AodiMeshAI/" + config.VERSION

    def _json(self, code, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        p = self.path.split("?", 1)[0]
        if p == "/api/health":
            return self._json(200, {"brand": config.BRAND, "version": config.VERSION,
                                    "fleet": ollama_client.fleet_status()})
        if p == "/api/fleet":
            return self._json(200, {"nodes": ollama_client.fleet_status()})
        if p.startswith("/api/task/"):
            tid = p.rsplit("/", 1)[1]
            rec = orchestrator.get_task(tid)
            return self._json(200 if rec else 404, rec or {"error": "غير موجود"})
        if p == "/api/tasks":
            return self._json(200, {"tasks": orchestrator.all_tasks()})
        if p == "/api/events":
            return self._json(200, {"events": storage.event_tail()})
        if p in ("/", "/dashboard"):
            return self._serve_dashboard()
        return self._json(404, {"error": "لا مسار"})

    def do_POST(self):
        p = self.path.split("?", 1)[0]
        body = self._body()
        if p == "/api/task":
            prompt = (body.get("prompt") or "").strip()
            if not prompt:
                return self._json(400, {"error": "المهمة الشاحبة prompt مطلوبة"})
            rec = orchestrator.new_task(prompt, body.get("test_harness"))
            return self._json(202, rec)
        if p == "/api/nodes":
            name, url = (body.get("name") or "").strip(), (body.get("url") or "").strip()
            if not name or not url:
                return self._json(400, {"error": "name و url مطلوبان"})
            nodes = [n for n in config.load_nodes() if n.get("name") != name]
            nodes.append({"name": name, "url": url,
                          "model": body.get("model"), "tags": body.get("tags", [])})
            config.save_nodes(nodes)
            return self._json(200, {"ok": True,
                                    "status": ollama_client.fleet_status(nodes)})
        return self._json(404, {"error": "لا مسار"})

    def _serve_dashboard(self):
        idx = os.path.join(STATIC, "index.html")
        if os.path.exists(idx):
            with open(idx, "rb") as f:
                raw = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            self._json(404, {"error": "missing dashboard"})


def main():
    import argparse
    ap = argparse.ArgumentParser(prog="meshai-core")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    a = ap.parse_args()
    httpd = ThreadingHTTPServer((a.host, a.port), Handler)
    print(config.banner(), flush=True)
    print(f"[core] listening http://{a.host}:{a.port}  (AODIM_HOME={config.HOME})",
          flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
