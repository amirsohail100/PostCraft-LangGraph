from pydantic import BaseModel


class GenerateRequest(BaseModel):
    topic: str


class GenerateResponse(BaseModel):
    draft: str
    is_approved: bool
    attempt: int
    reviewer_feedback: str
