def test_auto_refresh_prices_only_runs_for_existing_db_paths(import_main_safely, monkeypatch, tmp_path):
    main = import_main_safely

    existing_db = tmp_path / "existing.db"
    existing_db.write_text("", encoding="utf-8")
    missing_db = tmp_path / "missing.db"

    monkeypatch.setattr(
        "app.portfolio.list_portfolios",
        lambda: [
            {"name": "existing", "path": str(existing_db)},
            {"name": "missing", "path": str(missing_db)},
        ],
    )

    called: list[str] = []

    def fake_refresh_prices(*, db_path: str):
        called.append(db_path)
        return {"updated": [], "failed": []}

    monkeypatch.setattr(main, "refresh_prices", fake_refresh_prices)

    main._auto_refresh_prices()

    assert called == [str(existing_db)]


def test_auto_refresh_prices_isolates_failures_between_portfolios(import_main_safely, monkeypatch, tmp_path):
    main = import_main_safely

    good_db = tmp_path / "good.db"
    bad_db = tmp_path / "bad.db"
    good_db.write_text("", encoding="utf-8")
    bad_db.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "app.portfolio.list_portfolios",
        lambda: [
            {"name": "bad", "path": str(bad_db)},
            {"name": "good", "path": str(good_db)},
        ],
    )

    called: list[str] = []

    def fake_refresh_prices(*, db_path: str):
        called.append(db_path)
        if db_path == str(bad_db):
            raise RuntimeError("boom")
        return {"updated": [], "failed": []}

    monkeypatch.setattr(main, "refresh_prices", fake_refresh_prices)

    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(main.logger, "error", lambda msg, name, exc: errors.append((name, str(exc))))

    main._auto_refresh_prices()

    assert str(bad_db) in called
    assert str(good_db) in called
    assert ("bad", "boom") in errors
