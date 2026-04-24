"""Finance mission control — local-only FastAPI server."""

import atexit
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler

from app.db import init_db
from app.seed import seed_demo
from app.queries import (
    get_dashboard_summary,
    get_allocation,
    get_tax_summary,
    get_rebalance,
    get_journal,
    get_cashflow_by_category,
    get_accounts_summary,
    get_real_estate,
    get_amortization,
    get_allocation_targets,
    get_budget_categories_full,
    get_transactions,
    get_ticker_data,
    get_account_by_id,
    get_account_transactions,
)
from app.writer import (
    refresh_prices,
    update_price,
    save_snapshot,
    add_journal_entry,
    update_journal_entry,
    delete_journal_entry,
    add_transaction,
    update_transaction,
    delete_transaction,
    update_real_estate,
    add_real_estate,
    delete_real_estate,
    link_real_estate_account,
    add_holding,
    update_holding,
    delete_holding,
    get_all_holdings_raw,
    add_account,
    update_account,
    delete_account,
    import_snapshot_csv,
    import_transaction_csv,
    import_holdings_csv,
    reset_all_data,
    save_mortgage_config,
    upsert_property_cost,
    upsert_allocation_target,
    add_budget_category,
    update_budget_category,
    delete_budget_category,
)

init_db()
seed_demo()

logger = logging.getLogger(__name__)

def _auto_refresh_prices():
    from app.portfolio import list_portfolios
    for p in list_portfolios():
        path = Path(p["path"])
        if not path.is_absolute():
            path = Path(__file__).parent / path
        if not path.exists():
            continue
        try:
            refresh_prices(db_path=str(path))
            logger.info("Auto price refresh: %s", p["name"])
        except Exception as exc:
            logger.error("Auto price refresh failed for %s: %s", p["name"], exc)

_scheduler = BackgroundScheduler(daemon=True)
_scheduler.add_job(
    _auto_refresh_prices,
    'cron',
    day_of_week='mon-fri',
    hour=16,
    minute=5,
    timezone='America/New_York',
)
_scheduler.start()
atexit.register(lambda: _scheduler.shutdown(wait=False))

app = FastAPI(title="Finance Mission Control", docs_url=None, redoc_url=None)

BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


def page(request: Request, template: str, active: str) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name=template, context={"active": active})


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return page(request, "dashboard.html", "dashboard")


@app.get("/investments", response_class=HTMLResponse)
async def investments_page(request: Request):
    return page(request, "investments.html", "investments")


@app.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request):
    return page(request, "accounts.html", "accounts")


@app.get("/accounts/{account_id}", response_class=HTMLResponse)
async def account_detail_page(request: Request, account_id: int):
    return templates.TemplateResponse(
        request=request,
        name="account_detail.html",
        context={"active": "accounts", "account_id": account_id},
    )


@app.get("/real-estate", response_class=HTMLResponse)
async def real_estate_page(request: Request):
    return page(request, "real_estate.html", "realestate")


@app.get("/tax", response_class=HTMLResponse)
async def tax_page(request: Request):
    return page(request, "tax.html", "tax")


@app.get("/rebalance", response_class=HTMLResponse)
async def rebalance_page(request: Request):
    return page(request, "rebalance.html", "rebalance")


@app.get("/journal", response_class=HTMLResponse)
async def journal_page(request: Request):
    return page(request, "journal.html", "journal")


@app.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request):
    return page(request, "budget.html", "budget")


@app.get("/data", response_class=HTMLResponse)
async def data_page(request: Request):
    return page(request, "data.html", "data")


# ── Read API ──────────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
async def api_dashboard():
    return get_dashboard_summary()


@app.get("/api/allocation")
async def api_allocation():
    return get_allocation()


@app.get("/api/tax")
async def api_tax():
    return get_tax_summary()


@app.get("/api/rebalance")
async def api_rebalance(new_cash: float = 0.0):
    return get_rebalance(new_cash)


@app.get("/api/journal")
async def api_journal(limit: int = 100):
    return get_journal(limit)


