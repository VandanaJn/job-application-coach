import boto3
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from api.config import config
from api.dependencies import current_user_id
from models.user import UserProfileResponse, UserResumeResponse
from parsers.pdf import extract_text

router = APIRouter(prefix="/user", tags=["user"])


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_users_table)


def _s3():
    return boto3.client("s3", region_name=config.aws_region)


@router.get("", response_model=UserProfileResponse)
def get_user(user_id: str = Depends(current_user_id)):
    result = _table().get_item(Key={"user_id": user_id})
    item = result.get("Item")
    if not item:
        return UserProfileResponse(user_id=user_id, has_resume=False)
    return UserProfileResponse(
        user_id=user_id,
        has_resume=True,
        resume_text_length=len(item.get("resume_text", "")),
    )


@router.post("/resume", response_model=UserResumeResponse)
def upload_resume(
    resume: UploadFile = File(...),
    user_id: str = Depends(current_user_id),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = resume.file.read()
    try:
        text = extract_text(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    s3_key = f"{user_id}/resume.pdf"
    _s3().put_object(Bucket=config.s3_bucket_name, Key=s3_key, Body=pdf_bytes)

    uploaded_at = datetime.now(timezone.utc).isoformat()
    _table().put_item(Item={
        "user_id": user_id,
        "resume_text": text,
        "s3_pdf_key": s3_key,
        "uploaded_at": uploaded_at,
    })

    return UserResumeResponse(
        user_id=user_id,
        resume_text_length=len(text),
        s3_pdf_key=s3_key,
        uploaded_at=uploaded_at,
    )
