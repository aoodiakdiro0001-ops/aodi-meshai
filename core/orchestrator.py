"""Aodı-MeshAI — orchestrator: routing → decomposition → self-healing loop → telemetry."""
import os, sys, threading, time, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import router
import sandbox
import storage
import telemetry
import ollama_client

TASKS = {}            # id -> record
_TLOCK = threading.Lock()

SYSTEM_CODER = """أنت وكيل توليد كود في منظومة Aodı-MeshAI.
الشرط الصارم: أخرج شفرة بايثون فقط صالحة للتشغيل الفوري، بلا شرح، وبلا زخارف.
الشفرة ستنفذ في صندوق معزول بحدود زمن وذاكرة صارمة. تجنب: قراءة ملفات خارجية،
اتصالات شبكة، خيوط لا نهائية، حلقات بلا شرط انتهاء."""

SYSTEM_PLANNER = """أنت مخطط مهام. اختصر المطلوب إلى خطوات مرقمة تنفيذية (5 على الأكثر)
بلغة عربية واضحة. بلا شفرة في هذه المرحلة."""

SYSTEM_REPAIR = """أنت وكيل إصلاح ذاتي. تستلم شفرة بايثون فاشلة ورسالة خطأ من الصندوق المعزول.
أخرج الشفرة الكاملة المصححة فقط — بلا شرح، بلا زخارف، وبلا مراجعات جانبية."""


def new_task(prompt, test_harness=None, kind="code"):
    info = router.classify(prompt)
    tier = info["tier"]
    tid = uuid.uuid4().hex[:10]
    rec = {"id": tid, "prompt": prompt, "tier": tier, "score": info["score"],
           "status": "queued", "attempts": 0, "created": time.strftime("%H:%M:%S"),
           "ok": None, "error": None, "code": None, "model": None, "node": None,
           "attempts_log": [], "duration_ms": 0,
           "test_harness": (test_harness or "") if kind == "code" else ""}
    with _TLOCK:
        TASKS[tid] = rec
    storage.new_task(tid, prompt, tier)
    telemetry.emit(tid, "info", f"مهمة جديدة بدرجة صعوبة {tier} (score {info['score']})")
    threading.Thread(target=_run, args=(tid,), daemon=True).start()
    return rec


def get_task(tid):
    with _TLOCK:
        return TASKS.get(tid)


def all_tasks(limit=30):
    with _TLOCK:
        return list(TASKS.values())[::-1][:limit]


