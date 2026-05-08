import os
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage
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


def build_answer_coach_agent(user_memory: str = ""):
    """Convenience factory used by the AgentCore entrypoint."""
    model = ChatBedrockConverse(model=BEDROCK_MODEL_ID)
    system_prompt = SYSTEM_PROMPT
    if user_memory:
        system_prompt += f"\n\nUser coaching notes: {user_memory}"

    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=system_prompt,
        response_format=ToolStrategy(CoachingResponse),
        middleware=[
            SummarizationMiddleware(
                model=model,
                trigger=("tokens", 8000),
                keep=("messages", 10),
            ),
        ],
    )

    def run(messages: list[BaseMessage]) -> CoachingResponse:
        result = agent.invoke({"messages": messages})
        return result["structured_response"]

    return run
