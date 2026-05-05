import os
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

SYSTEM_PROMPT = (
    "You are an expert interview coach helping candidates craft strong answers using the STAR "
    "method (Situation, Task, Action, Result). "
    "When a candidate answers an interview question, evaluate their response and provide "
    "specific, constructive coaching. "
    "Ask follow-up questions to draw out missing STAR elements. "
    "When the answer is complete and well-structured, set is_complete to true. "
    "Keep your responses concise and encouraging."
)


class CoachingResponse(BaseModel):
    response: str
    is_complete: bool


def create_agent(model, tools, system_prompt):
    """
    Creates an answer coach agent callable.
    tools is unused but kept for interface consistency across all agents.
    """
    structured_llm = model.with_structured_output(CoachingResponse)

    def agent(messages: list[BaseMessage]) -> CoachingResponse:
        return structured_llm.invoke([SystemMessage(content=system_prompt)] + messages)

    return agent


def build_answer_coach_agent(user_memory: str = ""):
    """Convenience factory used by the AgentCore entrypoint."""
    model = ChatBedrockConverse(model=BEDROCK_MODEL_ID)
    system_prompt = SYSTEM_PROMPT
    if user_memory:
        system_prompt += f"\n\nUser coaching notes: {user_memory}"
    return create_agent(model, [], system_prompt)
