from unittest.mock import patch


PARSED_JOB = {
    "job_title": "Senior Software Engineer",
    "company": "Acme Corp",
    "job_description": "We are looking for a senior engineer...",
}


def _create_session(client):
    return client.post("/sessions").json()["session_id"]


def test_post_job_with_text_returns_200(client):
    session_id = _create_session(client)
    response = client.post(f"/sessions/{session_id}/job", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build great things.",
    })
    assert response.status_code == 200


def test_post_job_with_text_returns_fields(client):
    session_id = _create_session(client)
    response = client.post(f"/sessions/{session_id}/job", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build great things.",
    })
    data = response.json()
    assert data["job_title"] == "Engineer"
    assert data["company"] == "Acme"
    assert data["job_description"] == "Build great things."
    assert data["session_id"] == session_id


def test_post_job_with_text_stores_to_dynamodb(client, aws_env):
    from tests.api.conftest import TABLE_NAME, USER_ID
    dynamodb, _ = aws_env
    session_id = _create_session(client)

    client.post(f"/sessions/{session_id}/job", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build great things.",
    })

    table = dynamodb.Table(TABLE_NAME)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": session_id})
    assert item["Item"]["job_title"] == "Engineer"
    assert item["Item"]["company"] == "Acme"
    assert item["Item"]["job_description"] == "Build great things."


def test_post_job_with_url_calls_parser_and_stores(client, aws_env):
    from tests.api.conftest import TABLE_NAME, USER_ID
    dynamodb, _ = aws_env
    session_id = _create_session(client)

    with patch("api.routes.sessions.fetch_job_from_url", return_value=PARSED_JOB):
        response = client.post(f"/sessions/{session_id}/job", json={
            "url": "https://example.com/jobs/123",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] == "Senior Software Engineer"
    assert data["company"] == "Acme Corp"

    table = dynamodb.Table(TABLE_NAME)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": session_id})
    assert item["Item"]["job_description"] == "We are looking for a senior engineer..."


def test_post_job_url_scrape_failure_returns_422(client):
    session_id = _create_session(client)

    with patch("api.routes.sessions.fetch_job_from_url", side_effect=ValueError("blocked")):
        response = client.post(f"/sessions/{session_id}/job", json={
            "url": "https://linkedin.com/jobs/123",
        })

    assert response.status_code == 422


def test_post_job_requires_url_or_description(client):
    session_id = _create_session(client)
    response = client.post(f"/sessions/{session_id}/job", json={
        "job_title": "Engineer",
    })
    assert response.status_code == 422


def test_post_job_session_not_found(client):
    response = client.post("/sessions/nonexistent/job", json={
        "job_description": "Some job.",
    })
    assert response.status_code == 404


def test_get_job_returns_stored_details(client):
    session_id = _create_session(client)
    client.post(f"/sessions/{session_id}/job", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build great things.",
    })

    response = client.get(f"/sessions/{session_id}/job")
    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] == "Engineer"
    assert data["job_description"] == "Build great things."


def test_get_job_returns_404_before_job_is_set(client):
    session_id = _create_session(client)
    response = client.get(f"/sessions/{session_id}/job")
    assert response.status_code == 404


def test_get_job_session_not_found(client):
    response = client.get("/sessions/nonexistent/job")
    assert response.status_code == 404
