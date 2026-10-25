# Contributing

Welcome -- especially attack cases. The house rules:

1. **Eval first.** A new attack class lands as a failing case in
   `evals/dataset.jsonl` *before* the policy that stops it.
2. **Policies are functions.** `ToolCall -> PolicyResult | None`, pure,
   no I/O, unit-tested. If a policy needs config, pass it at construction.
3. **Fail closed.** Any new judge/backend must return require-approval on
   error, never allow. Tests must prove it.
4. **No secrets, ever.** Keys come from the environment (`.env.example`
   documents the names). Test fixtures use obvious fakes.
5. Run before you push: `make lint && make test && make eval`
   (CI enforces all three; a false allow in evals fails the build).

## Dev setup
```bash
pip install -e ".[dev]"
pytest -q && PYTHONPATH=src python -m agent_control_plane.cli eval
```

## Style
Ruff (config in `pyproject.toml`), type hints on public functions,
comments only where the *why* is non-obvious.
