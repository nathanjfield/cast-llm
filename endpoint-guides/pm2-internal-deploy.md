# PM2 Internal Deployment Runbook (`cast-llm-api`)

This runbook is for operating the AI API on an internal network for CastNet.

## Prerequisites

- Repo checked out at `/home/castalum/dev/cast-llm`
- `uv` installed and usable
- `pm2` installed on host (`npm i -g pm2`)
- Mongo reachable from host (`CAST_LLM_MONGODB_URI` etc.)
- Ollama running with required model (default `gemma4:latest`)

## Start Service with PM2

From repo root:

```bash
mkdir -p logs
uv sync
pm2 start ecosystem.config.cjs
pm2 status
```

Expected process name: `cast-llm-api`

## Health and Endpoint Smoke Checks

### Local host check

```bash
curl -sS http://127.0.0.1:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

### API check (small range)

```bash
curl -sS -X POST http://127.0.0.1:8000/handover/weekly \
  -H "Content-Type: application/json" \
  -d '{
    "start_local": "2026-04-22T06:00:00",
    "end_local": "2026-04-22T14:00:00",
    "timezone": "Europe/London",
    "model": "gemma4:latest",
    "context_note": "smoke test window"
  }'
```

Plant glossary from `artifacts/shift_glossary/finalglossary.json` is included automatically unless you pass `"use_glossary": false`. Optional override: `"glossary_path": "artifacts/shift_glossary/finalglossary.json"`.

```bash
curl -sS -X POST http://127.0.0.1:8000/handover/weekly \
  -H "Content-Type: application/json" \
  -d '{
    "start_local": "2026-06-09T18:00:00",
    "end_local": "2026-06-16T18:00:00",
    "timezone": "Europe/London",
    "model": "gemma4:latest"
  }'
```

Expected: JSON with `run_id`, `machine_count`, `machines`.

### From CastNet-reachable internal host

Replace host/IP and run:

```bash
curl -sS http://<ai-server-internal-ip>:8000/healthz
```

If this fails, check internal firewall and route policy for TCP `8000`.

## PM2 Operations

```bash
pm2 status
pm2 logs cast-llm-api
pm2 restart cast-llm-api
pm2 stop cast-llm-api
pm2 delete cast-llm-api
```

## Restart Resilience

1. Validate auto-restart on crash:

```bash
pm2 pid cast-llm-api
kill -9 <pid>
pm2 status
```

Expected: PM2 restarts process (uptime resets, status returns `online`).

2. Validate startup persistence:

```bash
pm2 startup
pm2 save
pm2 list
```

After reboot, confirm:

```bash
pm2 list
curl -sS http://127.0.0.1:8000/healthz
```

## Failure Triage

- `ServerSelectionTimeoutError` in logs: Mongo URI/network/auth issue.
- LLM errors/timeouts: Ollama service unavailable or model missing.
- `422` from API: bad request payload shape.
- `400` from API: invalid range logic (`start_local`/`end_local`).

Use:

```bash
pm2 logs cast-llm-api --lines 200
```

to inspect recent failures quickly.
