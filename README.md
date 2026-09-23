cast-llm: poc analysis of castnet reports

Minimal setup:

1) Create and activate a virtualenv, then install dependencies:

```bash
uv venv
source .venv/bin/activate
uv sync
```

2) **MongoDB (weekly handover)** — CastNet must be reachable at the URI you configure. Optional environment variables (prefix `CAST_LLM_`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CAST_LLM_MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `CAST_LLM_MONGODB_DB` | `castnet` | Database name |
| `CAST_LLM_REPORTS_COLLECTION` | `reports` | Shift reports collection |
| `CAST_LLM_HANDOVER_GLOSSARY_ENABLED` | `true` | Append plant glossary to weekly handover context |
| `CAST_LLM_HANDOVER_GLOSSARY_PATH` | `artifacts/shift_glossary/finalglossary.json` | Curated glossary JSON (`entries` array) |

You can also place a `.env` file in the **project root** (same directory as `pyproject.toml`); settings load it when the process starts. Start Jupyter from the project root so `.env` is found.

3) **Weekly handover (live data)** — Run [notebooks/weekly_handover_pipeline.ipynb](notebooks/weekly_handover_pipeline.ipynb) or `POST /handover/weekly` from CastNet. Edit the date-range cell (UK local → UTC for `date_iso`). Summaries are limited to equipment flagged **DCM** in CastNet (`equipment.dcm: true`). Assets that only share the name prefix, such as DCM ladders, are left out. By default the service loads **`artifacts/shift_glossary/finalglossary.json`** and injects term/expansion/definition into handover context. Disable with `use_glossary: false` on the API or `CAST_LLM_HANDOVER_GLOSSARY_ENABLED=false`. The notebook runs each tag in `HANDOVER_MODELS` and writes markdown to `/home/castalum/thinclient_drives/AI Serve/` (`weekly_handover_<model_tag>.md`).

4) **One-time glossary backfill (live data)** — build a merged glossary from historical weekly windows:

```bash
cast-llm-glossary-backfill --years 2026,2025 --resume
```

Outputs are written under `artifacts/shift_glossary/`:

- `glossary.json` merged glossary + patterns
- `checkpoint.json` completed week list for resume
- `weeks/<YYYY-MM-DD>.json` per-week extraction artifacts

5) **Legacy POC (static JSON)** — Update `config/` to match your task:

   - Edit `config/context.txt` to provide the task context.
   - Edit `config/filters.json` to set the filters you want applied.

   Run [notebooks/poc_pipeline.ipynb](notebooks/poc_pipeline.ipynb) and point it at your `data/castnet.reports.json` export.

6) Inspect generated reports: handover markdown under `AI Serve/` (see step 3) or `notebooks/report.md` (POC).

## PM2 Deployment (Internal Network)

Use this when exposing the API to CastNet internally.

1) Install dependencies and ensure `uv` works:

```bash
uv sync
```

2) Ensure runtime env is present:

- Put `CAST_LLM_*` variables in repo-root `.env` (preferred), or
- Export them in shell before starting PM2.

3) Create logs directory:

```bash
mkdir -p logs
```

4) Start with PM2:

```bash
pm2 start ecosystem.config.cjs
pm2 status
```

5) Verify endpoint:

```bash
curl http://127.0.0.1:8000/healthz
```

6) Common PM2 lifecycle commands:

```bash
pm2 logs cast-llm-api
pm2 restart cast-llm-api
pm2 stop cast-llm-api
pm2 delete cast-llm-api
```

7) Enable startup persistence across reboot:

```bash
pm2 startup
pm2 save
```

If the host reboots, PM2 restores `cast-llm-api` from saved state.
