import uuid
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, HTTPException

from api.config import config
from models.session import SessionCreate, SessionResponse, SessionListResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_table_name)


def _jobs_table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_jobs_table)


@router.post("", response_model=SessionResponse)
def create_session(body: SessionCreate):
    result = _jobs_table().get_item(Key={"user_id": config.user_id, "job_id": body.job_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Job not found")

    session_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    _table().put_item(Item={
        "user_id": config.user_id,
        "session_id": session_id,
        "job_id": body.job_id,
        "status": "pending",
        "created_at": created_at,
    })

    return SessionResponse(
        session_id=session_id,
        job_id=body.job_id,
        status="pending",
        created_at=created_at,
    )


@router.get("", response_model=SessionListResponse)
def list_sessions():
    result = _table().query(
        KeyConditionExpression=Key("user_id").eq(config.user_id)
    )
    sessions = [
        SessionResponse(
            session_id=item["session_id"],
            job_id=item.get("job_id", ""),
            status=item["status"],
            created_at=item["created_at"],
        )
        for item in result.get("Items", [])
    ]
    return SessionListResponse(sessions=sessions)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    result = _table().get_item(Key={"user_id": config.user_id, "session_id": session_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Session not found")
    item = result["Item"]
    return SessionResponse(
        session_id=item["session_id"],
        job_id=item.get("job_id", ""),
        status=item["status"],
        created_at=item["created_at"],
    )
