# Services Migration Plan

## Goal

Keep routing and transport logic thin while preserving existing API contracts, DB schema behavior, and frontend payload shapes. Most domains now call `app.queries.py`, `app.writer.py`, `app.csv_mapper.py`, or `app.profile.py` directly; only a small number of behavior-owning helpers remain in `app/services/`.

## Current state

- App entrypoint: `app/main.py`
- Routers: `app/routers/pages.py` and `app/routers/api/*.py`
- Behavior-owning services remain only where they add domain rules:
  - `app/services/investments.py`
  - `app/services/real_estate.py`
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

- Add domain service modules under `app/services/` where they meaningfully own behavior.
- Route handlers call those helpers when a domain has orchestration or validation worth centralizing.

### Phase 3 (completed): Orchestration extraction and consolidation

- Move multi-step business orchestration into the smallest useful owning layer.
- Keep low-level SQL in `queries.py` and `writer.py`.
- Delete passthrough service modules once routers can call lower-level modules directly.

### Phase 4 (optional, future): Selective domain data extraction

- Extract only the data access that still benefits from a dedicated home.
- Keep compatibility wrappers only when they reduce churn or preserve a stable contract during migration.

## Per-domain checklist

1. Identify router endpoints for the domain.
2. Decide whether the logic belongs in a shared helper, a router, or the underlying data module.
3. Move orchestration and validation out of the router only when there is a real behavior boundary to own.
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
