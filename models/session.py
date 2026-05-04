from pydantic import BaseModel, model_validator
from typing import Optional


class SessionResponse(BaseModel):
    session_id: str
    status: str
    created_at: str


class ResumeUploadResponse(BaseModel):
    session_id: str
    resume_text_length: int


class JobRequest(BaseModel):
    url: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_description: Optional[str] = None

    @model_validator(mode="after")
    def require_url_or_description(self):
        if not self.url and not self.job_description:
            raise ValueError("Either url or job_description must be provided")
        return self


class JobResponse(BaseModel):
    session_id: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_description: str
