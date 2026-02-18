cast-llm: poc analysis of castnet reports

Minimal setup:

1) Create and activate a virtualenv, then install dependencies:

```bash
uv venv
source .venv/bin/activate
uv sync
```

2) Update `config/` to match your task:
   - Edit `config/context.txt` to provide the task context.
   - Edit `config/filters.json` to set the filters you want applied.

3) Run the notebook [poc_pipeline.ipynb](notebooks/poc_pipeline.ipynb)
   - Make sure the path to your castnet reports data is correct.

4) Inspect the generated report at `notebooks/report.md`.
