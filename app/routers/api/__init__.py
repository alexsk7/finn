from fastapi import APIRouter

from app.routers.api.accounts import router as accounts_router
from app.routers.api.analytics import router as analytics_router
from app.routers.api.budget import router as budget_router
from app.routers.api.investments import router as investments_router
from app.routers.api.journal import router as journal_router
from app.routers.api.portfolios import router as portfolios_router
from app.routers.api.profile import router as profile_router
from app.routers.api.real_estate import router as real_estate_router
from app.routers.api.system import router as system_router
from app.routers.api.transactions import router as transactions_router

router = APIRouter(prefix="/api", tags=["api"])
router.include_router(analytics_router)
router.include_router(accounts_router)
router.include_router(real_estate_router)
router.include_router(investments_router)
router.include_router(budget_router)
router.include_router(journal_router)
router.include_router(transactions_router)
router.include_router(profile_router)
router.include_router(portfolios_router)
router.include_router(system_router)
