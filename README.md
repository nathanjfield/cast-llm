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

You can also place a `.env` file in the **project root** (same directory as `pyproject.toml`); settings load it when the process starts. Start Jupyter from the project root so `.env` is found.

3) **Weekly handover (live data)** — Run [notebooks/weekly_handover_pipeline.ipynb](notebooks/weekly_handover_pipeline.ipynb). Edit the date-range cell (UK local → UTC for `date_iso`). Output is written to `notebooks/weekly_handover.md`. Set `OLLAMA_MODEL` to a model you have in Ollama.

4) **Legacy POC (static JSON)** — Update `config/` to match your task:

   - Edit `config/context.txt` to provide the task context.
   - Edit `config/filters.json` to set the filters you want applied.

   Run [notebooks/poc_pipeline.ipynb](notebooks/poc_pipeline.ipynb) and point it at your `data/castnet.reports.json` export.

5) Inspect generated reports: `notebooks/weekly_handover.md` (handover) or `notebooks/report.md` (POC).
