.PHONY: setup hooks lint format typecheck check test coverage coverage-html coverage-new run backup refresh snapshot

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
	mise exec -- uv run coverage json --pretty-print -o coverage.json >/dev/null

coverage:
	mise exec -- uv run pytest --override-ini="addopts=-q --strict-markers --cov=app --cov-report=term:skip-covered"
	mise exec -- uv run coverage json --pretty-print -o coverage.json >/dev/null

coverage-new:
	$(MAKE) coverage
	mise exec -- uv run python scripts/check_new_code_coverage.py --auto-base --head HEAD --print-range

coverage-html:
	$(MAKE) coverage
	mise exec -- uv run coverage html -d htmlcov >/dev/null
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
