import uuid
import boto3
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException

from api.config import config
from models.session import SessionResponse, ResumeUploadResponse
from parsers.pdf import extract_text

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_table_name)


def _s3():
    return boto3.client("s3", region_name=config.aws_region)


@router.post("", response_model=SessionResponse)
def create_session():
    session_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    _table().put_item(Item={
        "user_id": config.user_id,
        "session_id": session_id,
        "status": "pending",
        "created_at": created_at,
    })

    return SessionResponse(session_id=session_id, status="pending", created_at=created_at)


@router.post("/{session_id}/resume", response_model=ResumeUploadResponse)
def upload_resume(session_id: str, resume: UploadFile = File(...)):
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    table = _table()
    result = table.get_item(Key={"user_id": config.user_id, "session_id": session_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Session not found")

    pdf_bytes = resume.file.read()

    try:
        text = extract_text(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    s3_key = f"{config.user_id}/{session_id}/resume.pdf"
    _s3().put_object(Bucket=config.s3_bucket_name, Key=s3_key, Body=pdf_bytes)

    table.update_item(
        Key={"user_id": config.user_id, "session_id": session_id},
        UpdateExpression="SET resume_text = :t, s3_pdf_key = :k",
        ExpressionAttributeValues={":t": text, ":k": s3_key},
    )

    return ResumeUploadResponse(session_id=session_id, resume_text_length=len(text))
