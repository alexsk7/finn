from app import csv_mapper as csvm
from app import profile as profile_mod
from app import queries as q
from app import writer as w


def test_budget_module_exports_work(monkeypatch):
    monkeypatch.setattr("app.queries.get_budget_month", lambda month=None: {"month": month or "2026-05"})
    monkeypatch.setattr("app.queries.get_budget_categories_full", lambda: [{"id": 1, "name": "Housing"}])
    monkeypatch.setattr("app.writer.add_budget_category", lambda *args: {"ok": True})
    monkeypatch.setattr("app.writer.update_budget_category", lambda *args: {"ok": True})
    monkeypatch.setattr("app.writer.delete_budget_category", lambda *args: None)
    monkeypatch.setattr("app.writer.save_budget_month", lambda *args: {"ok": True})
    monkeypatch.setattr("app.writer.copy_budget_month", lambda *args: {"ok": True})

    assert q.get_budget_month("2026-05")["month"] == "2026-05"
    assert q.get_budget_categories_full()[0]["name"] == "Housing"
    assert w.add_budget_category("Housing", 1000, "expense")["ok"] is True
    assert w.update_budget_category(1, "Housing", 1200)["ok"] is True
    assert w.save_budget_month("2026-05", [], None)["ok"] is True
    assert w.copy_budget_month("2026-06", "2026-05", False)["ok"] is True


def test_transactions_module_exports_work(monkeypatch):
    monkeypatch.setattr("app.queries.get_transactions", lambda *args: [{"id": 1}])
    monkeypatch.setattr("app.writer.add_transaction", lambda *args: {"id": 1})
    monkeypatch.setattr("app.writer.update_transaction", lambda *args: {"ok": True})
    monkeypatch.setattr("app.writer.bulk_update_transaction_category", lambda *args: {"updated": 2})
    monkeypatch.setattr("app.writer.delete_transaction", lambda *args: None)
    monkeypatch.setattr("app.writer.import_transaction_csv", lambda *args: {"inserted": 1})
    monkeypatch.setattr("app.csv_mapper.detect_transaction_csv_mapping", lambda csv_text: {"ok": True})

    assert q.get_transactions(100) == [{"id": 1}]
    assert w.add_transaction("2026-05-01", 10, "expense", "food", None, None, None, False)["id"] == 1
    assert w.update_transaction(1, "2026-05-01", 10, "expense", "food", None, None, None)["ok"] is True
    assert w.bulk_update_transaction_category([1, 2], "food")["updated"] == 2
    assert w.import_transaction_csv("date,amount", None, None)["inserted"] == 1
    assert csvm.detect_transaction_csv_mapping("date,amount")["ok"] is True


def test_profile_and_system_modules_work(monkeypatch):
    monkeypatch.setattr("app.profile.get_profile", lambda: {"user_name": "Alex"})
    monkeypatch.setattr("app.profile.save_profile", lambda *args: None)
    monkeypatch.setattr("app.writer.reset_all_data", lambda: None)

    assert profile_mod.get_profile()["user_name"] == "Alex"
    profile_mod.save_profile("Alex", "$")
    w.reset_all_data()