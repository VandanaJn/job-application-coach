from unittest.mock import patch
from tests.api.conftest import JOBS_TABLE, USER_ID

PARSED_JOB = {
    "job_title": "Senior Engineer",
    "company": "Acme Corp",
    "job_description": "Build great things at scale.",
}


def test_create_job_with_text_returns_200(client):
    response = client.post("/jobs", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build things.",
    })
    assert response.status_code == 200


def test_create_job_returns_fields(client):
    response = client.post("/jobs", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build things.",
    })
    data = response.json()
    assert data["job_title"] == "Engineer"
    assert data["company"] == "Acme"
    assert data["job_description"] == "Build things."
    assert "job_id" in data
    assert "created_at" in data


def test_create_job_stores_to_dynamodb(client, aws_env):
    dynamodb, _ = aws_env
    response = client.post("/jobs", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build things.",
    })
    job_id = response.json()["job_id"]

    item = dynamodb.Table(JOBS_TABLE).get_item(
        Key={"user_id": USER_ID, "job_id": job_id}
    )["Item"]
    assert item["job_title"] == "Engineer"
    assert item["job_description"] == "Build things."


def test_create_job_with_url_parses_and_stores(client, aws_env):
    dynamodb, _ = aws_env
    with patch("api.routes.jobs.fetch_job_from_url", return_value=PARSED_JOB):
        response = client.post("/jobs", json={"url": "https://example.com/jobs/123"})

    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] == "Senior Engineer"
    assert data["company"] == "Acme Corp"


def test_create_job_url_failure_returns_422(client):
    with patch("api.routes.jobs.fetch_job_from_url", side_effect=ValueError("blocked")):
        response = client.post("/jobs", json={"url": "https://linkedin.com/jobs/123"})
    assert response.status_code == 422


def test_create_job_requires_url_or_description(client):
    response = client.post("/jobs", json={"job_title": "Engineer"})
    assert response.status_code == 422


def test_list_jobs_empty(client):
    response = client.get("/jobs")
    assert response.status_code == 200
    assert response.json()["jobs"] == []


def test_list_jobs_returns_all(client):
    client.post("/jobs", json={"job_description": "Job one."})
    client.post("/jobs", json={"job_description": "Job two."})

    response = client.get("/jobs")
    assert response.status_code == 200
    assert len(response.json()["jobs"]) == 2


def test_get_job_returns_job(client):
    job_id = client.post("/jobs", json={
        "job_title": "Engineer",
        "company": "Acme",
        "job_description": "Build things.",
    }).json()["job_id"]

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert response.json()["job_title"] == "Engineer"


def test_get_job_returns_404_for_unknown(client):
    response = client.get("/jobs/nonexistent")
    assert response.status_code == 404
