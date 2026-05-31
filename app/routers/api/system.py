from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.writes import reset_all_data

router = APIRouter(tags=["system"])


class ResetBody(BaseModel):
    confirm: str


@router.post("/reset")
async def api_reset(body: ResetBody):
    if body.confirm != "RESET":
        raise HTTPException(status_code=400, detail="confirm must be 'RESET'")
    reset_all_data()
    return {"ok": True}
