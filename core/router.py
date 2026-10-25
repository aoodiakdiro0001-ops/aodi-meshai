"""Aodı-MeshAI — heuristic task router (بلا نموذج: قواعد وراثية سريعة)."""
import re

HARD_PATTERNS = [
    r"\b(async|thread|threading|concurrent|parallel|websocket|redis|nats)\b",
    r"\b(optimi[sz]e|algorithm|complexity|benchmark|crypto|encode|parser|interpreter)\b",
    r"\b(database|sql|migration|index|cache|distributed|network|protocol)\b",
    r"\b(class\s+\w+.*inherit|metaclass|decorator|generator|decor)\b",
    r"\b(security|encrypt|hash|auth|token|session|audit)\b",
    r"\b(multi|agonist|pipeline|framework|architecture)\b",
    r"\b(\d{3,})\s*(lines|سطر)\b",
    r"^[^?]{280,}",                 # وصف طويل جداً = مشروع
]
MED_PATTERNS = [
    r"\bapi\b", r"\bjson\b", r"\bfile\b", r"\b(loop|recurse|sorting)\b",
    r"\b(dict|list|tuple|matrix|regex)\b", r"\b(test|validate|parse)\b",
]


def classify(prompt):
    """يعيد tier: easy|medium|hard + score (قارن حصص) — بلا استدعاء نموذج."""
    p = (prompt or "").strip()
    text = p.lower()
    hard = sum(1 for rx in HARD_PATTERNS if re.search(rx, text, re.I))
    med = sum(1 for rx in MED_PATTERNS if re.search(rx, text, re.I))
    score = hard * 3 + med + min(len(p) // 220, 5)
    if score >= 5 or (hard >= 2 and med >= 1):
        tier = "hard"
    elif score >= 2:
        tier = "medium"
    else:
        tier = "easy"
    return {"tier": tier, "score": score, "hard_hits": hard, "med_hits": med}


def pick_nodes(nodes, tier):
    """يفلتر العقد حسب العلامة المطلوبة (small: easy/medium — strong: hard)."""
    import config
    tag = config.TIER_TAG.get(tier, "small")
    exact = [n for n in nodes if tag in (n.get("tags") or [])]
    if exact:
        return exact
    if tier == "hard" and nodes:
        return nodes  # لا عقدة strong — تسلسل فشل سلس إلى أي عقدة متاحة
    return [n for n in nodes if "small" in (n.get("tags") or [])] or nodes


def route_info(prompt, nodes):
    c = classify(prompt)
    chosen = pick_nodes(nodes or [], c["tier"])
    return {"tier": c["tier"], "score": c["score"],
            "chosen": [n.get("name") for n in chosen[:2]],
            "tags_hint": c}
