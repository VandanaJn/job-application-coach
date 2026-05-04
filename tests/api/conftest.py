import os
import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient

TABLE_NAME = "test-sessions"
BUCKET_NAME = "test-pdfs"
USER_ID = "default"
REGION = "us-east-1"


@pytest.fixture()
def aws_env():
    os.environ.update({
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": REGION,
        "DYNAMODB_TABLE_NAME": TABLE_NAME,
        "S3_BUCKET_NAME": BUCKET_NAME,
        "ENVIRONMENT": "test",
    })
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "session_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "session_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=BUCKET_NAME)
        yield dynamodb, s3


@pytest.fixture()
def client(aws_env):
    from api.app import app
    return TestClient(app)
