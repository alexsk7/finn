from pydantic import BaseModel


class ResetBody(BaseModel):
    confirm: str
