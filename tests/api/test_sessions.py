import json
import uuid
import boto3
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from tests.api.conftest import SESSIONS_TABLE, JOBS_TABLE, USERS_TABLE, USER_ID


def _seed_job(dynamodb) -> str:
    job_id = str(uuid.uuid4())
    dynamodb.Table(JOBS_TABLE).put_item(Item={
        "user_id": USER_ID,
        "job_id": job_id,
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build things.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return job_id


def test_create_session_returns_session_id(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    response = client.post("/sessions", json={"job_id": job_id})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "pending"
    assert data["job_id"] == job_id


def test_create_session_stores_record_in_dynamodb(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = client.post("/sessions", json={"job_id": job_id}).json()["session_id"]

    item = dynamodb.Table(SESSIONS_TABLE).get_item(
        Key={"user_id": USER_ID, "session_id": session_id}
    )["Item"]
    assert item["status"] == "pending"
    assert item["job_id"] == job_id
    assert "created_at" in item


def test_create_session_returns_404_for_unknown_job(client):
    response = client.post("/sessions", json={"job_id": "nonexistent"})
    assert response.status_code == 404


def test_list_sessions_returns_all(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    client.post("/sessions", json={"job_id": job_id})
    client.post("/sessions", json={"job_id": job_id})

    response = client.get("/sessions")
    assert response.status_code == 200
    assert len(response.json()["sessions"]) == 2


def test_list_sessions_empty(client):
    response = client.get("/sessions")
    assert response.status_code == 200
    assert response.json()["sessions"] == []


def test_get_session_returns_session(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = client.post("/sessions", json={"job_id": job_id}).json()["session_id"]

    response = client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["session_id"] == session_id
    assert response.json()["job_id"] == job_id


def test_get_session_returns_404_for_unknown(client):
    response = client.get("/sessions/nonexistent")
    assert response.status_code == 404


def _seed_user_with_resume(dynamodb):
    dynamodb.Table(USERS_TABLE).put_item(Item={
        "user_id": USER_ID,
        "resume_text": "Python engineer, 5 years experience.",
    })


def _seed_session(dynamodb, job_id: str) -> str:
    session_id = str(uuid.uuid4())
    dynamodb.Table(SESSIONS_TABLE).put_item(Item={
        "user_id": USER_ID,
        "session_id": session_id,
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return session_id


def test_run_session_returns_200(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    _seed_user_with_resume(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {}
    with patch("api.routes.sessions._lambda", mock_lambda):
        response = client.post(f"/sessions/{session_id}/run")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_run_session_invokes_runner_lambda(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    _seed_user_with_resume(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {}
    with patch("api.routes.sessions._lambda", mock_lambda):
        client.post(f"/sessions/{session_id}/run")

    mock_lambda.invoke.assert_called_once()
    call_kwargs = mock_lambda.invoke.call_args[1]
    assert call_kwargs["InvocationType"] == "Event"
    payload = json.loads(call_kwargs["Payload"])
    assert payload["session_id"] == session_id
    assert payload["resume_text"] == "Python engineer, 5 years experience."
    assert payload["job_description"] == "Build things."


def test_run_session_updates_status_to_running(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    _seed_user_with_resume(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {}
    with patch("api.routes.sessions._lambda", mock_lambda):
        client.post(f"/sessions/{session_id}/run")

    item = dynamodb.Table(SESSIONS_TABLE).get_item(
        Key={"user_id": USER_ID, "session_id": session_id}
    )["Item"]
    assert item["status"] == "running"


def test_run_session_returns_404_for_unknown_session(client):
    response = client.post("/sessions/nonexistent/run")
    assert response.status_code == 404


def test_run_session_returns_404_when_no_resume(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    response = client.post(f"/sessions/{session_id}/run")
    assert response.status_code == 400


def test_run_session_returns_409_when_already_running(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    _seed_user_with_resume(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {}
    with patch("api.routes.sessions._lambda", mock_lambda):
        first = client.post(f"/sessions/{session_id}/run")
        second = client.post(f"/sessions/{session_id}/run")

    assert first.status_code == 200
    assert second.status_code == 409
    # Lambda must only be invoked once — second click should NOT trigger a runner
    mock_lambda.invoke.assert_called_once()


def test_get_status_returns_running(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    response = client.get(f"/sessions/{session_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_get_status_returns_questions_when_completed(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = _seed_session(dynamodb, job_id)
    dynamodb.Table(SESSIONS_TABLE).update_item(
        Key={"user_id": USER_ID, "session_id": session_id},
        UpdateExpression="SET #st = :s, questions = :q",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":s": "completed",
            ":q": [{"question": "Tell me about yourself?", "category": "behavioral"}],
        },
    )

    response = client.get(f"/sessions/{session_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == "Tell me about yourself?"


def test_get_status_returns_404_for_unknown(client):
    response = client.get("/sessions/nonexistent/status")
    assert response.status_code == 404


def test_get_status_returns_usage_when_present(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = _seed_session(dynamodb, job_id)
    dynamodb.Table(SESSIONS_TABLE).update_item(
        Key={"user_id": USER_ID, "session_id": session_id},
        UpdateExpression=(
            "SET #st = :s, usage_input_tokens = :uin, "
            "usage_output_tokens = :uout, usage_total_tokens = :utotal"
        ),
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":s": "completed",
            ":uin": 120,
            ":uout": 80,
            ":utotal": 200,
        },
    )

    response = client.get(f"/sessions/{session_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["usage"] == {"input_tokens": 120, "output_tokens": 80, "total_tokens": 200}


def test_get_status_omits_usage_when_missing(client, aws_env):
    dynamodb, _ = aws_env
    job_id = _seed_job(dynamodb)
    session_id = _seed_session(dynamodb, job_id)

    response = client.get(f"/sessions/{session_id}/status")
    assert response.status_code == 200
    assert response.json().get("usage") is None
