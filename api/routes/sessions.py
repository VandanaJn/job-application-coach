import json
import uuid
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, HTTPException

from api.config import config
from models.session import SessionCreate, SessionResponse, SessionListResponse, SessionStatusResponse, QuestionItem

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_table_name)


def _jobs_table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_jobs_table)


def _users_table():
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    return dynamodb.Table(config.dynamodb_users_table)


def _lambda_client():
    return boto3.client("lambda", region_name=config.aws_region)


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


@router.post("/{session_id}/run", response_model=SessionResponse)
def run_session(session_id: str):
    session_result = _table().get_item(Key={"user_id": config.user_id, "session_id": session_id})
    if "Item" not in session_result:
        raise HTTPException(status_code=404, detail="Session not found")
    session = session_result["Item"]

    user_result = _users_table().get_item(Key={"user_id": config.user_id})
    user = user_result.get("Item", {})
    resume_text = user.get("resume_text")
    if not resume_text:
        raise HTTPException(status_code=400, detail="No resume on file. Upload a resume first.")

    job_result = _jobs_table().get_item(Key={"user_id": config.user_id, "job_id": session["job_id"]})
    job = job_result.get("Item", {})

    _table().update_item(
        Key={"user_id": config.user_id, "session_id": session_id},
        UpdateExpression="SET #st = :status",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":status": "running"},
    )

    payload = {
        "session_id": session_id,
        "user_id": config.user_id,
        "job_id": session["job_id"],
        "resume_text": resume_text,
        "job_description": job.get("job_description", ""),
        "num_questions": 5,
    }
    _lambda_client().invoke(
        FunctionName=config.runner_function_name,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )

    return SessionResponse(
        session_id=session_id,
        job_id=session["job_id"],
        status="running",
        created_at=session["created_at"],
    )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def get_session_status(session_id: str):
    result = _table().get_item(Key={"user_id": config.user_id, "session_id": session_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Session not found")
    item = result["Item"]

    questions = None
    if item.get("questions"):
        questions = [QuestionItem(**q) for q in item["questions"]]

    return SessionStatusResponse(
        session_id=session_id,
        status=item["status"],
        questions=questions,
        error=item.get("error"),
    )
