from __future__ import annotations

import os
import shutil
import subprocess
import sys
import jsii
from aws_cdk import (
    BundlingOptions,
    Duration,
    ILocalBundling,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct


@jsii.implements(ILocalBundling)
class _ApiLocalBundler:
    """Bundles the API Lambda without Docker — works on Windows and any CI with Python."""

    def __init__(self, project_root: str) -> None:
        self._root = project_root

    def try_bundle(self, output_dir: str, options: BundlingOptions) -> bool:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", os.path.join(self._root, "lambda", "api", "requirements.txt"),
                "-t", output_dir, "--quiet",
            ])
            for pkg in ("api", "models", "parsers"):
                shutil.copytree(
                    os.path.join(self._root, pkg),
                    os.path.join(output_dir, pkg),
                    dirs_exist_ok=True,
                )
            shutil.copy(
                os.path.join(self._root, "lambda", "api", "handler.py"),
                output_dir,
            )
            return True
        except Exception as exc:
            print(f"Local bundling failed, falling back to Docker: {exc}")
            return False


class JobCoachStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        prefix = f"job-coach-{env_name}"
        is_dev = env_name == "dev"
        removal = RemovalPolicy.DESTROY if is_dev else RemovalPolicy.RETAIN

        # S3 — PDF storage
        pdf_bucket = s3.Bucket(
            self,
            "PdfBucket",
            bucket_name=f"{prefix}-pdfs-{self.account}",
            removal_policy=removal,
            auto_delete_objects=is_dev,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                )
            ],
        )

        # DynamoDB — sessions
        sessions_table = dynamodb.Table(
            self,
            "SessionsTable",
            table_name=f"{prefix}-sessions",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="session_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal,
        )

        # DynamoDB — LangGraph checkpoints
        checkpoints_table = dynamodb.Table(
            self,
            "CheckpointsTable",
            table_name=f"{prefix}-checkpoints",
            partition_key=dynamodb.Attribute(
                name="thread_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="checkpoint_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal,
        )

        # DynamoDB — long-term user memory
        memory_table = dynamodb.Table(
            self,
            "MemoryTable",
            table_name=f"{prefix}-memory",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="memory_type", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal,
        )

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        lambda_root = os.path.join(project_root, "lambda")

        # Lambda — Runner (async LangGraph execution)
        runner_fn = lambda_.Function(
            self,
            "RunnerFunction",
            function_name=f"{prefix}-runner",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(os.path.join(lambda_root, "runner")),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "ENVIRONMENT": env_name,
                "DYNAMODB_TABLE_NAME": sessions_table.table_name,
                "DYNAMODB_CHECKPOINTS_TABLE": checkpoints_table.table_name,
                "DYNAMODB_MEMORY_TABLE": memory_table.table_name,
                "S3_BUCKET_NAME": pdf_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-haiku-4-5-20251001-v1:0",
                "BEDROCK_GUARDRAIL_ID": "",
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Lambda — API (FastAPI + Mangum)
        api_fn = lambda_.Function(
            self,
            "ApiFunction",
            function_name=f"{prefix}-api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                project_root,
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    local=_ApiLocalBundler(project_root),
                    command=[
                        "bash", "-c",
                        "pip install -r lambda/api/requirements.txt -t /asset-output --quiet"
                        " && cp -r api models parsers /asset-output"
                        " && cp lambda/api/handler.py /asset-output",
                    ],
                ),
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "ENVIRONMENT": env_name,
                "DYNAMODB_TABLE_NAME": sessions_table.table_name,
                "DYNAMODB_CHECKPOINTS_TABLE": checkpoints_table.table_name,
                "DYNAMODB_MEMORY_TABLE": memory_table.table_name,
                "S3_BUCKET_NAME": pdf_bucket.bucket_name,
                "RUNNER_FUNCTION_NAME": runner_fn.function_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-haiku-4-5-20251001-v1:0",
                "BEDROCK_GUARDRAIL_ID": "",
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # IAM — Runner permissions
        pdf_bucket.grant_read(runner_fn)
        sessions_table.grant_read_write_data(runner_fn)
        checkpoints_table.grant_read_write_data(runner_fn)
        memory_table.grant_read_write_data(runner_fn)
        runner_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        # IAM — API permissions
        pdf_bucket.grant_read_write(api_fn)
        sessions_table.grant_read_write_data(api_fn)
        checkpoints_table.grant_read_write_data(api_fn)
        memory_table.grant_read_write_data(api_fn)
        runner_fn.grant_invoke(api_fn)

        # API Gateway
        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{prefix}-api",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
            deploy_options=apigw.StageOptions(stage_name=env_name),
        )

        integration = apigw.LambdaIntegration(api_fn)

        # /sessions
        sessions = api.root.add_resource("sessions")
        sessions.add_method("GET", integration)
        sessions.add_method("POST", integration)

        # /sessions/{session_id}
        session = sessions.add_resource("{session_id}")
        session.add_method("GET", integration)

        # /sessions/{session_id}/run
        session.add_resource("run").add_method("POST", integration)

        # /sessions/{session_id}/status
        session.add_resource("status").add_method("GET", integration)

        # /sessions/{session_id}/job
        job = session.add_resource("job")
        job.add_method("GET", integration)
        job.add_method("POST", integration)

        # /sessions/{session_id}/resume
        session.add_resource("resume").add_method("POST", integration)