@app.get("/api/cashflow")
async def api_cashflow():
    return get_cashflow_by_category()


@app.get("/api/accounts")
async def api_accounts():
    return get_accounts_summary()


@app.get("/api/accounts/{account_id}")
async def api_account_detail(account_id: int):
    acct = get_account_by_id(account_id)
    if acct is None:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return acct


@app.get("/api/accounts/{account_id}/transactions")
async def api_account_transactions(account_id: int, limit: int = 500):
    return get_account_transactions(account_id, limit)


@app.get("/api/real-estate")
async def api_real_estate():
    return get_real_estate()


@app.get("/api/allocation-targets")
async def api_allocation_targets():
    return get_allocation_targets()


@app.get("/api/budget-categories")
async def api_budget_categories():
    return get_budget_categories_full()


@app.get("/api/transactions")
async def api_transactions_list():
    return get_transactions()


@app.get("/api/ticker")
async def api_ticker():
    return get_ticker_data()


# ── Write API ─────────────────────────────────────────────────────────────────

@app.post("/api/prices/refresh")
async def api_prices_refresh():
    return refresh_prices()


class PriceUpdate(BaseModel):
    symbol: str
    price: float

@app.post("/api/prices/manual")
async def api_price_manual(body: PriceUpdate):
    update_price(body.symbol, body.price)
    return {"ok": True, "symbol": body.symbol.upper(), "price": body.price}


class SnapshotBody(BaseModel):
    account_balances: list[dict]
    snapshot_date: Optional[str] = None
    notes: Optional[str] = None

@app.post("/api/snapshot")
async def api_snapshot(body: SnapshotBody):
    return save_snapshot(body.account_balances, body.snapshot_date, body.notes)


class JournalBody(BaseModel):
    title: str
    body: Optional[str] = None
    entry_date: Optional[str] = None
    tags: Optional[str] = None
    is_milestone: bool = False
    milestone_value: Optional[float] = None

@app.post("/api/journal")
async def api_journal_post(entry: JournalBody):
    return add_journal_entry(
        entry.title, entry.body, entry.entry_date,
        entry.tags, entry.is_milestone, entry.milestone_value,
    )


class TransactionBody(BaseModel):
    txn_date: str
    amount: float
    direction: str
    category: str
    description: Optional[str] = None
    account_id: Optional[int] = None
    recurring: bool = False

@app.post("/api/transactions")
async def api_transaction_post(txn: TransactionBody):
    return add_transaction(
        txn.txn_date, txn.amount, txn.direction,
        txn.category, txn.description, txn.account_id, txn.recurring,
    )


class RealEstateUpdate(BaseModel):
    property_id: int
    estimated_value: float
    mortgage_balance: float

@app.post("/api/real-estate/update")
async def api_real_estate_update(body: RealEstateUpdate):
    return update_real_estate(body.property_id, body.estimated_value, body.mortgage_balance)


class RealEstateAdd(BaseModel):
    name: str
    estimated_value: float
    mortgage_balance: float = 0
    address: Optional[str] = None
    purchase_price: float = 0
    purchase_date: Optional[str] = None
    account_id: Optional[int] = None

@app.post("/api/real-estate")
async def api_real_estate_add(body: RealEstateAdd):
    return add_real_estate(body.name, body.estimated_value, body.mortgage_balance,
                           body.address, body.purchase_price, body.purchase_date, body.account_id)

class RealEstateLinkBody(BaseModel):
    account_id: Optional[int] = None

@app.post("/api/real-estate/{property_id}/link-account")
async def api_real_estate_link(property_id: int, body: RealEstateLinkBody):
    return link_real_estate_account(property_id, body.account_id)

@app.delete("/api/real-estate/{property_id}")
async def api_real_estate_delete(property_id: int):
    return delete_real_estate(property_id)


@app.get("/api/real-estate/{property_id}/amortization")
async def api_amortization(property_id: int):
    data = get_amortization(property_id)
    if data is None:
        return {"config": None, "schedule": [], "summary": {}}
    return data


