# ARCHITECTURE — Aodı-MeshAI v1.0.0

## Key design decisions

1. **Deterministic routing (no LLM classifier):** weighted keyword rules + length +
   structural patterns return a tier in microseconds. LLMs are called for execution,
   never for classification. This removes cost headroom and avoids model-dependent
   triage flakiness in the hot path.

2. **Sandbox without Docker in the default path:** subprocess execution with `-I`
   (isolated mode), `RLIMIT_AS/CPU/NPROC/CORE`, `start_new_session=True` and a
   `killpg(SIGKILL)` fallback on timeout. A containerized mode (`--network none`) is
   documented as the hard-isolation upgrade for production.

3. **Bounded self-healing:** `MAX_ATTEMPTS=3` (env override). After the final failure
   the task is `status=failed` — no unbounded loops are possible. Every attempt is
   recorded with a unique `trace_id`, attempt index, exit code and duration in the
   `attempts` table for deterministic audit.

4. **Telemetry can never block a task:** all notification paths run in daemon threads;
   Telegram or relay failures are swallowed and logged only.

5. **Go gateway is a pure edge:** reverse proxy to core with atomic counters and latency
   buckets. All business logic (routing, healing, storage, prompting) lives in Python
   core, keeping a single brain for the mesh.

## Full task flow

```
POST :9100/submit (Go gateway, ~ms overhead)
  → POST :9008/api/task (Python core)
    → router.classify()            [rules, ~0ms]
    → router.pick_nodes(tag)       [small|strong]
    → (hard only) short plan step, then execution prompt with plan
    → generate_on(node) → Ollama /api/generate (temperature 0.15)
    → sandbox.run_code(code, harness)   [-I + rlimits + killpg]
        ├─ ok  → status=done · telemetry("ok") → Telegram → phone
        └─ fail → log_attempt(trace_id) → repair_prompt(stderr) → loop ≤ MAX_ATTEMPTS
```

## SQLite schema (stdlib sqlite3, WAL-safe by isolation)

| Table | Purpose |
|---|---|
| `tasks` | task row: tier, status, attempts, model, node, ok, error |
| `attempts` | sandbox attempts: trace_id, idx, ok, exit_code, ms, error, taken |
| `events` | tail buffer for dashboard and notifications |

Review-subagent requirements integrated: `RLIMIT_CORE=0`, bounded attempts, unique
per-attempt trace ids, breaker semantics (loop stops after 3 failures and escalates),
no external dependencies anywhere in the hot path.

## Limitations (explicit)

- Sandboxed processes are resource-isolated but network-exposed to localhost only;
  true network isolation belongs in a container or VM.
- Heuristic routing misclassifies rare ambiguous prompts; keyword sets are plain lists
  meant to be tuned per domain.
- The Go gateway trusts the local core URL; TLS should terminate at the edge in
  multi-machine Tailscale deployments (or use Tailscale's own encrypted links).
