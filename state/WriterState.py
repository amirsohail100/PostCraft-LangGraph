from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class WriterState(TypedDict):
    topic: str
    messages: Annotated[list, add_messages]
    draft: str
    reviewer_feedback: str
    is_approved: bool
    attempt: int
