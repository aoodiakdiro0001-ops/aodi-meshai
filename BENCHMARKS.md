# BENCHMARKS — Aodı-MeshAI v1.0.0

All numbers below are from a **real live session on 2026-10-25** — not synthetic
values. Setup: 1× Mac (Ollama, `qwen2.5-coder` + `gemma4:12b`) + 1× second
laptop `excalibur-laptop` (LAN `192.168.1.117`, `qwen2.5-coder`) as a registered
mesh node. Re-run the same commands to reproduce on your hardware.

## Routing (deterministic, zero LLM calls)

| Metric | Measured |
|---|---|
| Classification latency | **22–25 µs** per call |
| Throughput (single core) | **≈ 44,000 classifications / sec** |
| Method | 4 prompts × 2,500 calls via `core/router.classify` |
| Live tier results | easy (score 0–1), hard (score 12) ✓ |

## Gateway (Go, :9100 → :9008)

| Metric | Measured |
|---|---|
| `POST /submit` overhead | **2–7 ms** typical, 19 ms max over 6 submissions |
| `X-Gateway-Latency-Ms` header | exposed on every proxied task |

Latency buckets available live at `GET :9100/stats`.

## Sandbox (isolated execution)

| Metric | Measured (8 executions) |
|---|---|
| Execution overhead | **22–45 ms** median ≈ 35 ms |
| Harness pass-through | `assert` lines run inside the same isolated process |

## Task-level live results

| Task | Tier | Node / model | Result | Notes |
|---|---|---|---|---|
| `f(xs)` sum | easy | mesh-small / qwen2.5-coder | **done, 1 attempt**, sandbox 22 ms | gateway 7 ms |
| `divide` (explicit zero-case in prompt) | easy | mesh-small / qwen2.5-coder | **done, 1 attempt**, sandbox 33 ms | gateway 2 ms |
| `divide` (no zero-case hint, pre-fix core) | easy | mesh-small | **failed honestly at 3/3 attempts** | bounded loop stopped, 3 trace_ids in `attempts` table |
| `divide` rerun (post-fix core) | easy | mesh-small / qwen2.5-coder | **done, 1 attempt**, total **3.0 s** | harness disclosed to model |
| `eval_expr` (async/pipeline/redis/parser prompt) | **hard** | **mesh-strong / gemma4:12b** | **done after 1 repair round** | attempt 1 `exit 1` → auto-repair → attempt 2 `exit 0` (35 ms) |

Total wall time for the hard task: ~12 min on a GPU that was also serving other
jobs (plan step + two generations + repair); sandbox rounds stayed ≤ 36 ms.

## Cross-node (LAN mesh)

| Metric | Measured |
|---|---|
| Fleet ping (mac local) | 4–12 ms |
| Fleet ping (`excalibur-laptop`, LAN) | **27–32 ms** |
| Direct generation probe on laptop | **9.5 s** round-trip, first token→end |
| Fleet health | **3 / 3 nodes OK** |

## Self-healing loop evidence (SQLite `attempts` table)

```
492648d397  #1 first-shot   ok=0 exit=1   (pre-fix core, no harness disclosed)
492648d397  #2 repair-loop  ok=0 exit=1
492648d397  #3 repair-loop  ok=0 exit=1   → status=failed (bounded at MAX_ATTEMPTS)
c85fd5ee20  #1 first-shot   ok=1 exit=0   (post-fix, harness disclosed)
f1845d756f  #1 first-shot   ok=0 exit=1   (hard, strong node)
f1845d756f  #2 repair-loop  ok=1 exit=0   → status=done (1 repair round)
```

### Lesson captured during this live run

Repair rounds must disclose the **test harness** to the model, not only the
stderr — the exact failing assertions carry the required behavior. Deployed in
v1.0.0: the harness is appended to the first prompt and to every repair round;
the delivered code is cleaned of echoed harness lines.

## Honest caveats

- Single-session measurements on Apple-Silicon-class GPU with Ollama
  serializing concurrent requests; scale your expectations to your hardware.
- Small prompts (≤ 100 tokens) with low temperature (0.15).
- Generation latency dominates end-to-end time; router + sandbox overhead is
  negligible (~25 µs + ~35 ms).
