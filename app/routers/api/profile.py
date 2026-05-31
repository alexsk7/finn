from fastapi import APIRouter
from pydantic import BaseModel

from app.services.profile import get_profile, save_profile

router = APIRouter(tags=["profile"])


@router.get("/profile")
async def api_profile_get():
    return get_profile()


class ProfileBody(BaseModel):
    user_name: str = ""
    currency_symbol: str = "$"


@router.post("/profile")
async def api_profile_save(body: ProfileBody):
    save_profile(body.user_name, body.currency_symbol)
    return {"ok": True}
