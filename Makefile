.PHONY: setup hooks lint format typecheck check test run backup refresh snapshot

PORT ?= 8080

setup:
	mise trust
	mise install
	$(MAKE) hooks
	mise exec -- uv sync

hooks:
	git config core.hooksPath .githooks

lint:
	mise exec -- ruff check --fix .

format:
	mise exec -- ruff format .

typecheck:
	mise exec -- ty check .

check: lint typecheck

test:
	mise exec -- uv run pytest

run:
	./run.sh $(PORT)

backup:
	mise exec -- uv run python scripts/backup.py

refresh:
	curl -s -X POST http://localhost:$(PORT)/api/prices/refresh | python3 -m json.tool

snapshot:
	@echo "Open http://localhost:$(PORT)/data and use the Snapshot tab to record balances."
