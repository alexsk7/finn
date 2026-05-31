from __future__ import annotations

from app import writer
from app.writer import (
    add_account,
    add_budget_category,
    add_holding,
    add_journal_entry,
    add_real_estate,
    bulk_update_transaction_category,
    copy_budget_month,
    delete_account,
    delete_budget_category,
    delete_holding,
    delete_journal_entry,
    delete_real_estate,
    delete_transaction,
    get_all_holdings_raw,
    import_holdings_csv,
    import_snapshot_csv,
    reset_all_data,
    save_budget_month,
    save_mortgage_config,
    save_snapshot,
    update_account,
    update_budget_category,
    update_holding,
    update_journal_entry,
    update_price,
    update_real_estate,
    update_transaction,
    upsert_allocation_target,
    upsert_property_cost,
)


def test_update_price_upserts_uppercase_symbol(db_conn):
    update_price("brk.b", 511.25)

    row = db_conn.execute("SELECT symbol, price FROM prices ORDER BY id DESC LIMIT 1").fetchone()

    assert row is not None
    assert row["symbol"] == "BRK.B"
    assert row["price"] == 511.25


def test_save_snapshot_calculates_totals_and_upserts(minimal_seed_data, db_conn):
    balances = [
        {"account_id": 1, "balance": 1000},
        {"account_id": 2, "balance": 2000},
        {"account_id": 3, "balance": 500},
        {"account_id": 999, "balance": 123},
    ]

    result = save_snapshot(balances, snapshot_date="2026-06-01", notes="first")

    assert result["snapshot_date"] == "2026-06-01"
    assert result["liquid_cash"] == 1000.0
    assert result["invested_total"] == 2000.0
    assert result["debt_total"] == 500.0
    assert result["home_equity"] == 200000.0
    assert result["net_worth"] == 202500.0

    updated = save_snapshot([{"account_id": 1, "balance": 900}], snapshot_date="2026-06-01", notes="updated")
    assert updated["net_worth"] == 200900.0

    snap = db_conn.execute("SELECT notes, net_worth FROM snapshots WHERE snapshot_date='2026-06-01'").fetchone()
    acct_snaps = db_conn.execute(
        "SELECT COUNT(*) FROM account_snapshots WHERE snapshot_id=(SELECT id FROM snapshots WHERE snapshot_date='2026-06-01')"
    ).fetchone()[0]

    assert snap is not None
    assert snap["notes"] == "updated"
    assert snap["net_worth"] == 200900.0
    assert acct_snaps == 1


def test_journal_entry_add_update_delete_flow(db_conn):
    created = add_journal_entry("Title", body="Body", tags="tag1", is_milestone=True, milestone_value=100000)

    changed = update_journal_entry(
        created["id"],
        title="Edited",
        body="Edited body",
        entry_date="2026-05-11",
        tags="tag2",
        is_milestone=False,
        milestone_value=None,
    )

    assert changed["title"] == "Edited"
    assert changed["entry_date"] == "2026-05-11"
    assert changed["is_milestone"] == 0

    delete_journal_entry(created["id"])

    row = db_conn.execute("SELECT id FROM journal_entries WHERE id=?", (created["id"],)).fetchone()

    assert row is None


def test_private_category_and_month_helpers(frozen_now):
    assert writer._clean_category(None) == "uncategorized"
    assert writer._clean_category("  groceries  ") == "groceries"

    assert writer._normalize_month(" 2026-11 ") == "2026-11"

    try:
        writer._normalize_month("2026-7")
        assert False, "Expected ValueError for missing zero-padded month"
    except ValueError:
        pass

    try:
        writer._normalize_month("2026/11")
        assert False, "Expected ValueError for invalid month format"
    except ValueError:
        pass

    with frozen_now("2026-07-15 10:00:00"):
        assert writer._current_month() == "2026-07"


