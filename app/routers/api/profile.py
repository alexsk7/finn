from fastapi import APIRouter

from app.schemas.profile import ProfileBody
from app.services.profile import get_profile, save_profile

router = APIRouter(tags=["profile"])


@router.get("/profile")
async def api_profile_get():
    return get_profile()


@router.post("/profile")
async def api_profile_save(body: ProfileBody):
    save_profile(body.user_name, body.currency_symbol)
    return {"ok": True}
