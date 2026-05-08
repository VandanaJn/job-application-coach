import json
import uuid
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, HTTPException, Depends

from api.config import config
from api.dependencies import current_user_id
from models.session import SessionCreate, SessionResponse, SessionListResponse, SessionStatus, SessionStatusResponse, QuestionItem
from models.coaching import CoachRequest, CoachResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Boto resources/clients are created once per Lambda container and reused
# across requests. boto3 connection pools are tied to the Client object,
# so re-creating them per request defeats the warm-start benefit.
_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
_sessions_table = _dynamodb.Table(config.dynamodb_table_name)
_jobs_table = _dynamodb.Table(config.dynamodb_jobs_table)
_users_table = _dynamodb.Table(config.dynamodb_users_table)
_lambda = boto3.client("lambda", region_name=config.aws_region)
_agentcore = boto3.client("bedrock-agentcore", region_name=config.aws_region)


@router.post("", response_model=SessionResponse)
def create_session(body: SessionCreate, user_id: str = Depends(current_user_id)):
    result = _jobs_table.get_item(Key={"user_id": user_id, "job_id": body.job_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Job not found")

    session_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    _sessions_table.put_item(Item={
        "user_id": user_id,
        "session_id": session_id,
        "job_id": body.job_id,
        "status": SessionStatus.PENDING.value,
        "created_at": created_at,
    })

    return SessionResponse(
        session_id=session_id,
        job_id=body.job_id,
        status=SessionStatus.PENDING,
        created_at=created_at,
    )


@router.get("", response_model=SessionListResponse)
def list_sessions(user_id: str = Depends(current_user_id)):
    result = _sessions_table.query(
        KeyConditionExpression=Key("user_id").eq(user_id)
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
def get_session(session_id: str, user_id: str = Depends(current_user_id)):
    result = _sessions_table.get_item(Key={"user_id": user_id, "session_id": session_id})
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
def run_session(session_id: str, user_id: str = Depends(current_user_id)):
    session_result = _sessions_table.get_item(Key={"user_id": user_id, "session_id": session_id})
    if "Item" not in session_result:
        raise HTTPException(status_code=404, detail="Session not found")
    session = session_result["Item"]

    user_result = _users_table.get_item(Key={"user_id": user_id})
    user = user_result.get("Item", {})
    resume_text = user.get("resume_text")
    if not resume_text:
        raise HTTPException(status_code=400, detail="No resume on file. Upload a resume first.")

    job_result = _jobs_table.get_item(Key={"user_id": user_id, "job_id": session["job_id"]})
    job = job_result.get("Item", {})

    # Conditional update: only flip pending → running. If the row is already
    # running/completed/error, the second click is a no-op (avoids racing
    # runner Lambdas on the same session).
    try:
        _sessions_table.update_item(
            Key={"user_id": user_id, "session_id": session_id},
            UpdateExpression="SET #st = :running",
            ConditionExpression="#st = :pending",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":running": SessionStatus.RUNNING.value,
                ":pending": SessionStatus.PENDING.value,
            },
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=409,
                detail=f"Session is not in 'pending' state (current: {session['status']}); cannot run.",
            )
        raise

    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "job_id": session["job_id"],
        "resume_text": resume_text,
        "job_description": job.get("job_description", ""),
        "num_questions": 5,
    }
    _lambda.invoke(
        FunctionName=config.runner_function_name,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )

    return SessionResponse(
        session_id=session_id,
        job_id=session["job_id"],
        status=SessionStatus.RUNNING,
        created_at=session["created_at"],
    )


@router.post("/{session_id}/coach", response_model=CoachResponse)
def coach_answer(
    session_id: str,
    body: CoachRequest,
    user_id: str = Depends(current_user_id),
):
    result = _sessions_table.get_item(Key={"user_id": user_id, "session_id": session_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Session not found")

    session = result["Item"]
    questions = session.get("questions")
    if not questions:
        raise HTTPException(status_code=400, detail="Session has no questions yet. Run the session first.")

    if body.question_index >= len(questions):
        raise HTTPException(status_code=400, detail=f"question_index {body.question_index} out of range.")

    is_first_turn = body.runtime_session_id is None
    runtime_session_id = body.runtime_session_id or str(uuid.uuid4())

    payload: dict = {"prompt": body.user_message, "user_id": user_id}
    if is_first_turn:
        payload["question"] = questions[body.question_index]["question"]

    raw = _agentcore.invoke_agent_runtime(
        agentRuntimeArn=config.answer_coach_runtime_arn,
        qualifier="DEFAULT",
        runtimeSessionId=runtime_session_id,
        payload=json.dumps(payload).encode(),
    )
    agent_result = json.loads(raw["response"].read())

    return CoachResponse(
        question_index=body.question_index,
        coaching_response=agent_result["response"],
        runtime_session_id=runtime_session_id,
        is_complete=agent_result.get("is_complete", False),
    )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def get_session_status(session_id: str, user_id: str = Depends(current_user_id)):
    result = _sessions_table.get_item(Key={"user_id": user_id, "session_id": session_id})
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
