from pydantic import BaseModel
from typing import List


class SessionCreate(BaseModel):
    job_id: str


class SessionResponse(BaseModel):
    session_id: str
    job_id: str
    status: str
    created_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
