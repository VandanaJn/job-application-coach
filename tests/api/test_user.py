import io
from unittest.mock import patch
from tests.api.conftest import USERS_TABLE, BUCKET_NAME, USER_ID


def test_get_user_no_resume(client):
    response = client.get("/user")
    assert response.status_code == 200
    data = response.json()
    assert data["has_resume"] is False
    assert data["user_id"] == USER_ID


def test_upload_resume_returns_ok(client):
    with patch("api.routes.user.extract_text", return_value="Resume text here"):
        response = client.post(
            "/user/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["resume_text_length"] == len("Resume text here")
    assert data["user_id"] == USER_ID


def test_upload_resume_stores_to_s3(client, aws_env):
    _, s3 = aws_env
    with patch("api.routes.user.extract_text", return_value="Resume text"):
        client.post(
            "/user/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    objects = s3.list_objects_v2(Bucket=BUCKET_NAME)
    assert objects["KeyCount"] == 1
    assert objects["Contents"][0]["Key"] == f"{USER_ID}/resume.pdf"


def test_upload_resume_stores_text_to_dynamodb(client, aws_env):
    dynamodb, _ = aws_env
    with patch("api.routes.user.extract_text", return_value="Software engineer 5 years"):
        client.post(
            "/user/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    item = dynamodb.Table(USERS_TABLE).get_item(Key={"user_id": USER_ID})["Item"]
    assert item["resume_text"] == "Software engineer 5 years"
    assert "uploaded_at" in item


def test_get_user_after_upload_shows_resume(client, aws_env):
    with patch("api.routes.user.extract_text", return_value="My resume"):
        client.post(
            "/user/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    response = client.get("/user")
    assert response.json()["has_resume"] is True
    assert response.json()["resume_text_length"] == len("My resume")


def test_upload_resume_rejects_non_pdf(client):
    response = client.post(
        "/user/resume",
        files={"resume": ("resume.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_resume_returns_400_when_pdf_has_no_text(client):
    with patch("api.routes.user.extract_text", side_effect=ValueError("no text extracted")):
        response = client.post(
            "/user/resume",
            files={"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert response.status_code == 400


def test_upload_resume_overwrites_previous(client, aws_env):
    dynamodb, _ = aws_env
    with patch("api.routes.user.extract_text", return_value="Old resume"):
        client.post("/user/resume",
            files={"resume": ("r.pdf", io.BytesIO(b"%PDF"), "application/pdf")})
    with patch("api.routes.user.extract_text", return_value="New resume"):
        client.post("/user/resume",
            files={"resume": ("r.pdf", io.BytesIO(b"%PDF"), "application/pdf")})

    item = dynamodb.Table(USERS_TABLE).get_item(Key={"user_id": USER_ID})["Item"]
    assert item["resume_text"] == "New resume"
