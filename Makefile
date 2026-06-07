.PHONY: install ingest serve web-install web-dev dev test lint

install:
	python3.11 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

ingest:
	.venv/bin/python -m pipeline.ingest

serve:
	.venv/bin/python -m api.main

web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

dev:
	@echo "Run in two terminals:"
	@echo "  make serve"
	@echo "  make web-dev"

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check .
