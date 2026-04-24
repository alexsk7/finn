# Contributing to finctl

## Running locally

```bash
git clone https://github.com/jacksonrc/finctl.git
cd finctl
./run.sh
```

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12+. The server starts at `http://localhost:8080` with auto-reload. A demo dataset is inserted on first run.

## Running tests

```bash
uv run python tests/test_tax.py
```

## Project structure

```
app/
  db.py        schema init and migrations
  queries.py   all read queries (plain SQL, no ORM)
  writer.py    all write operations
  seed.py      demo data (runs once on first start)
main.py        FastAPI routes and Pydantic models
templates/     Jinja2 HTML templates
static/        CSS and static assets
```

The [`docs/`](docs/) directory has detailed reference material — architecture, schema, frontend conventions, and a development guide. Worth reading before making changes.

## Making changes

- **New page**: add a query in `queries.py`, a route in `main.py`, a nav link in `base.html`, and a template. See the "Adding a new page" section in CLAUDE.md.
- **New API endpoint**: add the function in `queries.py` or `writer.py`, a Pydantic model + route in `main.py`, then call it from the relevant template.
- **Schema changes**: add idempotent `ALTER TABLE` migrations in `db.py` (inside the try/except block after `executescript`).

## Submitting a PR

1. Fork the repo and create a branch from `main`.
2. Keep changes focused — one feature or fix per PR.
3. If touching the balance computation or snapshot logic, re-read the Balance Architecture section in CLAUDE.md first.
4. Open a PR with a short description of what changed and why.

## Roadmap

Open tasks and ideas live in [TASKS.md](TASKS.md).
