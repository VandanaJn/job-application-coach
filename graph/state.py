from typing import TypedDict, Optional
from pydantic import BaseModel


class InterviewQuestion(BaseModel):
    question: str
    category: str  # behavioral | technical | situational


class GraphState(TypedDict):
    session_id: str
    user_id: str
    job_id: str
    resume_text: str
    job_description: str
    num_questions: int
    questions: Optional[list[InterviewQuestion]]
    status: str
    error: Optional[str]