class MortgageConfigBody(BaseModel):
    property_id: int
    loan_amount: float
    annual_rate_pct: float
    term_months: int
    monthly_payment: float
    start_date: str
    appreciation_rate: float = 2.5

@app.post("/api/real-estate/mortgage-config")
async def api_mortgage_config(body: MortgageConfigBody):
    return save_mortgage_config(
        body.property_id, body.loan_amount, body.annual_rate_pct,
        body.term_months, body.monthly_payment, body.start_date,
        body.appreciation_rate,
    )


class PropertyCostBody(BaseModel):
    property_id: int
    cost_year: int
    cost_month: int
    amount: float
    memo: Optional[str] = None

@app.post("/api/real-estate/cost")
async def api_property_cost(body: PropertyCostBody):
    return upsert_property_cost(
        body.property_id, body.cost_year, body.cost_month, body.amount, body.memo
    )


# ── Holdings CRUD ──────────────────────────────────────────────────────────────

@app.get("/api/holdings")
async def api_holdings_all():
    return get_all_holdings_raw()


class HoldingBody(BaseModel):
    account_id: int
    symbol: str
    asset_class: str
    shares: float
    cost_basis: float
    name: Optional[str] = None

@app.post("/api/holdings")
async def api_holding_add(body: HoldingBody):
    return add_holding(body.account_id, body.symbol, body.asset_class,
                       body.shares, body.cost_basis, body.name)

@app.put("/api/holdings/{holding_id}")
async def api_holding_update(holding_id: int, body: HoldingBody):
    return update_holding(holding_id, body.account_id, body.symbol, body.asset_class,
                          body.shares, body.cost_basis, body.name)

@app.delete("/api/holdings/{holding_id}")
async def api_holding_delete(holding_id: int):
    delete_holding(holding_id)
    return {"ok": True}


# ── Account CRUD ───────────────────────────────────────────────────────────────

class AccountBody(BaseModel):
    name: str
    institution: str
    type: str
    notes: Optional[str] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    opening_balance: Optional[float] = None

@app.post("/api/accounts")
async def api_account_add(body: AccountBody):
    return add_account(body.name, body.institution, body.type, body.notes,
                       body.interest_rate, body.minimum_payment, body.opening_balance)

class AccountUpdateBody(BaseModel):
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    opening_balance: Optional[float] = None

@app.put("/api/accounts/{account_id}")
async def api_account_update(account_id: int, body: AccountUpdateBody):
    return update_account(account_id, body.interest_rate, body.minimum_payment, body.opening_balance)

@app.delete("/api/accounts/{account_id}")
async def api_account_delete(account_id: int):
    return delete_account(account_id)


# ── Allocation Targets ─────────────────────────────────────────────────────────

class AllocationTargetBody(BaseModel):
    asset_class: str
    target_pct: float

@app.post("/api/allocation-targets")
async def api_allocation_target_upsert(body: AllocationTargetBody):
    return upsert_allocation_target(body.asset_class, body.target_pct)


# ── Budget Categories ──────────────────────────────────────────────────────────

class BudgetCategoryBody(BaseModel):
    name: str
    monthly_target: float
    direction: str = "expense"

class BudgetCategoryUpdate(BaseModel):
    name: str
    monthly_target: float

@app.post("/api/budget-categories")
async def api_budget_category_add(body: BudgetCategoryBody):
    return add_budget_category(body.name, body.monthly_target, body.direction)

@app.put("/api/budget-categories/{category_id}")
async def api_budget_category_update(category_id: int, body: BudgetCategoryUpdate):
    return update_budget_category(category_id, body.name, body.monthly_target)

@app.delete("/api/budget-categories/{category_id}")
async def api_budget_category_delete(category_id: int):
    delete_budget_category(category_id)
    return {"ok": True}


# ── Journal CRUD ───────────────────────────────────────────────────────────────

