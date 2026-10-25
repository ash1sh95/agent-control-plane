.PHONY: install test eval demo lint clean
install:  ## install in editable mode with dev tools
	pip install -e ".[dev]"
test:     ## run the unit test suite
	pytest -q
eval:     ## run the gate eval harness
	PYTHONPATH=src python -m agent_control_plane.cli eval
demo:     ## run the gated demo agent
	PYTHONPATH=src python -m agent_control_plane.cli demo
lint:     ## lint with ruff (if installed)
	ruff check src tests || true
clean:
	rm -rf .acp .pytest_cache **/__pycache__
