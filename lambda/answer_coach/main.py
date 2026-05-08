import logging
import os
import boto3
from langchain_core.messages import HumanMessage, AIMessage
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agents.answer_coach import build_answer_coach_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = BedrockAgentCoreApp()

DYNAMODB_MEMORY_TABLE = os.environ.get("DYNAMODB_MEMORY_TABLE", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Per-session in-memory state.
# AgentCore pins each runtimeSessionId to a single microVM, so this is safe.
_conversation_history: list = []
_agent = None


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
    global _conversation_history, _agent

    user_message = payload.get("prompt", "")
    question = payload.get("question")
    user_id = payload.get("user_id", "default")

    if _agent is None:
        user_memory = _load_user_memory(user_id)
        _agent = build_answer_coach_agent(user_memory=user_memory)

    # First turn: frame the user message as question + answer
    if question and not _conversation_history:
        user_message = f"Question: {question}\n\nMy answer: {user_message}"

    _conversation_history.append(HumanMessage(content=user_message))

    result = _agent(_conversation_history)
    coaching = result.coaching

    logger.info(
        "answer_coach turn user_id=%s turn=%d input_tokens=%d output_tokens=%d total_tokens=%d is_complete=%s",
        user_id,
        len(_conversation_history) // 2 + 1,
        result.input_tokens,
        result.output_tokens,
        result.total_tokens,
        coaching.is_complete,
    )

    _conversation_history.append(AIMessage(content=coaching.response))

    return {"response": coaching.response, "is_complete": coaching.is_complete}


app.run()
