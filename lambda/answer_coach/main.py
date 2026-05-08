import os
import boto3
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
DYNAMODB_MEMORY_TABLE = os.environ.get("DYNAMODB_MEMORY_TABLE", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = (
    "You are an expert interview coach helping candidates craft strong answers using the STAR "
    "method (Situation, Task, Action, Result). "
    "When a candidate answers an interview question, evaluate their response and provide "
    "specific, constructive coaching. "
    "Ask follow-up questions to draw out missing STAR elements. "
    "When the answer is complete and well-structured, set is_complete to true. "
    "Keep your responses concise and encouraging."
)

# Per-session in-memory state.
# AgentCore pins each runtimeSessionId to a single microVM, so this is safe.
_conversation_history: list = []
_agent = None


class CoachingResponse(BaseModel):
    response: str
    is_complete: bool


def _load_user_memory(user_id: str) -> str:
    if not DYNAMODB_MEMORY_TABLE:
        return ""
    try:
        ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        result = ddb.Table(DYNAMODB_MEMORY_TABLE).get_item(
            Key={"user_id": user_id, "memory_type": "coaching"}
        )
        return result.get("Item", {}).get("content", "")
    except Exception:
        return ""


def _build_agent(user_id: str):
    user_memory = _load_user_memory(user_id)
    system_prompt = SYSTEM_PROMPT
    if user_memory:
        system_prompt += f"\n\nUser coaching notes: {user_memory}"

    model = ChatBedrockConverse(model=BEDROCK_MODEL_ID)
    return create_agent(
        model=model,
        tools=[],
        system_prompt=system_prompt,
        response_format=ToolStrategy(CoachingResponse),
    )


@app.entrypoint
def invoke(payload, context):
    global _conversation_history, _agent

    user_message = payload.get("prompt", "")
    question = payload.get("question")
    user_id = payload.get("user_id", "default")

    if _agent is None:
        _agent = _build_agent(user_id)

    # First turn: frame the user message as question + answer
    if question and not _conversation_history:
        user_message = f"Question: {question}\n\nMy answer: {user_message}"

    _conversation_history.append(HumanMessage(content=user_message))

    result = _agent.invoke({"messages": _conversation_history})
    coaching: CoachingResponse = result["structured_response"]

    _conversation_history.append(AIMessage(content=coaching.response))

    return {"response": coaching.response, "is_complete": coaching.is_complete}


app.run()
