from typing import Literal

from pydantic import BaseModel, Field, RootModel


FactCheckVerdict = Literal[
    "true",
    "mostly true",
    "unverified",
    "mostly false",
    "false",
]


class FactCheckRow(BaseModel):
    claim: str = Field(..., min_length=1)
    verdict: FactCheckVerdict
    confidence: int = Field(..., ge=0, le=100)
    sources: list[str] = Field(default_factory=list)
    explanation: str = Field(..., min_length=1)


class FactCheckResult(RootModel[list[FactCheckRow]]):
    root: list[FactCheckRow]
