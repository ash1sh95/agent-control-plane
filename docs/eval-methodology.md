# Eval methodology

Most agent evals score *answers*. This harness scores **decisions** —
for a control plane, the verdict *is* the product.

## Dataset
`evals/dataset.jsonl` — 17 cases in four buckets:
- **normal** (4): benign calls that must be allowed (friction check)
- **attack** (7): traversal, secrets access/exfiltration, prompt injection
  in tool arguments, calculator code injection, unknown tool, prod delete
- **approval** (4): shell, tmp-file delete, external email, data export
- **abuse** (2): duplicate call, rate-limit flooding — both expressed with
  `setup` calls that execute first, so stateful defences are really tested

## Metrics
- **Pass rate** — exact verdict match.
- **False allows** — expected deny/approval, gate allowed. The dangerous
  metric; CI fails the build if this is non-zero (`acp eval` exit code).
- **False denies** — expected allow, gate blocked. The friction metric;
  a gate that denies everything is "secure" and useless.

## Current results (run 2026-10-25, this repo)
17/17 pass, 100.0% pass rate, 0 false allows, 0 false denies.
Reproduce: `make eval`.

## Extending
Add a line to the JSONL: `{"id", "category", "tool", "arguments",
"expected", "setup"?}`. New attack classes belong here *before* they get
a policy — write the failing case first, then the policy that passes it.
That loop is the whole development method of this repo.
