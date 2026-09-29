from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class PushRequest(BaseModel):
    do_reset: Optional[int] = 0

class SearchRequest(BaseModel):
    text: str
    reranker_limit: Optional[int] = 20
    limit: Optional[int] = 5

class ChatRequest(BaseModel):
    text: str
    conversation_uuid: Optional[UUID] = None

    limit: int = 10
    reranker_limit: int = 20
    title: Optional[str] = "New conversation"

    latitude: float | None = None
    longitude: float | None = None