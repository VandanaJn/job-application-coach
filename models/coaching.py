from typing import Optional
from pydantic import BaseModel


class CoachRequest(BaseModel):
    question_index: int
    user_message: str
    runtime_session_id: Optional[str] = None


class CoachResponse(BaseModel):
    question_index: int
    coaching_response: str
    runtime_session_id: str
    is_complete: bool
