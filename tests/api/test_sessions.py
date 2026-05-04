import io
import boto3
from unittest.mock import patch
from tests.api.conftest import TABLE_NAME, BUCKET_NAME, USER_ID


def test_create_session_returns_session_id(client):
    response = client.post("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "pending"


def test_create_session_stores_record_in_dynamodb(client, aws_env):
    dynamodb, _ = aws_env
    response = client.post("/sessions")
    session_id = response.json()["session_id"]

    table = dynamodb.Table(TABLE_NAME)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": session_id})
    assert "Item" in item
    assert item["Item"]["status"] == "pending"
    assert "created_at" in item["Item"]


def test_upload_resume_returns_ok(client):
    session_id = client.post("/sessions").json()["session_id"]

    with patch("api.routes.sessions.extract_text", return_value="Extracted resume text"):
        response = client.post(
            f"/sessions/{session_id}/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert response.status_code == 200


def test_upload_resume_stores_pdf_to_s3(client, aws_env):
    dynamodb, s3 = aws_env
    session_id = client.post("/sessions").json()["session_id"]

    with patch("api.routes.sessions.extract_text", return_value="Extracted resume text"):
        client.post(
            f"/sessions/{session_id}/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )

    objects = s3.list_objects_v2(Bucket=BUCKET_NAME)
    assert objects["KeyCount"] == 1


def test_upload_resume_saves_extracted_text_to_dynamodb(client, aws_env):
    dynamodb, _ = aws_env
    session_id = client.post("/sessions").json()["session_id"]

    with patch("api.routes.sessions.extract_text", return_value="Software engineer with 5 years experience"):
        client.post(
            f"/sessions/{session_id}/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )

    table = dynamodb.Table(TABLE_NAME)
    item = table.get_item(Key={"user_id": USER_ID, "session_id": session_id})
    assert item["Item"]["resume_text"] == "Software engineer with 5 years experience"


def test_upload_resume_rejects_non_pdf(client):
    session_id = client.post("/sessions").json()["session_id"]

    response = client.post(
        f"/sessions/{session_id}/resume",
        files={"resume": ("resume.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_resume_returns_404_for_unknown_session(client):
    with patch("api.routes.sessions.extract_text", return_value="some text"):
        response = client.post(
            "/sessions/nonexistent-id/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert response.status_code == 404


def test_upload_resume_returns_400_when_pdf_has_no_text(client):
    session_id = client.post("/sessions").json()["session_id"]

    with patch("api.routes.sessions.extract_text", side_effect=ValueError("no text extracted")):
        response = client.post(
            f"/sessions/{session_id}/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert response.status_code == 400
