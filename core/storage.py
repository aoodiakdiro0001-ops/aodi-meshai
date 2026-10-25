"""Aodı-MeshAI — SQLite storage (stdlib sqlite3) لسجل المهام والأحداث."""
import json, sqlite3, threading, time

import config

_LOCK = threading.Lock()
_CONN = None


def _db():
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(str(config.DB_FILE), check_same_thread=False)
        _CONN.execute("""CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY, prompt TEXT NOT NULL, tier TEXT,
            status TEXT DEFAULT 'queued', attempts INTEGER DEFAULT 0,
            model TEXT, node TEXT, ok INTEGER, exit_code INTEGER,
            error TEXT, code_path TEXT, created REAL, finished REAL)""")
        _CONN.execute("""CREATE TABLE IF NOT EXISTS attempts(
            trace_id TEXT PRIMARY KEY, task_id TEXT, idx INTEGER,
            ok INTEGER, exit_code INTEGER, ms INTEGER, error TEXT,
            taken TEXT, ts REAL)""")
        _CONN.execute("""CREATE TABLE IF NOT EXISTS events(
            ts REAL, task_id TEXT, level TEXT, message TEXT)""")
        _CONN.commit()
    return _CONN


def log_attempt(trace_id, task_id, idx, ok, exit_code, ms, error, taken):
    with _LOCK:
        _db().execute(
            "INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?,?,?,?)",
            (trace_id, task_id, idx, ok, exit_code, ms,
             (error or "")[:300], (taken or "")[:200], time.time()))
        _db().commit()


def new_task(tid, prompt, tier):
    with _LOCK:
        _db().execute("INSERT INTO tasks(id,prompt,tier,created) VALUES(?,?,?,?)",
                      (tid, prompt, tier, time.time()))
        _db().commit()


def update_task(tid, **kw):
    cols = ", ".join(f"{k}=?" for k in kw)
    with _LOCK:
        _db().execute(f"UPDATE tasks SET {cols} WHERE id=?",
                      (*kw.values(), tid))
        _db().commit()


def get_task(tid):
    with _LOCK:
        cur = _db().execute("SELECT * FROM tasks WHERE id=?", (tid,))
        row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description] if hasattr(cur, "description") else []
    return dict(zip(cols, row)) if row else None


def list_tasks(limit=30):
    with _LOCK:
        cur = _db().execute(
            "SELECT id,tier,status,attempts,model,node,ok,created FROM tasks "
            "ORDER BY created DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def log_event(task_id, level, message):
    with _LOCK:
        _db().execute("INSERT INTO events(ts,task_id,level,message) VALUES(?,?,?,?)",
                      (time.time(), task_id or "", level, message[:400]))
        _db().commit()


def event_tail(limit=40):
    with _LOCK:
        cur = _db().execute(
            "SELECT ts,task_id,level,message FROM events ORDER BY ts DESC LIMIT ?",
            (limit,))
        return [dict(r) for r in cur.fetchall()]
