import aws_cdk as cdk
import pytest
from aws_cdk import assertions
from stacks.job_coach_stack import JobCoachStack


@pytest.fixture(scope="module")
def template():
    app = cdk.App()
    stack = JobCoachStack(app, "TestStack", env_name="dev")
    return assertions.Template.from_stack(stack)


# S3
def test_pdf_bucket_exists(template):
    template.resource_count_is("AWS::S3::Bucket", 1)


def test_pdf_bucket_has_cors(template):
    template.has_resource_properties("AWS::S3::Bucket", {
        "CorsConfiguration": {
            "CorsRules": assertions.Match.array_with([
                assertions.Match.object_like({
                    "AllowedMethods": ["GET", "PUT"],
                    "AllowedOrigins": ["*"],
                })
            ])
        }
    })


# DynamoDB
def test_five_dynamodb_tables(template):
    template.resource_count_is("AWS::DynamoDB::Table", 5)


def test_users_table_keys(template):
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    })


def test_jobs_table_keys(template):
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": assertions.Match.array_with([
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "job_id", "KeyType": "RANGE"},
        ]),
        "BillingMode": "PAY_PER_REQUEST",
    })


def test_sessions_table_keys(template):
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": assertions.Match.array_with([
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "session_id", "KeyType": "RANGE"},
        ]),
        "BillingMode": "PAY_PER_REQUEST",
    })


def test_checkpoints_table_keys(template):
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": assertions.Match.array_with([
            {"AttributeName": "thread_id", "KeyType": "HASH"},
            {"AttributeName": "checkpoint_id", "KeyType": "RANGE"},
        ]),
        "BillingMode": "PAY_PER_REQUEST",
    })


def test_memory_table_keys(template):
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": assertions.Match.array_with([
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "memory_type", "KeyType": "RANGE"},
        ]),
        "BillingMode": "PAY_PER_REQUEST",
    })


# Lambda
def test_api_lambda_config(template):
    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.12",
        "Timeout": 30,
        "MemorySize": 512,
        "Handler": "handler.handler",
    })


def test_runner_lambda_config(template):
    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.12",
        "Timeout": 900,
        "MemorySize": 1024,
        "Handler": "handler.handler",
    })


def test_runner_has_bedrock_policy(template):
    template.has_resource_properties("AWS::IAM::Policy", {
        "PolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": assertions.Match.array_with([
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                    ]),
                    "Effect": "Allow",
                })
            ])
        }
    })


# API Gateway
def test_api_gateway_exists(template):
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_api_gateway_name(template):
    template.has_resource_properties("AWS::ApiGateway::RestApi", {
        "Name": "job-coach-dev-api",
    })


# CFN Outputs
def test_stack_exports_api_url(template):
    template.has_output("ApiUrl", {})


def test_stack_exports_answer_coach_runtime_arn(template):
    template.has_output("AnswerCoachRuntimeArn", {})


def test_stack_exports_pdf_bucket_name(template):
    template.has_output("PdfBucketName", {})
