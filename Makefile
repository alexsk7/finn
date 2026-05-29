.PHONY: setup run backup refresh snapshot

PORT ?= 8080

setup:
	mise trust
	mise install
	mise exec -- uv sync

run:
	./run.sh $(PORT)

backup:
	mise exec -- uv run python scripts/backup.py

refresh:
	curl -s -X POST http://localhost:$(PORT)/api/prices/refresh | python3 -m json.tool

snapshot:
	@echo "Open http://localhost:$(PORT)/data and use the Snapshot tab to record balances."
