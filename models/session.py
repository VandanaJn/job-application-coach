from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class SessionCreate(BaseModel):
    job_id: str


class SessionResponse(BaseModel):
    session_id: str
    job_id: str
    status: SessionStatus
    created_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]


class QuestionItem(BaseModel):
    question: str
    category: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatus
    questions: Optional[List[QuestionItem]] = None
    error: Optional[str] = None
