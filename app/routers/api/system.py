from fastapi import APIRouter, HTTPException

from app.schemas.system import ResetBody
from app.services.system import reset_all_data

router = APIRouter(tags=["system"])


@router.post("/reset")
async def api_reset(body: ResetBody):
    if body.confirm != "RESET":
        raise HTTPException(status_code=400, detail="confirm must be 'RESET'")
    reset_all_data()
    return {"ok": True}
