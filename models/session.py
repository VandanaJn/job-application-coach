from pydantic import BaseModel
from typing import Optional


class SessionResponse(BaseModel):
    session_id: str
    status: str
    created_at: str


class ResumeUploadResponse(BaseModel):
    session_id: str
    resume_text_length: int
