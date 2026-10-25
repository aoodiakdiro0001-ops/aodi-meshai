# Changelog — Aodı-MeshAI

## 1.0.0 — 2026-10-25

First public release.

### Core (Python stdlib, zero deps)
- Deterministic rule-based task router: `easy / medium / hard` tiers with no LLM
  classification call (weighted keywords + prompt length + structural patterns).
- Self-healing execution loop bounded at `MAX_ATTEMPTS=3` (env
  `AODIM_MAX_ATTEMPTS`): failed sandbox runs feed their exact stderr back to the
  model for automatic repair, then the task is honestly marked `failed`.
- The evaluation harness is disclosed to the model in the first prompt **and**
  in every repair round (a fix found during live testing: without the harness
  the repair round kept failing on the same edge case).
- Isolated sandbox: `python -I`, `RLIMIT_AS` (512MB default), `RLIMIT_CPU`,
  `RLIMIT_NPROC=24`, `RLIMIT_CORE=0`, process-group `SIGKILL` on timeout.
- Task decomposition pre-step for `hard` tier (short plan, then execution).
- SQLite audit trail: `tasks`, `attempts` (unique `trace_id` per attempt,
  exit code, duration, error, taken=first-shot/repair-loop), `events`.
- Delivered code is cleaned of any echoed harness lines before storage.
- Non-blocking telemetry: all notifications run in daemon threads and can
  never break a task.

### Gateway (Go stdlib)
- `/submit` reverse proxy with atomic counters, latency buckets and an
  `X-Gateway-Latency-Ms` header; `/health`, `/stats`.

### Telemetry (Node, zero npm deps)
- Telegram Bot relay (`/emit` → real phone notifications), event buffer,
  `/health`, `/last`.

### Dashboard
- Arabic RTL live dashboard showing the tier, per-attempt sandbox results,
  exit codes, durations and final generated code.

### Known limitations
- Sandbox is resource- and timeout-isolated; network isolation requires a
  container (`--network none`) for production use.
- Heuristic routing can misclassify rare ambiguous prompts; keyword sets are
  plain editable lists.
