import os
from typing import Any

import boto3

from graph.orchestrator import build_graph
from graph.state import GraphState
from models.session import SessionStatus

SESSIONS_TABLE = os.environ.get("DYNAMODB_TABLE_NAME", "")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(SESSIONS_TABLE)


def _write_result(session_id: str, user_id: str, status: str, questions=None, error=None, usage=None):
    update_expr = "SET #st = :status"
    expr_names = {"#st": "status"}
    expr_values: dict[str, Any] = {":status": status}

    if questions is not None:
        update_expr += ", questions = :questions"
        expr_values[":questions"] = [q.model_dump() for q in questions]

    if error is not None:
        update_expr += ", #err = :error"
        expr_names["#err"] = "error"
        expr_values[":error"] = error

    if usage is not None:
        update_expr += ", usage_input_tokens = :uin, usage_output_tokens = :uout, usage_total_tokens = :utotal"
        expr_values[":uin"] = usage["input_tokens"]
        expr_values[":uout"] = usage["output_tokens"]
        expr_values[":utotal"] = usage["input_tokens"] + usage["output_tokens"]

    _table().update_item(
        Key={"user_id": user_id, "session_id": session_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def handler(event, context):
    session_id = event["session_id"]
    user_id = event["user_id"]

    try:
        state: GraphState = {
            "session_id": session_id,
            "user_id": user_id,
            "job_id": event["job_id"],
            "resume_text": event["resume_text"],
            "job_description": event["job_description"],
            "num_questions": event.get("num_questions", 5),
            "questions": None,
            "coaching_sessions": None,
            "status": SessionStatus.RUNNING.value,
            "error": None,
            "input_tokens": None,
            "output_tokens": None,
        }

        result = build_graph().invoke(state)

        if result.get("status") == SessionStatus.ERROR.value:
            _write_result(session_id, user_id, SessionStatus.ERROR.value, error=result.get("error", "Unknown error"))
        else:
            usage = None
            if "input_tokens" in result and "output_tokens" in result:
                usage = {
                    "input_tokens": result["input_tokens"] or 0,
                    "output_tokens": result["output_tokens"] or 0,
                }
            _write_result(
                session_id,
                user_id,
                SessionStatus.COMPLETED.value,
                questions=result["questions"],
                usage=usage,
            )

    except Exception as exc:
        _write_result(session_id, user_id, SessionStatus.ERROR.value, error=str(exc))

    return {"statusCode": 200}
