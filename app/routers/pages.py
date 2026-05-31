from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.services.profile import get_profile

router = APIRouter(tags=["pages"])


def _page(request: Request, template: str, active: str, **extra) -> HTMLResponse:
    profile = get_profile()
    context = {"active": active, "profile": profile, **extra}
    return request.app.state.templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return _page(request, "dashboard.html", "dashboard")


@router.get("/landing", response_class=HTMLResponse)
async def landing_page(request: Request):
    return _page(request, "landing.html", "landing")


@router.get("/investments", response_class=HTMLResponse)
async def investments_page(request: Request):
    return _page(request, "investments.html", "investments")


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request):
    return _page(request, "accounts.html", "accounts")


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
async def account_detail_page(request: Request, account_id: int):
    return _page(request, "account_detail.html", "accounts", account_id=account_id)


@router.get("/real-estate", response_class=HTMLResponse)
async def real_estate_page(request: Request):
    return _page(request, "real_estate.html", "realestate")


@router.get("/tax", response_class=HTMLResponse)
async def tax_page(request: Request):
    return _page(request, "tax.html", "tax")


@router.get("/rebalance", response_class=HTMLResponse)
async def rebalance_page(request: Request):
    return _page(request, "rebalance.html", "rebalance")


@router.get("/journal", response_class=HTMLResponse)
async def journal_page(request: Request):
    return _page(request, "journal.html", "journal")


@router.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request):
    return _page(request, "budget.html", "budget")


@router.get("/data", response_class=HTMLResponse)
async def data_page(request: Request):
    return _page(request, "data.html", "data")
