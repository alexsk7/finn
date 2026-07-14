from pydantic import BaseModel


class PortfolioSwitchBody(BaseModel):
    name: str


class PortfolioNewBody(BaseModel):
    name: str


class PortfolioRenameBody(BaseModel):
    name: str
