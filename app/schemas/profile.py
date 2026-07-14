from pydantic import BaseModel


class ProfileBody(BaseModel):
    user_name: str = ""
    currency_symbol: str = "$"
