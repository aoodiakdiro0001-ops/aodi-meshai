# Aodı-MeshAI

**Intelligent Multi-Node Autonomous AI Orchestrator & Self-Healing Pipeline**

A distributed AI mesh that routes tasks by complexity, executes them on the right node (small/fast vs strong/large model), runs generated code in an isolated sandbox, and **auto-repairs failed code up to 3 attempts until it passes 100% clean** — with live telemetry pushed to your phone.

| Layer | Language | Role |
|---|---|---|
| `core/` | Python 3.8+ (stdlib only) | heuristic router + self-heal orchestrator + SQLite audit |
| `gateway/` | Go 1.21+ (stdlib only) | high-concurrency `/submit` gateway with atomic counters + latency buckets |
| `telemetry/` | Node 18+ (zero npm deps) | Telegram Bot relay for live task events to your phone |
| `dashboard/` | HTML/JS (zero deps) | Arabic RTL dashboard showing the live self-heal cycle |

- **License:** MIT © 2026 Baran Avisat
- **Support:** baranavisat@gmail.com · WhatsApp +90 531 326 37 22 (wa.me/905313263722)
- **100% free stack:** Ollama (local) · SQLite · GitHub Actions · Telegram Bot API (optional) · Tailscale (optional) · Docker (optional)

## The idea in 30 seconds

You have a small fast model and a big strong model on your machines. A deterministic
rule-based router (no LLM call) classifies the task in microseconds, then dispatches it
to the right node. The agent's code goes into an **isolated sandbox** immediately
(`python -I` + rlimits + process-group kill on timeout). On failure, the exact error
message is fed back to the model for automatic repair — bounded loop, `MAX_ATTEMPTS=3`,
with every attempt written to a full SQLite audit trail (`attempts` table + unique
`trace_id`).

```
[ Gateway (Go :9100) ] → [ Core router + self-heal loop (Python :9008) ]
                                ↓ isolated execution
[ Ollama nodes: small / strong ]
      ↑ error fed back for auto-repair        ↓ result
[ telemetry (Node :7242) → Telegram → your phone ]  +  [ RTL live dashboard ]
```

## Running in 90 seconds (no pip, no npm)

```bash
# terminal 1 — core (Python stdlib only)
python3 core/server.py --port 9008

# terminal 2 — telemetry relay (optional)
node telemetry/relay.js

# terminal 3 — Go gateway
cd gateway && go build -o meshai-gateway . && ./meshai-gateway

# dashboard
open http://127.0.0.1:9008/dashboard
```

Submit a task through the gateway:

```bash
curl -s -X POST http://127.0.0.1:9100/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt":"write python divide(a,b) returning -1 on zero division","test_harness":"assert divide(10,2)==5.0\nassert divide(10,0)==-1.0"}'
```

On the dashboard you will see: easy/medium/hard tier → first attempt (often fails on the
zero-division edge) → sandbox reports the exact exception → model repairs itself →
**clean code delivered** → notification on your phone.

## Intelligent routing — no LLM classifier

- Rule-based scoring: prompt length + technical keyword weights + structural patterns
- Tier → node tag: `easy/medium` → `small`, `hard` → `strong`
- `hard` tasks get a short deterministic-style plan step before execution
- Nodes are plain entries: `{"name":"win-gpu","url":"http://…","model":"qwen2.5-coder","tags":["small"]}`
- With Tailscale every node becomes reachable by IP in one mesh — no port forwarding

## Sandbox guardrails (security before convenience)

| Guard | Value |
|---|---|
| Python isolation | `-I` flag (no user site, no env paths) |
| Memory cap | `RLIMIT_AS` 512MB default (`AODIM_MEM_MB`) |
| CPU cap | `RLIMIT_CPU` = sandbox timeout + 2s |
| Fork bomb | `RLIMIT_NPROC=24` |
| Core dumps | `RLIMIT_CORE=0` |
| Timeout hang | `killpg(SIGKILL)` on the whole process group |
| Repair loop | `MAX_ATTEMPTS=3` → then task marked `failed` (no infinite loops), full trace in `attempts` |

## Live numbers (measured, see BENCHMARKS.md)

Recorded live in `BENCHMARKS.md` on real hardware: router **22–25 µs** per
classification (≈44k/sec, zero LLM calls), gateway overhead **2–7 ms**, sandbox
**22–45 ms** median ≈35 ms, `hard` task auto-repaired on a strong node after one
round, cross-node LAN generation probe **9.5 s** on the second laptop — fleet
health **3/3**.

## Honest disclosure

- The sandbox enforces resource/timeout isolation, not a network-secure container.
  For hard production isolation run the core inside `docker run --network none`.
- The rule-based router is fast and cheap but not perfect; add your own keyword sets in
  `core/router.py` (plain lists, no config files needed).
- Telegram queue is fire-and-forget: without a token the events still live locally in
  SQLite and the dashboard.

© 2026 Baran Avisat · MIT License · BTC `bc1q8dhtdrndxsl70e97t8grydfe6pjue37zrhzf6c` · USDT-TRC20 `TLWdTjqqogkXNEXGiPWsGdjFP6ioycxeWW`