def test_holdings_add_update_delete_and_list(minimal_seed_data, db_conn):
    added = add_holding(
        account_id=2,
        symbol="bondx",
        asset_class="bond",
        shares=12,
        cost_basis=9.5,
        name="Bond Fund",
        is_manual=True,
    )
    assert added["symbol"] == "BONDX"
    assert added["is_manual"] == 1

    changed = update_holding(
        holding_id=added["id"],
        account_id=2,
        symbol="bondx",
        asset_class="bond",
        shares=15,
        cost_basis=10.0,
        name="Bond Fund Updated",
        is_manual=False,
    )
    assert changed["shares"] == 15.0
    assert changed["is_manual"] == 0

    holdings = get_all_holdings_raw()
    assert any(h["symbol"] == "BONDX" and h["account_name"] == "Test Brokerage" for h in holdings)

    delete_holding(added["id"])
    row = db_conn.execute("SELECT id FROM holdings WHERE id=?", (added["id"],)).fetchone()
    assert row is None


def test_account_add_update_delete_guards_and_success(init_schema, minimal_seed_data):
    new_acct = add_account("Spare", "Local", "checking", opening_balance=50)
    assert new_acct["name"] == "Spare"
    assert new_acct["opening_balance"] == 50.0

    updated = update_account(new_acct["id"], interest_rate=3.4, minimum_payment=20, opening_balance=75)
    assert updated["interest_rate"] == 3.4
    assert updated["opening_balance"] == 75.0

    with_holdings = delete_account(2)
    assert with_holdings["ok"] is False
    assert "holding" in with_holdings["error"].lower()

    with_txns = delete_account(1)
    assert with_txns["ok"] is False
    assert "transaction" in with_txns["error"].lower()

    deleted = delete_account(new_acct["id"])
    assert deleted == {"ok": True}


def test_import_snapshot_csv_inserts_and_updates(minimal_seed_data, db_conn):
    csv_text = """snapshot_date,net_worth,liquid_cash,invested_total,home_equity
2026-04-01,210000,6000,3500,200500
2026-07-01,220000,7000,4000,205000
"""

    result = import_snapshot_csv(csv_text)

    assert result["inserted"] == 1
    assert result["updated"] == 1
    assert result["skipped"] == 0

    row = db_conn.execute("SELECT net_worth FROM snapshots WHERE snapshot_date='2026-04-01'").fetchone()

    assert row is not None
    assert row["net_worth"] == 210000.0


def test_import_holdings_csv_detects_header_and_updates_existing(minimal_seed_data, db_conn):
    csv_text = """Account Number,123456
Generated On,2026-05-10
Symbol,Description,Quantity,Cost Basis Total,Security Type
BND,US Bond Market,6,390,Bond
"""

    first = import_holdings_csv(csv_text, account_id=2)
    assert first["inserted"] == 1
    assert first["updated"] == 0

    second_csv = """Symbol,Description,Quantity,Cost Basis Total,Security Type
BND,US Bond Market,8,520,Bond
"""
    second = import_holdings_csv(second_csv, account_id=2)
    assert second["updated"] == 1

    row = db_conn.execute("SELECT shares, cost_basis FROM holdings WHERE account_id=2 AND symbol='BND'").fetchone()

    assert row is not None
    assert row["shares"] == 8.0
    assert row["cost_basis"] == 65.0


def test_mortgage_and_property_cost_upserts(init_schema, minimal_seed_data):
    cfg = save_mortgage_config(
        property_id=1,
        loan_amount=300000,
        annual_rate_pct=6.5,
        term_months=360,
        monthly_payment=2200,
        start_date="2024-01-01",
        appreciation_rate=3.0,
    )
    assert cfg["property_id"] == 1
    assert cfg["annual_rate_pct"] == 6.5

    cost = upsert_property_cost(1, 2026, 6, 450.5, "repair")
    assert cost["amount"] == 450.5
    assert cost["memo"] == "repair"

    changed = upsert_property_cost(1, 2026, 6, 500.0, "updated")
    assert changed["amount"] == 500.0
    assert changed["memo"] == "updated"


