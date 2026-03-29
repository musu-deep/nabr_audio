from pydantic import BaseModel
from typing import List, Optional


class ProcessRequest(BaseModel):
    file_id: str
    actions: List[str]
    silence_min_ms: Optional[int] = 900
    silence_keep_ms: Optional[int] = 120


class ChatRequest(BaseModel):
    message: str
