from enum import Enum

from pydantic import BaseModel, Field


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    reviewer: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)