class JournalUpdateBody(BaseModel):
    title: str
    body: Optional[str] = None
    entry_date: Optional[str] = None
    tags: Optional[str] = None
    is_milestone: bool = False
    milestone_value: Optional[float] = None

@app.put("/api/journal/{entry_id}")
async def api_journal_update(entry_id: int, body: JournalUpdateBody):
    return update_journal_entry(entry_id, body.title, body.body, body.entry_date,
                                body.tags, body.is_milestone, body.milestone_value)

@app.delete("/api/journal/{entry_id}")
async def api_journal_delete(entry_id: int):
    delete_journal_entry(entry_id)
    return {"ok": True}


# ── Transaction CRUD ───────────────────────────────────────────────────────────

class TransactionUpdateBody(BaseModel):
    txn_date: str
    amount: float
    direction: str
    category: str
    description: Optional[str] = None
    account_id: Optional[int] = None

@app.put("/api/transactions/{txn_id}")
async def api_transaction_update(txn_id: int, body: TransactionUpdateBody):
    return update_transaction(
        txn_id, body.txn_date, body.amount, body.direction,
        body.category, body.description, body.account_id,
    )

@app.delete("/api/transactions/{txn_id}")
async def api_transaction_delete(txn_id: int):
    delete_transaction(txn_id)
    return {"ok": True}


# ── CSV Snapshot Import ────────────────────────────────────────────────────────

class SnapshotImportBody(BaseModel):
    csv_text: str

@app.post("/api/snapshots/import-csv")
async def api_snapshot_import_csv(body: SnapshotImportBody):
    return import_snapshot_csv(body.csv_text)


# ── CSV Transaction Import ─────────────────────────────────────────────────────

class TransactionImportBody(BaseModel):
    csv_text: str
    account_id: Optional[int] = None

@app.post("/api/transactions/import-csv")
async def api_transaction_import_csv(body: TransactionImportBody):
    return import_transaction_csv(body.csv_text, body.account_id)


# ── CSV Holdings Import ────────────────────────────────────────────────────────

class HoldingsImportBody(BaseModel):
    csv_text: str
    account_id: int

@app.post("/api/holdings/import-csv")
async def api_holdings_import_csv(body: HoldingsImportBody):
    return import_holdings_csv(body.csv_text, body.account_id)


# ── Reset ──────────────────────────────────────────────────────────────────────

@app.post("/api/reset")
async def api_reset():
    reset_all_data()
    return {"ok": True}


# ── Portfolio Management ───────────────────────────────────────────────────────

@app.get("/api/portfolios")
async def api_portfolios():
    from app.portfolio import _load, list_portfolios
    cfg = _load()
    return {"active": cfg["active"], "portfolios": list_portfolios()}


class PortfolioSwitchBody(BaseModel):
    name: str


@app.post("/api/portfolio/switch")
async def api_portfolio_switch(body: PortfolioSwitchBody):
    from app.portfolio import set_active
    try:
        set_active(body.name)
        init_db()  # apply any pending migrations to the newly active DB
        return {"ok": True, "active": body.name}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


class PortfolioNewBody(BaseModel):
    name: str


@app.post("/api/portfolio/new")
async def api_portfolio_new(body: PortfolioNewBody):
    from app.portfolio import create_portfolio
    try:
        entry = create_portfolio(body.name)
        init_db()    # init schema on the new (now active) DB
        seed_demo()  # seed demo data
        return {"ok": True, **entry}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


class PortfolioRenameBody(BaseModel):
    name: str


@app.put("/api/portfolio/{portfolio_name:path}")
async def api_portfolio_rename(portfolio_name: str, body: PortfolioRenameBody):
    from app.portfolio import rename_portfolio
    try:
        entry = rename_portfolio(portfolio_name, body.name)
        return {"ok": True, **entry}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.delete("/api/portfolio/{portfolio_name:path}")
async def api_portfolio_delete(portfolio_name: str):
    from app.portfolio import delete_portfolio
    try:
        delete_portfolio(portfolio_name)
        return {"ok": True}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
