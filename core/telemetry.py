"""Aodı-MeshAI — telemetry funnel: Telegram مباشرة أو عبر relay Node (اختياري كلاهما)."""
import json, threading, urllib.request, urllib.error

import config
import storage


def emit(task_id, level, message):
    """غير حاجزة أبداً: فشل الشبكة لا يلحق ضربة بالمهمة."""
    record = {"task_id": task_id, "level": level, "message": message[:280]}
    storage.log_event(task_id, level, record["message"])
    threading.Thread(target=_fire, args=(record,), daemon=True).start()


def _fire(record):
    if config.TELEGRAM_RELAY:
        return _post_relay(record)
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        return _post_direct(record)


def _post_relay(record):
    try:
        data = json.dumps(record).encode("utf-8")
        req = urllib.request.Request(config.TELEGRAM_RELAY, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


def _post_direct(record):
    try:
        text = f"[{record['level'].upper()}] MeshAI#{record['task_id']}\n{record['message']}"
        url = (f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
               f"?chat_id={config.TELEGRAM_CHAT_ID}&text={urllib.request.quote(text)}")
        urllib.request.urlopen(url, timeout=5).read()
    except Exception:
        pass