def test_upsert_allocation_target_updates_existing(init_schema, minimal_seed_data):
    out = upsert_allocation_target("bond", 25.0)
    assert out["asset_class"] == "bond"
    assert out["target_pct"] == 25.0


def test_budget_functions_save_copy_add_update_delete(db_conn):
    cat = add_budget_category("Utilities", 150, "expense")
    assert cat["name"] == "Utilities"

    changed = update_budget_category(cat["id"], "Utilities & Internet", 175)
    assert changed["name"] == "Utilities & Internet"
    assert changed["monthly_target"] == 175.0

    saved = save_budget_month(
        "2026-08",
        [
            {"category_id": cat["id"], "planned_amount": 180},
        ],
        notes="plan",
    )
    assert saved == {"ok": True, "month": "2026-08", "updated": 1}

    copied = copy_budget_month("2026-09", "2026-08", overwrite=False)
    assert copied["ok"] is True
    assert copied["copied"] == 1

    delete_budget_category(cat["id"])
    row = db_conn.execute("SELECT id FROM budget_categories WHERE id=?", (cat["id"],)).fetchone()
    assert row is None


def test_transaction_update_bulk_and_delete_flow(db_conn):
    normalized = writer.add_transaction("2026-05-01", 20, "expense", "   ", description="Normalized")
    assert normalized["category"] == "uncategorized"

    t1 = writer.add_transaction("2026-05-01", 20, "expense", "food", description="A")
    t2 = writer.add_transaction("2026-05-02", 40, "expense", "food", description="B")

    updated = update_transaction(
        t1["id"],
        txn_date="2026-05-03",
        amount=25,
        direction="income",
        category="  ",
        payee="Employer",
        description="Salary adj",
        account_id=None,
    )
    assert updated["txn_date"] == "2026-05-03"
    assert updated["category"] == "uncategorized"

    bulk = bulk_update_transaction_category([t1["id"], t2["id"], t1["id"], -1], "misc")
    assert bulk == {"updated": 2, "category": "misc"}

    delete_transaction(t2["id"])
    row = db_conn.execute("SELECT id FROM transactions WHERE id=?", (t2["id"],)).fetchone()
    assert row is None


def test_real_estate_add_link_update_delete(init_schema, minimal_seed_data):
    created = add_real_estate(
        name="Rental",
        estimated_value=300000,
        mortgage_balance=100000,
        address="123 Main",
        purchase_price=250000,
        purchase_date="2020-01-01",
        account_id=1,
    )
    assert created["name"] == "Rental"
    assert created["account_id"] == 1

    linked = writer.link_real_estate_account(created["id"], 2)
    assert linked["account_id"] == 2

    changed = update_real_estate(created["id"], estimated_value=320000, mortgage_balance=95000)
    assert changed["estimated_value"] == 320000.0
    assert changed["mortgage_balance"] == 95000.0

    deleted = delete_real_estate(created["id"])
    assert deleted == {"ok": True}

    missing = delete_real_estate(999999)
    assert missing["ok"] is False
    assert "not found" in missing["error"].lower()


def test_reset_all_data_clears_tables(minimal_seed_data, db_conn):
    reset_all_data()

    counts = {
        "accounts": db_conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0],
        "holdings": db_conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0],
        "transactions": db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
        "snapshots": db_conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
        "real_estate": db_conn.execute("SELECT COUNT(*) FROM real_estate").fetchone()[0],
        "budget_categories": db_conn.execute("SELECT COUNT(*) FROM budget_categories").fetchone()[0],
        "allocation_targets": db_conn.execute("SELECT COUNT(*) FROM allocation_targets").fetchone()[0],
        "journal_entries": db_conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0],
    }

    assert all(v == 0 for v in counts.values())
