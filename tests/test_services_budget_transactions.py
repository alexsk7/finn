from app.services import budget as budget_svc
from app.services import transactions as txn_svc


def test_budget_service_exports_work(monkeypatch):
    monkeypatch.setattr("app.services.budget.get_budget_month", lambda month=None: {"month": month or "2026-05"})
    monkeypatch.setattr("app.services.budget.get_budget_categories_full", lambda: [{"id": 1, "name": "Housing"}])
    monkeypatch.setattr("app.services.budget.add_budget_category", lambda *args: {"ok": True})
    monkeypatch.setattr("app.services.budget.update_budget_category", lambda *args: {"ok": True})
    monkeypatch.setattr("app.services.budget.delete_budget_category", lambda *args: None)
    monkeypatch.setattr("app.services.budget.save_budget_month", lambda *args: {"ok": True})
    monkeypatch.setattr("app.services.budget.copy_budget_month", lambda *args: {"ok": True})

    assert budget_svc.get_budget_month("2026-05")["month"] == "2026-05"
    assert budget_svc.get_budget_categories_full()[0]["name"] == "Housing"
    assert budget_svc.add_budget_category("Housing", 1000, "expense")["ok"] is True
    assert budget_svc.update_budget_category(1, "Housing", 1200)["ok"] is True
    assert budget_svc.save_budget_month("2026-05", [], None)["ok"] is True
    assert budget_svc.copy_budget_month("2026-06", "2026-05", False)["ok"] is True


def test_transactions_service_exports_work(monkeypatch):
    monkeypatch.setattr("app.services.transactions.get_transactions", lambda *args: [{"id": 1}])
    monkeypatch.setattr("app.services.transactions.add_transaction", lambda *args: {"id": 1})
    monkeypatch.setattr("app.services.transactions.update_transaction", lambda *args: {"ok": True})
    monkeypatch.setattr("app.services.transactions.bulk_update_transaction_category", lambda *args: {"updated": 2})
    monkeypatch.setattr("app.services.transactions.delete_transaction", lambda *args: None)
    monkeypatch.setattr("app.services.transactions.import_transaction_csv", lambda *args: {"inserted": 1})
    monkeypatch.setattr("app.services.transactions.detect_transaction_csv_mapping", lambda csv_text: {"ok": True})

    assert txn_svc.get_transactions(100) == [{"id": 1}]
    assert txn_svc.add_transaction("2026-05-01", 10, "expense", "food", None, None, None, False)["id"] == 1
    assert txn_svc.update_transaction(1, "2026-05-01", 10, "expense", "food", None, None, None)["ok"] is True
    assert txn_svc.bulk_update_transaction_category([1, 2], "food")["updated"] == 2
    assert txn_svc.import_transaction_csv("date,amount", None, None)["inserted"] == 1
    assert txn_svc.detect_transaction_csv_mapping("date,amount")["ok"] is True
