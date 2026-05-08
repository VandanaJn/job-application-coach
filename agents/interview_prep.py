import os
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse
from pydantic import BaseModel
from typing import List

from graph.state import InterviewQuestion

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

SYSTEM_PROMPT = (
    "You are an expert interviewer helping candidates prepare for job interviews. "
    "Given a candidate's resume and a job description, generate targeted interview questions "
    "that assess the candidate's fit for the role. "
    "Create a mix of behavioral, technical, and situational questions. "
    "Focus on areas where the resume and job requirements overlap."
)


class InterviewQuestions(BaseModel):
    questions: List[InterviewQuestion]


@dataclass
class InterviewPrepResult:
    questions: List[InterviewQuestion]
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _sum_usage(messages: list) -> tuple[int, int]:
    """Sum input/output tokens across all AIMessages in an agent run."""
    total_in = 0
    total_out = 0
    for m in messages or []:
        meta = getattr(m, "usage_metadata", None) or {}
        total_in += meta.get("input_tokens", 0) or 0
        total_out += meta.get("output_tokens", 0) or 0
    return total_in, total_out


def build_interview_prep_agent(num_questions: int = 5):
    """Convenience factory used by the LangGraph node."""
    model = ChatBedrockConverse(model=BEDROCK_MODEL_ID)
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(InterviewQuestions),
    )

    def run(resume_text: str, job_description: str) -> InterviewPrepResult:
        prompt = (
            f"Generate exactly {num_questions} interview questions for this candidate.\n\n"
            f"RESUME:\n{resume_text}\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"Return exactly {num_questions} questions covering behavioral, technical, "
            f"and situational categories as appropriate."
        )
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        structured: InterviewQuestions = result["structured_response"]
        input_tokens, output_tokens = _sum_usage(result.get("messages", []))
        return InterviewPrepResult(
            questions=structured.questions,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    return run
