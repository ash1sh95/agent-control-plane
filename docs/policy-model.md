# Policy model

A **policy** is a pure function `ToolCall -> PolicyResult | None`.
Returning `None` means "no opinion". The rule judge collects all non-None
results and applies the **strictest** verdict:

```
deny  >  require_approval  >  allow
```

Built-in policies (`src/agent_control_plane/policies.py`):

| Policy | Denies | Requires approval |
|---|---|---|
| `prompt-injection` | args matching injection patterns ("ignore previous instructions", "bypass the policy", "exfiltrate", mode-switch phrases) | — |
| `sensitive-data` | args carrying secret-shaped payloads (`password:`, `api_key=`, SSN, card assignments) | — |
| `tool-risk` | deletes of `/prod`, `/etc`, `production` paths | `shell_command` (always), `delete_file`, `export_data`, email to non-allowlisted domains |
| `file-access` | path traversal (`..`, absolute paths), secrets-looking files (`.env`, `credentials`, `id_rsa`) | — |
| `calculator-safety` | expressions with anything beyond arithmetic characters | — |

## Writing your own
See `examples/custom_policy.py`. Add the function to the policy list when
constructing `RuleBasedJudge` — no gate changes, no subclassing. House rules
("deploys need a second approver", "no external email on Fridays") are
one-function changes, which is the point: **policy should be cheaper to
change than the agent**.

## Design stance
Deterministic rules are the default judge on purpose. A control plane whose
decisions cannot be reproduced in a unit test cannot be evaluated, audited,
or defended in an architecture review. Learned judges (see `LLMJudge`)
*add* signal on top; they never replace the floor.
