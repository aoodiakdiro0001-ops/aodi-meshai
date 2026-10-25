"""Aodı-MeshAI 1.0.0 — core config & state (stdlib-only)."""
import os
from pathlib import Path

VERSION = "1.0.0"
BRAND = "Aodı-MeshAI"

HOME = Path(os.environ.get("AODIM_HOME", str(Path.home() / ".aodim")))
HOME.mkdir(parents=True, exist_ok=True)
NODES_FILE = HOME / "nodes.json"
DB_FILE = HOME / "meshai.db"

# Task routing & self-healing limits
DEFAULT_PORT = int(os.environ.get("AODIM_PORT", "9008"))
GEN_TIMEOUT = int(os.environ.get("AODIM_GEN_TIMEOUT", "300"))
MAX_ATTEMPTS = int(os.environ.get("AODIM_MAX_ATTEMPTS", "3"))
SANDBOX_TIMEOUT = int(os.environ.get("AODIM_SANDBOX_TIMEOUT", "10"))
SANDBOX_MEM_MB = int(os.environ.get("AODIM_MEM_MB", "512"))

# Telemetry — optional Telegram relay (any Node/Python side)
TELEGRAM_BOT_TOKEN = os.environ.get("AODIM_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("AODIM_TELEGRAM_CHAT", "")
TELEGRAM_RELAY = os.environ.get("AODIM_TELEGRAM_RELAY", "")   # مثال: http://127.0.0.1:7242/emit

TIER_TAG = {"easy": "small", "medium": "small", "hard": "strong"}


def load_nodes():
    import json
    if NODES_FILE.exists():
        try:
            data = json.loads(NODES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    # عقد افتراضية منطقية على نفس المضيف (يمكن أن تتحول لجهازين عبر Tailscale)
    return [
        {"name": "mesh-small", "url": "http://127.0.0.1:11434",
         "model": "qwen2.5-coder", "tags": ["small"]},
        {"name": "mesh-strong", "url": "http://127.0.0.1:11434",
         "model": "gemma4:12b", "tags": ["strong"]},
    ]


def save_nodes(nodes):
    import json
    NODES_FILE.write_text(json.dumps(nodes, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")


def banner():
    return "\n".join([
        "===============================================",
        f"  {BRAND} v{VERSION} — self-healing mesh orchestrator",
        "  core router / sandbox loop / fleet telemetry",
        "===============================================",
    ])
