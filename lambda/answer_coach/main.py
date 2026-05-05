import os
import boto3
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
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
_system_prompt: str = ""


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


@app.entrypoint
def invoke(payload, context):
    global _conversation_history, _system_prompt

    user_message = payload.get("prompt", "")
    question = payload.get("question")
    user_id = payload.get("user_id", "default")

    if not _system_prompt:
        user_memory = _load_user_memory(user_id)
        _system_prompt = SYSTEM_PROMPT
        if user_memory:
            _system_prompt += f"\n\nUser coaching notes: {user_memory}"

    # First turn: frame the user message as question + answer
    if question and not _conversation_history:
        user_message = f"Question: {question}\n\nMy answer: {user_message}"

    _conversation_history.append(HumanMessage(content=user_message))

    model = ChatBedrockConverse(model=BEDROCK_MODEL_ID)
    structured_llm = model.with_structured_output(CoachingResponse)
    result = structured_llm.invoke(
        [SystemMessage(content=_system_prompt)] + _conversation_history
    )

    _conversation_history.append(AIMessage(content=result.response))

    return {"response": result.response, "is_complete": result.is_complete}


app.run()
