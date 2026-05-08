import uuid
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, HTTPException, Depends

from api.config import config
from api.dependencies import current_user_id
from models.job import JobCreate, JobResponse, JobListResponse
from parsers.job import fetch_job_from_url

router = APIRouter(prefix="/jobs", tags=["jobs"])

_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
_jobs_table = _dynamodb.Table(config.dynamodb_jobs_table)


@router.post("", response_model=JobResponse)
def create_job(body: JobCreate, user_id: str = Depends(current_user_id)):
    if body.url:
        try:
            parsed = fetch_job_from_url(body.url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        job_title = parsed.get("job_title") or body.job_title
        company = parsed.get("company") or body.company
        job_description = parsed["job_description"]
    else:
        job_title = body.job_title
        company = body.company
        job_description = body.job_description

    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    _jobs_table.put_item(Item={
        "user_id": user_id,
        "job_id": job_id,
        "job_title": job_title or "",
        "company": company or "",
        "job_description": job_description,
        "created_at": created_at,
    })

    return JobResponse(
        job_id=job_id,
        job_title=job_title,
        company=company,
        job_description=job_description,
        created_at=created_at,
    )


@router.get("", response_model=JobListResponse)
def list_jobs(user_id: str = Depends(current_user_id)):
    result = _jobs_table.query(
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    jobs = [
        JobResponse(
            job_id=item["job_id"],
            job_title=item.get("job_title"),
            company=item.get("company"),
            job_description=item["job_description"],
            created_at=item["created_at"],
        )
        for item in result.get("Items", [])
    ]
    return JobListResponse(jobs=jobs)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user_id: str = Depends(current_user_id)):
    result = _jobs_table.get_item(Key={"user_id": user_id, "job_id": job_id})
    if "Item" not in result:
        raise HTTPException(status_code=404, detail="Job not found")
    item = result["Item"]
    return JobResponse(
        job_id=item["job_id"],
        job_title=item.get("job_title"),
        company=item.get("company"),
        job_description=item["job_description"],
        created_at=item["created_at"],
    )
