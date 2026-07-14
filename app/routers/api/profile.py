from fastapi import APIRouter

from app.profile import get_profile, save_profile
from app.schemas.profile import ProfileBody

router = APIRouter(tags=["profile"])


@router.get("/profile")
async def api_profile_get():
    return get_profile()


@router.post("/profile")
async def api_profile_save(body: ProfileBody):
    save_profile(body.user_name, body.currency_symbol)
    return {"ok": True}
