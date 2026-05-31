from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.journal import add_journal_entry, delete_journal_entry, get_journal, update_journal_entry

router = APIRouter(tags=["journal"])


@router.get("/journal")
async def api_journal(limit: int = 100):
    return get_journal(limit)


class JournalBody(BaseModel):
    title: str
    body: Optional[str] = None
    entry_date: Optional[str] = None
    tags: Optional[str] = None
    is_milestone: bool = False
    milestone_value: Optional[float] = None


@router.post("/journal")
async def api_journal_post(entry: JournalBody):
    return add_journal_entry(
        entry.title,
        entry.body,
        entry.entry_date,
        entry.tags,
        entry.is_milestone,
        entry.milestone_value,
    )


class JournalUpdateBody(BaseModel):
    title: str
    body: Optional[str] = None
    entry_date: Optional[str] = None
    tags: Optional[str] = None
    is_milestone: bool = False
    milestone_value: Optional[float] = None


@router.put("/journal/{entry_id}")
async def api_journal_update(entry_id: int, body: JournalUpdateBody):
    return update_journal_entry(
        entry_id,
        body.title,
        body.body,
        body.entry_date,
        body.tags,
        body.is_milestone,
        body.milestone_value,
    )


@router.delete("/journal/{entry_id}")
async def api_journal_delete(entry_id: int):
    delete_journal_entry(entry_id)
    return {"ok": True}
