from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class SessionCreate(BaseModel):
    job_id: str


class SessionResponse(BaseModel):
    session_id: str
    job_id: str
    status: SessionStatus
    created_at: str
    # Populated once the session has run; absent for pending/running rows.
    questions_count: Optional[int] = None
    total_tokens: Optional[int] = None


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
    usage: Optional[TokenUsage] = None
