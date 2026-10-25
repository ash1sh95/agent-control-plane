# Databricks notebook source
# MAGIC %md
# MAGIC # Agent Control Plane on Databricks
# MAGIC Runs the judge-before-action gate in front of Unity-Catalog-function-style
# MAGIC tools, executes the 17-case eval harness, and logs results to MLflow
# MAGIC (and Delta, when Unity Catalog is writable). Workspace-agnostic:
# MAGIC configure via widgets -- no hosts or tokens anywhere in this notebook.

# COMMAND ----------

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "acp_demo")
dbutils.widgets.text("experiment", "/Shared/agent-control-plane")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
EXPERIMENT = dbutils.widgets.get("experiment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install the package from this repo (Git folder) or PyPI-style path

# COMMAND ----------

# In a Git folder this notebook lives in <repo>/databricks/, so the package
# source is one level up. Adjust ACP_PACKAGE_PATH if you vendored it elsewhere.
import os, sys
repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))
# Alternative: %pip install /Workspace/<path-to-repo>   (uncomment in workspace)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. UC-function-style tools behind the gate
# MAGIC Bodies are demo callables. In production each one calls a real UC
# MAGIC function, e.g. via SQL: SELECT catalog.schema.my_tool(:arg) -- the gate
# MAGIC code does not change, because it governs *calls*, not implementations.

# COMMAND ----------

from agent_control_plane import ControlPlaneGate, ToolCall, Verdict

def uc_style_lookup(query: str) -> str:
    """Stand-in for a governed UC function: catalog.schema.lookup_docs(query)."""
    return f"[uc-function result for '{query}']"

gate = ControlPlaneGate(
    audit_path=f"/Volumes/{CATALOG}/{SCHEMA}/acp_audit/audit.jsonl"
    if False else None,  # set a Volume path for persistent audit in your workspace
)
call = ToolCall("file_lookup", {"query": "gate"}, session_id="nb-session", case_id="nb-demo")
decision = gate.evaluate(call)
print(decision.verdict, "-", decision.reason)
assert decision.verdict == Verdict.ALLOW
print(uc_style_lookup(**call.arguments))

blocked = gate.evaluate(ToolCall("file_lookup", {"query": "x", "path": "../.env"}, "nb-session", "nb-demo"))
print(blocked.verdict, "-", blocked.reason)  # expect: deny (secrets/traversal)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Run the eval harness and log it: MLflow metrics + Delta table

# COMMAND ----------

import mlflow
from agent_control_plane.eval_runner import run_evals

mlflow.set_experiment(EXPERIMENT)
results = run_evals(os.path.join(repo_root, "evals", "dataset.jsonl"))
with mlflow.start_run(run_name="acp-gate-eval"):
    mlflow.log_metrics({"pass_rate": results["pass_rate"],
                        "false_allows": results["false_allows"],
                        "false_denies": results["false_denies"],
                        "cases": results["total"]})
    mlflow.log_param("gate", "rule-based-judge-v1")
    mlflow.log_dict({"rows": results["rows"]}, "eval_rows.json")
print(f"pass {results['passed']}/{results['total']}  false_allows={results['false_allows']}")

try:
    from pyspark.sql import Row
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
    df = spark.createDataFrame([Row(id=r["id"], category=r["category"], expected=r["expected"],
                                    got=r["got"], passed=r["pass"]) for r in results["rows"]])
    df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.acp_eval_results")
    print(f"Wrote results to {CATALOG}.{SCHEMA}.acp_eval_results")
except Exception as exc:  # UC not writable in this workspace: display instead
    print(f"Delta write skipped ({type(exc).__name__}); results are in the MLflow run above.")
    display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps in a real workspace
# MAGIC - Replace the demo tool bodies with real UC function calls / Vector Search queries.
# MAGIC - Point the judge at a small Foundation Model API endpoint (see model_serving_gate_example.py).
# MAGIC - Persist audit to a Delta table and approvals to your chat tool of choice.
