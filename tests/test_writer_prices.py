from app.writer import refresh_prices


def test_refresh_prices_dedup_excludes_manual_and_maps_share_class(db_conn, mock_yfinance_ticker):
    db_conn.executescript("""
        INSERT INTO accounts (id, name, institution, type) VALUES
            (1, 'Brokerage A', 'Fidelity', 'brokerage'),
            (2, 'Brokerage B', 'Schwab', 'brokerage');

        INSERT INTO holdings (account_id, symbol, name, asset_class, shares, cost_basis, is_manual) VALUES
            (1, 'VTI', 'Vanguard Total Stock Market ETF', 'us_equity', 10, 200, 0),
            (2, 'VTI', 'Vanguard Total Stock Market ETF', 'us_equity', 5, 210, 0),
            (1, 'BRK.B', 'Berkshire Hathaway', 'us_equity', 2, 300, 0),
            (1, 'M:PRIVATE', 'Manual Asset', 'other', 1, 1, 1);
    """)

    mock_yfinance_ticker.set_fast("BRK-B", last_price=450.0, previous_close=448.0)

    result = refresh_prices()

    assert mock_yfinance_ticker.called_symbols.count("VTI") == 1
    assert "M:PRIVATE" not in mock_yfinance_ticker.called_symbols
    assert "BRK-B" in mock_yfinance_ticker.called_symbols
    assert "BRK.B" not in mock_yfinance_ticker.called_symbols

    brkb = db_conn.execute("SELECT price, prev_close FROM prices WHERE symbol='BRK.B'").fetchone()
    assert brkb is not None
    assert brkb["price"] == 450.0
    assert brkb["prev_close"] == 448.0
    assert all(row["symbol"] != "M:PRIVATE" for row in result["updated"])


def test_refresh_prices_falls_back_to_history(db_conn, mock_yfinance_ticker):
    db_conn.executescript("""
        INSERT INTO accounts (id, name, institution, type) VALUES
            (1, 'Brokerage', 'Fidelity', 'brokerage');

        INSERT INTO holdings (account_id, symbol, name, asset_class, shares, cost_basis, is_manual) VALUES
            (1, 'VXUS', 'Vanguard Total International', 'intl_equity', 5, 55, 0);
    """)

    mock_yfinance_ticker.set_fast_exception("VXUS")
    mock_yfinance_ticker.set_history("VXUS", [60.0, 62.0])

    refresh_prices()

    row = db_conn.execute("SELECT price, prev_close FROM prices WHERE symbol='VXUS'").fetchone()
    assert row is not None
    assert row["price"] == 62.0
    assert row["prev_close"] == 60.0


def test_refresh_prices_reports_failed_symbols_and_continues(db_conn, mock_yfinance_ticker, frozen_now):
    db_conn.executescript("""
        INSERT INTO accounts (id, name, institution, type) VALUES
            (1, 'Brokerage', 'Fidelity', 'brokerage');

        INSERT INTO holdings (account_id, symbol, name, asset_class, shares, cost_basis, is_manual) VALUES
            (1, 'FAIL', 'Failing Symbol', 'other', 1, 1, 0);
    """)

    mock_yfinance_ticker.set_fast_exception("FAIL")
    mock_yfinance_ticker.set_history_exception("FAIL")

    with frozen_now("2026-05-30 12:34:56"):
        result = refresh_prices()

    failed_symbols = {item["symbol"] for item in result["failed"]}
    updated_symbols = {item["symbol"] for item in result["updated"]}
    assert "FAIL" in failed_symbols
    assert "SPY" in updated_symbols

    spy_row = db_conn.execute("SELECT recorded_at FROM prices WHERE symbol='SPY'").fetchone()
    assert spy_row is not None
    assert spy_row["recorded_at"] == "2026-05-30 12:34:56"
