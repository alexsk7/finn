# Copilot Instructions for finn

## Project Snapshot

- finn is a local-first personal finance dashboard.
- The app is single-process, with no auth, no external API dependencies for core functionality, and no build step.
- Data lives in SQLite and should stay local to the machine.
- The codebase favors small, focused changes over broad refactors.

## Primary Sources of Truth

- Read `README.md` for the product overview and top-level feature set.
- Read `docs/architecture.md` for system design and data flow.
- Read `docs/development.md` for repo conventions and workflows.
- Read `docs/services-migration.md` before making structural refactors.
- Read `docs/schema.md`, `docs/frontend.md`, and `docs/pages.md` when touching those areas.
- Read `TASKS.md` before making feature work if roadmap context matters.

## Architecture Rules

- Keep app wiring in `app/main.py`, routes in `app/routers/`, and route handlers thin.
- Route handlers should call domain services in `app/services/`.
- Keep read SQL in `app/queries.py` and write SQL in `app/writer.py` unless a migration step explicitly moves it.
- Prefer plain SQL over an ORM.
- Keep schema changes idempotent and place migrations in `app/db.py` after `executescript()` inside the existing try/except migration block.
- Use `CREATE INDEX IF NOT EXISTS` for indexes.
- Keep the app local-first; do not introduce cloud or network dependencies unless explicitly requested.
- Background work should stay consistent with the existing APScheduler usage in `app/main.py`.

## Backend Change Patterns

- For a new page: add a query function, add a route in `app/routers/pages.py`, add a sidebar link in `templates/base.html`, then create a template extending `base.html`.
- For a new API endpoint: add query/write helper(s), expose through a domain service in `app/services/`, add the Pydantic model and route in `app/routers/api/<domain>.py`, then call it from the relevant template.
- For data writes, keep logic in `app/writer.py` and return structured JSON responses.
- Preserve existing naming and data-shape conventions used by nearby code.
- Avoid introducing unnecessary abstraction layers.

## Frontend Change Patterns

- Templates use Jinja2 and vanilla JavaScript.
- Keep page logic in the template’s `{% block scripts %}` unless there is a strong reason to move it.
- Use the existing visual system in `static/style.css` and the current layout classes rather than adding a separate framework.
- When rendering user-controlled data with `innerHTML`, pass it through the global `esc()` helper from `templates/base.html`.
- Do not leave raw confidence scores or implementation details in the UI when a human-readable label would be clearer.
- Prefer explicit user actions over hidden automation when the workflow benefits from review.

## CSV Import Rules

- CSV imports belong inside the related tab, not in a standalone import page.
- Follow the established pattern: file picker, textarea paste area, preview, detection/review step, then import.
- For transaction CSVs, keep `payee` / `merchant` separate from `category`.
- Missing transaction categories should become `uncategorized` and be handled later in the inbox.
- Prefer clear mapping UI and reviewable detection results over opaque automation.
- If a CSV import needs mapping detection, wire detection and import as separate steps so the user can review before committing.

## Data and Safety Rules

- Keep all user-entered strings escaped before inserting them into HTML.
- Do not assume all CSVs or user imports are clean; validate and handle partial failures.
- Make date and amount parsing tolerant, but do not silently invent values.
- Preserve existing fallback behavior, especially for dates and account assignment.
- Keep import logic deterministic where possible.

## Testing and Validation

- Prefer the smallest useful test that covers the changed slice.
- Reuse fixtures from `tests/conftest.py`.
- Use `minimal_seed_data` for deterministic tests when possible.
- Mock Yahoo Finance access with `mock_yfinance_ticker`; do not depend on network access.
- Use `frozen_now` for time-sensitive assertions.
- After code changes, run the narrowest relevant test command first, then broader checks if needed.

## Standard Commands

- `make test`
- `make lint`
- `make typecheck`
- `make check`
- `make hooks`

For ad hoc Python commands, use the repo’s managed environment rather than system Python.

## Change Discipline

- Keep edits minimal and focused on the user’s requested behavior.
- Do not rewrite unrelated code or reformat large files without a reason.
- Do not delete user changes you did not make.
- Do not introduce new dependencies unless the problem clearly requires them.
- Prefer root-cause fixes over surface-level workarounds.

## When In Doubt

- Read the nearest existing implementation before inventing a new pattern.
- Follow the style of the file you are editing.
- If a change affects balances, budgets, or transaction import behavior, inspect the related docs before editing.
- If you are unsure whether a workflow belongs in backend, frontend, or docs, follow the existing architecture and place logic where similar code already lives.