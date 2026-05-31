# Services Migration Plan

## Goal

Move business orchestration behind domain service modules while preserving existing API contracts, DB schema behavior, and frontend payload shapes.

## Current state

- App entrypoint: `app/main.py`
- Routers: `app/routers/pages.py` and `app/routers/api/*.py`
- Domain services: `app/services/*.py`
- Core data modules remain authoritative implementations:
  - `app/queries.py` for read SQL
  - `app/writer.py` for write SQL and mutations

## Migration principles

1. Keep behavior stable: endpoints, response shapes, and side effects must not change unless explicitly requested.
2. Prefer incremental extraction: move one domain at a time.
3. Keep tests green after each domain move.
4. Avoid large cross-cutting rewrites.
5. Keep SQL close to data modules until a domain is mature enough to extract safely.

## Phases

### Phase 1 (completed): Routing split

- Split API routes into domain router modules under `app/routers/api/`.
- Keep page routes in `app/routers/pages.py`.

### Phase 2 (completed): Service boundary introduction

- Add domain service modules under `app/services/`.
- Route handlers call service functions rather than importing `queries.py`/`writer.py` directly.

### Phase 3 (in progress): Orchestration move into services

- Move multi-step business orchestration from routers into services first.
- Keep low-level SQL in `queries.py` and `writer.py` unless extraction is required.

### Phase 4 (optional, future): Domain data extraction

- Extract domain-specific data access from `queries.py`/`writer.py` into service-local helpers or domain data modules.
- Keep a compatibility layer during transition to avoid large breakage.

## Per-domain checklist

1. Identify router endpoints for the domain.
2. Ensure each endpoint calls a service function.
3. Move orchestration and validation from router to service where practical.
4. Keep endpoint schemas and payloads unchanged.
5. Add/update tests for the domain.
6. Run focused tests, then full suite.
7. Update docs if behavior or code location expectations changed.

## Testing expectations

- Start with focused runs (`tests/test_api_smoke.py`, `tests/test_scheduler.py`, plus domain-specific tests).
- Run full suite before merge.

## Documentation touchpoints after each migration slice

- `docs/development.md`
- `docs/architecture.md`
- `CONTRIBUTING.md`
- `copilot-instructions.md`
- `TASKS.md` when roadmap/task wording references old paths
