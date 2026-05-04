import uuid
import boto3
from datetime import datetime, timezone
from tests.api.conftest import SESSIONS_TABLE, JOBS_TABLE, USER_ID


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
