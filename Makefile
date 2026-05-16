.PHONY: run backup refresh snapshot

PORT ?= 8080

run:
	./run.sh $(PORT)

backup:
	uv run python scripts/backup.py

refresh:
	curl -s -X POST http://localhost:$(PORT)/api/prices/refresh | python3 -m json.tool

snapshot:
	@echo "Open http://localhost:$(PORT)/data and use the Snapshot tab to record balances."
