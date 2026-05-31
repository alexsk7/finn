from typing import Optional

from pydantic import BaseModel


class JournalBody(BaseModel):
    title: str
    body: Optional[str] = None
    entry_date: Optional[str] = None
    tags: Optional[str] = None
    is_milestone: bool = False
    milestone_value: Optional[float] = None


class JournalUpdateBody(BaseModel):
    title: str
    body: Optional[str] = None
    entry_date: Optional[str] = None
    tags: Optional[str] = None
    is_milestone: bool = False
    milestone_value: Optional[float] = None