def _run(tid):
    rec = get_task(tid)
    if not rec:
        return
    try:
        rec["status"] = "running"
        storage.update_task(tid, status="running")
        t0 = time.time()
        nodes = config.load_nodes()
        info = router.route_info(rec["prompt"], nodes)
        chosen = [n for n in nodes if n.get("name") in (info.get("chosen") or [])]
        if not chosen:
            chosen = router.pick_nodes(nodes, info["tier"])
        telemetry.emit(tid, "info",
                       f"الموجه اختار: {', '.join(n.get('name') or '' for n in chosen)}")
        prompt = rec["prompt"]
        harness = rec.get("test_harness") or ""
        if harness:
            # الصندوق سيحكم على الكود بهذا الـ harness حرفياً — دع النموذج يراه
            # منذ البداية (درس من جولة حية: غياب التوقعات يصنع فشلاً معاداً).
            prompt += ("\n\nأداة التحقق التي يجب أن تمر تماماً عند تشغيل الكود "
                       "(أدرجها كما هي في نهاية الكود):\n" + harness)
        if info["tier"] == "hard":
            prompt = _decompose(chosen, prompt)
        for attempt in range(1, config.MAX_ATTEMPTS + 1):
            rec["attempts"] = attempt
            r = ollama_client.with_failover(
                chosen, attempts=2, system=SYSTEM_CODER, prompt=prompt,
                expect_code=True, temperature=0.15)
            if not r or not r.get("ok"):
                err = (r or {}).get("error") or "لا عقد صالحة"
                rec.update(status="failed", error=f"توليد فاشل: {err}")
                storage.update_task(tid, status="failed", error=err[:200],
                                    attempts=attempt, finished=time.time())
                telemetry.emit(tid, "error", f"توليد فشل: {err[:140]}")
                return
            rec["model"], rec["node"] = r.get("model"), r.get("node")
            storage.update_task(tid, model=r.get("model"), node=r.get("node"))
            sbx = sandbox.run_code(r["text"], harness)
            trace_id = uuid.uuid4().hex[:12]
            storage.log_attempt(trace_id, tid, attempt, sbx["ok"],
                                sbx["exit_code"], sbx["duration_ms"],
                                sbx["error"], ("repair-loop" if attempt > 1
                                               else "first-shot"))
            rec["attempts_log"].append(
                {"attempt": attempt, "ok": sbx["ok"], "exit": sbx["exit_code"],
                 "ms": sbx["duration_ms"], "err": (sbx["error"] or "")[:200]})
            if sbx["ok"]:
                # النظافة الختامية: إن أعاد النموذج نسخة من سطور الأداة
                # في نهاية الكود نحذفها حتى يُسلَّم كود نظيف فقط.
                hlines = {ln.strip() for ln in harness.splitlines() if ln.strip()}
                lines = r["text"].rstrip().splitlines()
                while lines and lines[-1].strip() in hlines:
                    lines.pop()
                rec["code"] = "\n".join(lines).rstrip() + "\n"
                rec["ok"] = True
                rec["status"] = "done"
                rec["duration_ms"] = int((time.time() - t0) * 1000)
                storage.update_task(tid, ok=1, status="done", exit_code=0,
                                    attempts=attempt, finished=time.time())
                telemetry.emit(
                    tid, "ok",
                    f"كود نظيف 100% بعد {attempt} محاولة/محاولات · "
                    f"نموذج {r.get('model')} · صندوق {sbx['duration_ms']}ms")
                return
            storage.update_task(tid, attempts=attempt, error=(sbx["error"] or "")[:200])
            telemetry.emit(tid, "warn",
                           f"محاولة {attempt} فشلت (exit {sbx['exit_code']}) — "
                           f"يعاد إصلاحها ذاتياً: {str(sbx['error'])[:150]}")
            prompt = _repair_prompt(r["text"], sbx["error"] or "", harness)
        rec.update(ok=False, status="failed",
                   error=f"لم ينجح الإصلاح الذاتي بعد {config.MAX_ATTEMPTS} من المحاولات",
                   duration_ms=int((time.time() - t0) * 1000))
        storage.update_task(tid, ok=0, status="failed", finished=time.time())
        telemetry.emit(tid, "error", "اكتملت المحاولات دون شفرة نظيفة — رُجعت للمطور")
    except Exception as e:
        rec.update(status="failed", error=f"{type(e).__name__}: {e}")
        storage.update_task(tid, status="failed", error=str(e)[:200])
        telemetry.emit(tid, "error", f"استثناء غير متوقع: {e}"[:200])


def _decompose(chosen, prompt):
    r = ollama_client.with_failover(chosen, attempts=1, system=SYSTEM_PLANNER,
                                    prompt="برسم خطة تنفيذ: " + prompt,
                                    expect_code=False, temperature=0.2)
    if r.get("ok") and 40 < len(r.get("text") or "") < 2400:
        return prompt + "\n\nخطة التنفيذ المعتمدة:\n" + r["text"][:1200]
    return prompt


def _repair_prompt(code, error, harness=""):
    msg = (error or "").strip()
    if len(msg) > 1500:
        msg = msg[-1500:]
    out = ("شفرة تحتاج إصلاحاً:\n```python\n" + code + "```\n\n"
           "رسالة الصندوق المعزول:\n" + msg + "\n")
    if harness:
        out += ("\nأداة التحقق التي يجب أن تمر تماماً بعد الإصلاح "
                "(أدرجها كما هي في نهاية الكود):\n" + harness + "\n")
    out += "\nأخرج نسخة مصححة كاملة تعمل بلا أخطاء."
    return out
