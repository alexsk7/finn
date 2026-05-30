.PHONY: setup hooks lint format typecheck check test coverage coverage-html run backup refresh snapshot

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

coverage:
	mise exec -- uv run pytest --override-ini="addopts=-q --strict-markers --cov=app --cov=main --cov-report=term-missing:skip-covered --cov-report=xml:coverage.xml"

coverage-html:
	mise exec -- uv run pytest --override-ini="addopts=-q --strict-markers --cov=app --cov=main --cov-report=term-missing:skip-covered --cov-report=xml:coverage.xml --cov-report=html:htmlcov"
	mise exec -- uv run python tests/coverage_dashboard.py
	mise exec -- uv run python -c "from pathlib import Path; import webbrowser; webbrowser.open(Path('htmlcov/dashboard.html').resolve().as_uri())"

run:
	./run.sh $(PORT)

backup:
	mise exec -- uv run python scripts/backup.py

refresh:
	curl -s -X POST http://localhost:$(PORT)/api/prices/refresh | python3 -m json.tool

snapshot:
	@echo "Open http://localhost:$(PORT)/data and use the Snapshot tab to record balances."
