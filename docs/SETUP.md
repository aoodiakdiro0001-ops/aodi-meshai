# Setup — Aodı-MeshAI

Full setup needs **no pip, no npm, no Docker**: Python 3.8+, Node 18+ (only for
the optional Telegram relay), Go 1.21+ (only for the optional gateway).

## 1. Prerequisites

```bash
python3 --version     # 3.8+
node --version        # 18+ (optional, telemetry relay only)
go version            # 1.21+ (optional, gateway only)
```

## 2. Local inference with Ollama (free)

```bash
# https://ollama.com/download
ollama pull qwen2.5-coder
ollama pull gemma4:12b        # optional, the "strong" node
ollama serve                  # usually already running on 127.0.0.1:11434
```

## 3. Run the core (required)

```bash
python3 core/server.py --port 9008
# check the fleet: curl http://127.0.0.1:9008/api/health
```

Default config lives in `core/config.py`; every default is overridable by
environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `AODIM_HOME` | `~/.aodim` | state dir (SQLite DB + nodes.json) |
| `AODIM_GEN_TIMEOUT` | `300` | per-generation timeout seconds (600 recommended on slow GPUs) |
| `AODIM_MAX_ATTEMPTS` | `3` | self-healing repair rounds before `failed` |
| `AODIM_SANDBOX_TIMEOUT` | `10` | sandbox execution timeout seconds |
| `AODIM_MEM_MB` | `512` | sandbox memory cap |
| `AODIM_TELEGRAM_RELAY` | — | URL of the Node relay (`http://127.0.0.1:7242/emit`) |
| `AODIM_TELEGRAM_TOKEN` / `AODIM_TELEGRAM_CHAT` | — | direct Telegram mode (no relay) |

## 4. Run the Go gateway (recommended)

```bash
cd gateway
go build -o ../bin/meshai-gateway .
./../bin/meshai-gateway        # listens on :9100, proxies to :9008
```

`MESH_CORE` and `MESH_ADDR` override the core URL and listen address.

## 5. Phone notifications (optional)

- **Direct mode** — no relay needed on the core host:
  `AODIM_TELEGRAM_TOKEN=<bot token> AODIM_TELEGRAM_CHAT=<chat id>`
- **Relay mode** — run `node telemetry/relay.js` (env `TELEGRAM_TOKEN`,
  `TELEGRAM_CHAT`, `PORT=7242`) and point the core at
  `AODIM_TELEGRAM_RELAY=http://127.0.0.1:7242/emit`.

Get a free bot token from @BotFather, then message the bot once and read your
chat id from `https://api.telegram.org/bot<token>/getUpdates`.

## 6. First task

```bash
curl -s -X POST http://127.0.0.1:9100/submit \
  -H "Content-Type: application/json" \
  -d '{"prompt":"write a python function divide(a,b) that returns a divided by b","test_harness":"assert divide(10,2)==5.0\nassert divide(10,0)==-1.0"}'

# follow the task
curl http://127.0.0.1:9008/api/task/<task_id>
# or open the dashboard
open http://127.0.0.1:9008/dashboard
```

## 7. Distribute across your machines (optional, still free)

Add nodes from any machine with Ollama (e.g. a Windows GPU box reachable over
Tailscale):

```bash
curl -s -X POST http://127.0.0.1:9008/api/nodes -H "Content-Type: application/json" \
  -d '{"name":"win-gpu","url":"http://100.x.y.z:11434","model":"qwen2.5-coder","tags":["small"]}'
```

Tags decide routing: `small` gets easy/medium tasks, `strong` gets hard tasks.

## 8. Tests

```bash
python3 tests/test_meshai.py -v     # router + sandbox, no network needed
node --check telemetry/relay.js
cd gateway && go vet ./... && go build ./...
```

## Support

baranavisat@gmail.com · WhatsApp +90 531 326 37 22 (wa.me/905313263722)
MIT © 2026 Baran Avisat
