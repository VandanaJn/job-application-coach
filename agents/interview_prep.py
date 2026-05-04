import os
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import List

from graph.state import InterviewQuestion

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")

SYSTEM_PROMPT = (
    "You are an expert interviewer helping candidates prepare for job interviews. "
    "Given a candidate's resume and a job description, generate targeted interview questions "
    "that assess the candidate's fit for the role. "
    "Create a mix of behavioral, technical, and situational questions. "
    "Focus on areas where the resume and job requirements overlap."
)


class InterviewQuestions(BaseModel):
    questions: List[InterviewQuestion]


def create_agent(model, tools, system_prompt):
    """
    Creates an interview prep agent callable.
    tools is unused but kept for interface consistency across all agents.
    """
    structured_llm = model.with_structured_output(InterviewQuestions)

    def agent(resume_text: str, job_description: str, num_questions: int = 5) -> InterviewQuestions:
        prompt = (
            f"Generate exactly {num_questions} interview questions for this candidate.\n\n"
            f"RESUME:\n{resume_text}\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"Return exactly {num_questions} questions covering behavioral, technical, "
            f"and situational categories as appropriate."
        )
        return structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])

    return agent


def build_interview_prep_agent(num_questions: int = 5):
    """Convenience factory used by the LangGraph node."""
    model = ChatBedrockConverse(model=BEDROCK_MODEL_ID)
    agent = create_agent(model, [], SYSTEM_PROMPT)

    def run(resume_text: str, job_description: str) -> InterviewQuestions:
        return agent(resume_text, job_description, num_questions)

    return run
