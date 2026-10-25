# Use it on Databricks in 10 minutes

Workspace-agnostic: no hosts, tokens, catalogs or schemas are hard-coded.
Everything comes from notebook widgets / environment variables.

## The 10-minute path
1. Upload this repo to your workspace (Repos / Git folders -> clone), or
   `pip install` the wheel in the notebook below.
2. Open `01_agent_control_plane_on_databricks.py` in a workspace.
3. Set the widgets: `catalog`, `schema`, `experiment` (defaults are safe:
   `main.acp_demo`, `/Shared/agent-control-plane`).
4. Run all. The notebook:
   - installs the package from the repo,
   - registers UC-function-*style* demo tools (plain Python callables with
     UC-style names/descriptions -- swap the bodies for real
     `catalog.schema.function` calls when you wire real tools),
   - puts the control-plane gate in front of them,
   - runs the 17-case eval harness,
   - logs the results to an **MLflow experiment** and writes a summary row
     set to a **Delta table** (`<catalog>.<schema>.acp_eval_results`) if UC
     is writable, or displays it if not.
5. Skim the MLflow run: pass rate, false allows, and per-case verdicts are
   logged as metrics/params -- the same numbers `acp eval` prints locally.

## Deploy it as a job / app
`databricks.yml` in this folder is a Databricks Asset Bundle skeleton:
copy it to the repo root, set `var.workspace_host` via your Databricks
CLI profile (never commit a host/token), then:

```bash
databricks bundle validate
databricks bundle deploy --target dev
databricks bundle run acp_eval_job
```

The bundle defines one job (run the eval notebook on serverless) and a
commented Databricks App block for hosting the approval queue UI later.

## Model Serving / Foundation Models behind the gate
See `model_serving_gate_example.py`: a Foundation Model API / Model
Serving endpoint is treated as *just another tool*. The agent proposes a
call, the gate judges it (cost ceiling, prompt-injection scan of the
payload, per-session rate limit), and only then does the endpoint get
invoked -- with usage metered by the router. This is the AI Gateway
pattern, reproduced at application level so it works even where a
gateway is not yet configured.
