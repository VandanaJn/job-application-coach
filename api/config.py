import os


class Config:
    dynamodb_table_name: str = os.environ.get("DYNAMODB_TABLE_NAME", "")
    dynamodb_users_table: str = os.environ.get("DYNAMODB_USERS_TABLE", "")
    dynamodb_jobs_table: str = os.environ.get("DYNAMODB_JOBS_TABLE", "")
    s3_bucket_name: str = os.environ.get("S3_BUCKET_NAME", "")
    aws_region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    environment: str = os.environ.get("ENVIRONMENT", "dev")
    user_id: str = "default"


config = Config()
