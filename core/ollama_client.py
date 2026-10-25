"""Aodı-MeshAI — multi-node Ollama client (stdlib: failover + tag filtering)."""
import json, time, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor

import config

_health = {}
_HLOCK = threading.Lock()


def _req(method, url, payload=None, timeout=60):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ping(url):
    t0 = time.time()
    entry = {"ok": False, "latency_ms": None, "models": [], "error": None}
    try:
        tags = _req("GET", url.rstrip("/") + "/api/tags", timeout=8)
        entry["ok"] = True
        entry["latency_ms"] = int((time.time() - t0) * 1000)
        entry["models"] = [m.get("name", "?").split(":")[0]
                           for m in tags.get("models", [])]
    except Exception as e:
        entry["error"] = f"{type(e).__name__}: {e}"[:120]
    with _HLOCK:
        _health[url] = entry
    return entry


def fleet_status(nodes=None):
    nodes = nodes or config.load_nodes()
    urls = list({n.get("url", "") for n in nodes if n.get("url")})
    if urls:
        with ThreadPoolExecutor(max_workers=min(8, len(urls))) as ex:
            list(ex.map(ping, urls))
    out = []
    for n in nodes:
        h = _health.get(n.get("url"), {})
        out.append({"name": n.get("name"), "url": n.get("url"),
                    "model": n.get("model"), "tags": n.get("tags", []),
                    "ok": h.get("ok", False), "latency_ms": h.get("latency_ms"),
                    "error": h.get("error")})
    return out


def generate_on(node, system, prompt, timeout=None, temperature=0.2,
                expect_code=False):
    """توليد عبر عقدة محددة صراحة — تُستخدم من الموجه."""
    url = node["url"].rstrip("/")
    model = node.get("model") or _default_model(url)
    if not model:
        return {"ok": False, "text": "", "node": node.get("name"),
                "model": None, "latency_ms": None,
                "error": "لا نموذج على العقدة"}
    payload = {"model": model, "prompt": prompt, "system": system,
               "stream": False, "options": {"temperature": temperature,
                                            "num_ctx": 8192}}
    t0 = time.time()
    try:
        out = _req("POST", url + "/api/generate", payload,
                   timeout=timeout or config.GEN_TIMEOUT)
        text = (out.get("response") or "").strip()
        if expect_code:
            text = _strip_fences(text)
        return {"ok": True, "text": text, "node": node.get("name"),
                "model": model, "latency_ms": int((time.time() - t0) * 1000),
                "error": None}
    except Exception as e:
        return {"ok": False, "text": "", "node": node.get("name"), "model": model,
                "latency_ms": int((time.time() - t0) * 1000),
                "error": f"{type(e).__name__}: {e}"[:160]}


def _default_model(url):
    h = _health.get(url)
    if h and h.get("models"):
        return h["models"][0]
    p = ping(url)
    return (p.get("models") or [None])[0]


def _strip_fences(s):
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


def with_failover(nodes, attempts=2, **kw):
    """تسلسل عقد مع فشل سلس: يريد nodes مرتبة أولوية."""
    last = None
    for node in nodes[:attempts]:
        r = generate_on(node, **kw)
        if r["ok"]:
            return r
        last = r
    return last or {"ok": False, "error": "لا عقد متاحة"}
