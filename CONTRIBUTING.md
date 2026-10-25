# Contributing — Aodı-MeshAI

Thanks for your interest. This project deliberately keeps a **zero-dependency,
stdlib-first** discipline. Please respect it.

## Ground rules

1. **Python core**: standard library only (`http.server`, `sqlite3`, `resource`,
   `subprocess`, `json`, `re`, `urllib`). No pip packages.
2. **Gateway**: Go standard library only. No external modules — `go.mod` has no
   dependencies and should stay that way.
3. **Telemetry**: Node with zero npm deps (built-in `http`/`https` only).
4. **Bounded autonomy**: keep `MAX_ATTEMPTS` semantics safe; any new automated
   retry/repair cycle must stay bounded, logged and per-attempt audited
   (unique `trace_id`, exit code, duration).
5. **English docs**: README / ARCHITECTURE / CHANGELOG / SETUP / CONTRIBUTING /
   BENCHMARKS are English-only. Inline code comments may be Arabic or English.
6. **Contact/import hygiene inside generated code stays unsafe by design** —
   harden the sandbox, never loosen it.

## Dev workflow

```bash
python3 core/server.py --port 9008        # core
cd gateway && gofmt -w . && go vet ./... && go build -o ../bin/meshai-gateway .
./../bin/meshai-gateway                   # gateway
node telemetry/relay.js                   # optional relay

python3 tests/test_meshai.py -v           # must pass: no network, no Ollama
```

## Pull requests

- One logical change per PR; describe the behavior change in one sentence.
- Tests must pass on CI (Python 3.11, Go 1.21, Node 20).
- For new storage columns, extend the `CREATE TABLE` + `storage.py` and note it
  in CHANGELOG under `Unreleased`.

## Reporting issues

Include: OS, Ollama version, core log (`/api/events` tail), task id and the
`attempts` rows from SQLite if the issue is about the healing loop.

## License

MIT © 2026 Baran Avisat. By contributing you agree your contributions are
licensed under the same MIT license.
