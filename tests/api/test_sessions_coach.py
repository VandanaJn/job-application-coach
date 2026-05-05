import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tests.api.conftest import SESSIONS_TABLE, JOBS_TABLE, USERS_TABLE, USER_ID

QUESTION = {"question": "Tell me about leading a project.", "category": "behavioral"}


def _seed_session_with_questions(dynamodb) -> str:
    job_id = str(uuid.uuid4())
    dynamodb.Table(JOBS_TABLE).put_item(Item={
        "user_id": USER_ID, "job_id": job_id,
        "job_title": "Engineer", "company": "Acme",
        "job_description": "Build things.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    session_id = str(uuid.uuid4())
    dynamodb.Table(SESSIONS_TABLE).put_item(Item={
        "user_id": USER_ID,
        "session_id": session_id,
        "job_id": job_id,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "questions": [QUESTION],
    })
    return session_id


def _agentcore_response(text: str = "Can you add the outcome?", is_complete: bool = False):
    body = json.dumps({"response": text, "is_complete": is_complete}).encode()
    streaming_body = MagicMock()
    streaming_body.read.return_value = body
    mock_client = MagicMock()
    mock_client.invoke_agent_runtime.return_value = {"response": streaming_body}
    return mock_client


def test_coach_returns_200_on_first_turn(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)

    with patch("api.routes.sessions.boto3.client", return_value=_agentcore_response()):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            response = client.post(
                f"/sessions/{session_id}/coach",
                json={"question_index": 0, "user_message": "I led a team of three."},
            )
    assert response.status_code == 200


def test_coach_returns_coaching_response(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)

    with patch("api.routes.sessions.boto3.client", return_value=_agentcore_response("Great start! What was the outcome?")):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            data = client.post(
                f"/sessions/{session_id}/coach",
                json={"question_index": 0, "user_message": "I led a team."},
            ).json()

    assert data["coaching_response"] == "Great start! What was the outcome?"
    assert data["question_index"] == 0
    assert data["is_complete"] is False


def test_coach_generates_runtime_session_id_on_first_turn(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)

    with patch("api.routes.sessions.boto3.client", return_value=_agentcore_response()):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            data = client.post(
                f"/sessions/{session_id}/coach",
                json={"question_index": 0, "user_message": "I led a team."},
            ).json()

    assert "runtime_session_id" in data
    assert len(data["runtime_session_id"]) > 0


def test_coach_reuses_runtime_session_id_on_subsequent_turns(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)
    existing_session_id = "existing-runtime-session-abc"

    with patch("api.routes.sessions.boto3.client", return_value=_agentcore_response()):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            data = client.post(
                f"/sessions/{session_id}/coach",
                json={
                    "question_index": 0,
                    "user_message": "We reduced latency by 40%.",
                    "runtime_session_id": existing_session_id,
                },
            ).json()

    assert data["runtime_session_id"] == existing_session_id


def test_coach_passes_question_on_first_turn(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)
    mock_client = _agentcore_response()

    with patch("api.routes.sessions.boto3.client", return_value=mock_client):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            client.post(
                f"/sessions/{session_id}/coach",
                json={"question_index": 0, "user_message": "I led a team."},
            )

    call_kwargs = mock_client.invoke_agent_runtime.call_args[1]
    payload = json.loads(call_kwargs["payload"])
    assert payload["question"] == QUESTION["question"]


def test_coach_omits_question_on_subsequent_turns(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)
    mock_client = _agentcore_response()

    with patch("api.routes.sessions.boto3.client", return_value=mock_client):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            client.post(
                f"/sessions/{session_id}/coach",
                json={
                    "question_index": 0,
                    "user_message": "We cut latency by 40%.",
                    "runtime_session_id": "existing-session",
                },
            )

    call_kwargs = mock_client.invoke_agent_runtime.call_args[1]
    payload = json.loads(call_kwargs["payload"])
    assert "question" not in payload


def test_coach_returns_404_for_unknown_session(client, aws_env):
    with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
        response = client.post(
            "/sessions/nonexistent/coach",
            json={"question_index": 0, "user_message": "answer"},
        )
    assert response.status_code == 404


def test_coach_returns_400_for_invalid_question_index(client, aws_env):
    dynamodb, _ = aws_env
    session_id = _seed_session_with_questions(dynamodb)

    with patch("api.routes.sessions.boto3.client", return_value=_agentcore_response()):
        with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
            response = client.post(
                f"/sessions/{session_id}/coach",
                json={"question_index": 99, "user_message": "answer"},
            )
    assert response.status_code == 400


def test_coach_returns_400_when_session_has_no_questions(client, aws_env):
    dynamodb, _ = aws_env
    session_id = str(uuid.uuid4())
    dynamodb.Table(SESSIONS_TABLE).put_item(Item={
        "user_id": USER_ID,
        "session_id": session_id,
        "job_id": "some-job",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    with patch.dict("os.environ", {"ANSWER_COACH_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:123:runtime/abc"}):
        response = client.post(
            f"/sessions/{session_id}/coach",
            json={"question_index": 0, "user_message": "answer"},
        )
    assert response.status_code == 400
