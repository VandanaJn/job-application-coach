import os
import importlib.util
import boto3
import pytest
from unittest.mock import MagicMock, patch
from moto import mock_aws
from pathlib import Path

from graph.state import InterviewQuestion

_HANDLER_PATH = Path(__file__).parents[2] / "lambda" / "runner" / "handler.py"

SESSIONS_TABLE = "test-sessions"
REGION = "us-east-1"
USER_ID = "default"
SESSION_ID = "sess-abc"

SAMPLE_EVENT = {
    "session_id": SESSION_ID,
    "user_id": USER_ID,
    "job_id": "job-1",
    "resume_text": "Software engineer with 5 years Python experience.",
    "job_description": "Senior Python engineer to build scalable APIs.",
    "num_questions": 3,
}

SAMPLE_QUESTIONS = [
    InterviewQuestion(question=f"Q{i}?", category="technical") for i in range(3)
]


def _load_handler():
    spec = importlib.util.spec_from_file_location("runner_handler", _HANDLER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_graph(questions=SAMPLE_QUESTIONS, input_tokens=100, output_tokens=50):
    mock_compiled = MagicMock()
    mock_compiled.invoke.return_value = {
        "questions": questions,
        "status": "completed",
        "error": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    return MagicMock(return_value=mock_compiled)


@pytest.fixture()
def aws_env():
    os.environ.update({
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": REGION,
        "DYNAMODB_TABLE_NAME": SESSIONS_TABLE,
        "ENVIRONMENT": "test",
    })
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=SESSIONS_TABLE,
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "session_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "session_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.put_item(Item={
            "user_id": USER_ID,
            "session_id": SESSION_ID,
            "job_id": "job-1",
            "status": "pending",
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        yield dynamodb


def test_handler_returns_200(aws_env):
    mod = _load_handler()
    with patch.object(mod, "build_graph", _mock_graph()):
        result = mod.handler(SAMPLE_EVENT, {})
    assert result["statusCode"] == 200


def test_handler_writes_completed_status(aws_env):
    mod = _load_handler()
    with patch.object(mod, "build_graph", _mock_graph()):
        mod.handler(SAMPLE_EVENT, {})

    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    assert item["status"] == "completed"


def test_handler_writes_questions_to_dynamo(aws_env):
    mod = _load_handler()
    with patch.object(mod, "build_graph", _mock_graph()):
        mod.handler(SAMPLE_EVENT, {})

    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    assert "questions" in item
    assert len(item["questions"]) == 3


def test_handler_questions_have_correct_shape(aws_env):
    mod = _load_handler()
    with patch.object(mod, "build_graph", _mock_graph()):
        mod.handler(SAMPLE_EVENT, {})

    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    q = item["questions"][0]
    assert "question" in q
    assert "category" in q


def test_handler_passes_correct_state_to_graph(aws_env):
    mod = _load_handler()
    mock_build = _mock_graph()
    with patch.object(mod, "build_graph", mock_build):
        mod.handler(SAMPLE_EVENT, {})

    invoked_state = mock_build.return_value.invoke.call_args[0][0]
    assert invoked_state["session_id"] == SESSION_ID
    assert invoked_state["resume_text"] == SAMPLE_EVENT["resume_text"]
    assert invoked_state["job_description"] == SAMPLE_EVENT["job_description"]
    assert invoked_state["num_questions"] == 3


def test_handler_writes_error_status_on_graph_failure(aws_env):
    mod = _load_handler()
    mock_build = MagicMock(side_effect=Exception("Bedrock timeout"))
    with patch.object(mod, "build_graph", mock_build):
        result = mod.handler(SAMPLE_EVENT, {})

    assert result["statusCode"] == 200
    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    assert item["status"] == "error"
    assert "Bedrock timeout" in item["error"]


def test_handler_writes_token_usage_to_dynamo(aws_env):
    mod = _load_handler()
    with patch.object(mod, "build_graph", _mock_graph(input_tokens=120, output_tokens=80)):
        mod.handler(SAMPLE_EVENT, {})

    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    assert int(item["usage_input_tokens"]) == 120
    assert int(item["usage_output_tokens"]) == 80
    assert int(item["usage_total_tokens"]) == 200


def test_handler_skips_usage_when_missing_from_state(aws_env):
    mod = _load_handler()
    mock_compiled = MagicMock()
    mock_compiled.invoke.return_value = {
        "questions": SAMPLE_QUESTIONS,
        "status": "completed",
        "error": None,
    }
    with patch.object(mod, "build_graph", MagicMock(return_value=mock_compiled)):
        mod.handler(SAMPLE_EVENT, {})

    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    assert "usage_total_tokens" not in item


def test_handler_writes_error_when_graph_returns_error_state(aws_env):
    mod = _load_handler()
    mock_compiled = MagicMock()
    mock_compiled.invoke.return_value = {
        "questions": None,
        "status": "error",
        "error": "LLM returned invalid JSON",
    }
    mock_build = MagicMock(return_value=mock_compiled)
    with patch.object(mod, "build_graph", mock_build):
        mod.handler(SAMPLE_EVENT, {})

    table = aws_env.Table(SESSIONS_TABLE)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": SESSION_ID})["Item"]
    assert item["status"] == "error"
    assert "LLM returned invalid JSON" in item["error"]
