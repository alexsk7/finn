# Contributing to finn

## Running locally

```bash
git clone https://github.com/jacksonrc/finn.git
cd finn
./run.sh
```

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12+. The server starts at `http://localhost:8080` with auto-reload. A demo dataset is inserted on first run.

## Running checks

```bash
uv run python -m compileall app
```

There is not currently a committed test suite. If you add tests, document the exact command here and in [`docs/development.md`](docs/development.md).

## Project structure

```
app/
  main.py      FastAPI app wiring and startup jobs
  routers/     FastAPI route modules
  schemas/     Pydantic request schemas by domain
  services/    service-layer facades used by routers
  db.py        schema init and migrations
  queries.py   all read queries (plain SQL, no ORM)
  writer.py    all write operations
  seed.py      demo data (runs once on first start)
templates/     Jinja2 HTML templates
static/        CSS and static assets
```

The [`docs/`](docs/) directory has detailed reference material — architecture, schema, frontend conventions, and a development guide. Worth reading before making changes.

For service-layer refactors, follow [`docs/services-migration.md`](docs/services-migration.md).

## Making changes

- **New page**: add a query in `queries.py`, a route in `app/routers/pages.py`, a nav link in `base.html`, and a template. See the "Adding a new page" section in [`docs/development.md`](docs/development.md).
- **New API endpoint**: add the function in `queries.py` or `writer.py`, expose it via the relevant domain module in `app/services/`, add/extend request schemas in `app/schemas/<domain>.py`, add the route in `app/routers/api/<domain>.py`, then call it from the relevant template.
- **Schema changes**: add idempotent `ALTER TABLE` migrations in `db.py` (inside the try/except block after `executescript`).

## Submitting a PR

1. Fork the repo and create a branch from `main`.
2. Keep changes focused — one feature or fix per PR.
3. If touching the balance computation or snapshot logic, re-read the Balance Architecture section in [`docs/architecture.md`](docs/architecture.md) first.
4. Open a PR with a short description of what changed and why.

## Roadmap

Open tasks and ideas live in [TASKS.md](TASKS.md). The README has a shorter public roadmap summary.
