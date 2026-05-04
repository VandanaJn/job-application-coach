from pydantic import BaseModel
from typing import Optional


class UserProfileResponse(BaseModel):
    user_id: str
    has_resume: bool
    resume_text_length: Optional[int] = None


class UserResumeResponse(BaseModel):
    user_id: str
    resume_text_length: int
    s3_pdf_key: str
    uploaded_at: str
