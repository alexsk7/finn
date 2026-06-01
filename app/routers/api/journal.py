from fastapi import APIRouter

from app.queries import get_journal
from app.schemas.journal import JournalBody, JournalUpdateBody
from app.writer import add_journal_entry, delete_journal_entry, update_journal_entry

router = APIRouter(tags=["journal"])


@router.get("/journal")
async def api_journal(limit: int = 100):
    return get_journal(limit)


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
