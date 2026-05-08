from __future__ import annotations

import os
import shutil
import subprocess
import sys
import jsii
from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    CfnResource,
    CustomResource,
    Duration,
    ILocalBundling,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_codebuild as codebuild,
    aws_dynamodb as dynamodb,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
)
from constructs import Construct


_LINUX_PIP_FLAGS = [
    "--platform", "manylinux2014_x86_64",
    "--python-version", "312",
    "--implementation", "cp",
    "--only-binary", ":all:",
]


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
                *_LINUX_PIP_FLAGS,
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


@jsii.implements(ILocalBundling)
class _RunnerLocalBundler:
    """Bundles the Runner Lambda — includes graph/ and agents/ alongside the handler."""

    def __init__(self, project_root: str) -> None:
        self._root = project_root

    def try_bundle(self, output_dir: str, options: BundlingOptions) -> bool:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", os.path.join(self._root, "lambda", "runner", "requirements.txt"),
                *_LINUX_PIP_FLAGS,
                "-t", output_dir, "--quiet",
            ])
            for pkg in ("graph", "agents"):
                shutil.copytree(
                    os.path.join(self._root, pkg),
                    os.path.join(output_dir, pkg),
                    dirs_exist_ok=True,
                )
            shutil.copy(
                os.path.join(self._root, "lambda", "runner", "handler.py"),
                output_dir,
            )
            return True
        except Exception as exc:
            print(f"Local bundling failed, falling back to Docker: {exc}")
            return False


@jsii.implements(ILocalBundling)
class _AnswerCoachAssetBundler:
    """Bundles the AnswerCoach AgentCore CodeBuild source — Dockerfile + main.py + requirements.txt + agents/."""

    def __init__(self, project_root: str) -> None:
        self._root = project_root

    def try_bundle(self, output_dir: str, options: BundlingOptions) -> bool:
        try:
            for f in ("Dockerfile", "main.py", "requirements.txt"):
                shutil.copy(
                    os.path.join(self._root, "lambda", "answer_coach", f),
                    os.path.join(output_dir, f),
                )
            shutil.copytree(
                os.path.join(self._root, "agents"),
                os.path.join(output_dir, "agents"),
                dirs_exist_ok=True,
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

        # DynamoDB — user profiles (resume storage)
        users_table = dynamodb.Table(
            self,
            "UsersTable",
            table_name=f"{prefix}-users",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal,
        )

        # DynamoDB — saved job postings
        jobs_table = dynamodb.Table(
            self,
            "JobsTable",
            table_name=f"{prefix}-jobs",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal,
        )

        # DynamoDB — interview practice sessions
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

        shared_env = {
            "ENVIRONMENT": env_name,
            "DYNAMODB_TABLE_NAME": sessions_table.table_name,
            "DYNAMODB_USERS_TABLE": users_table.table_name,
            "DYNAMODB_JOBS_TABLE": jobs_table.table_name,
            "DYNAMODB_CHECKPOINTS_TABLE": checkpoints_table.table_name,
            "DYNAMODB_MEMORY_TABLE": memory_table.table_name,
            "S3_BUCKET_NAME": pdf_bucket.bucket_name,
            "BEDROCK_MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "BEDROCK_GUARDRAIL_ID": "",
        }

        # Lambda — Runner (async LangGraph execution)
        runner_fn = lambda_.Function(
            self,
            "RunnerFunction",
            function_name=f"{prefix}-runner",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                project_root,
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    local=_RunnerLocalBundler(project_root),
                    command=[
                        "bash", "-c",
                        "pip install -r lambda/runner/requirements.txt -t /asset-output --quiet"
                        " && cp -r graph agents /asset-output"
                        " && cp lambda/runner/handler.py /asset-output",
                    ],
                ),
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment=shared_env,
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
            environment={**shared_env, "RUNNER_FUNCTION_NAME": runner_fn.function_name},
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # IAM — Runner permissions
        pdf_bucket.grant_read(runner_fn)
        users_table.grant_read_data(runner_fn)
        jobs_table.grant_read_data(runner_fn)
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
        users_table.grant_read_write_data(api_fn)
        jobs_table.grant_read_write_data(api_fn)
        sessions_table.grant_read_write_data(api_fn)
        checkpoints_table.grant_read_write_data(api_fn)
        memory_table.grant_read_write_data(api_fn)
        runner_fn.grant_invoke(api_fn)

        # ── AgentCore AnswerCoach ────────────────────────────────────────────

        # ECR — container image for AnswerCoach agent
        answer_coach_repo = ecr.Repository(
            self,
            "AnswerCoachRepo",
            repository_name=f"{prefix}-answer-coach",
            removal_policy=removal,
            empty_on_delete=is_dev,
        )

        # IAM — execution role that AgentCore assumes when running the agent
        agentcore_exec_role = iam.Role(
            self,
            "AnswerCoachExecRole",
            role_name=f"{prefix}-answer-coach-exec",
            assumed_by=iam.ServicePrincipal(
                "bedrock-agentcore.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.account},
                    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:*"},
                },
            ),
        )
        agentcore_exec_role.add_to_policy(iam.PolicyStatement(
            actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"],
            resources=[answer_coach_repo.repository_arn],
        ))
        agentcore_exec_role.add_to_policy(iam.PolicyStatement(
            actions=["ecr:GetAuthorizationToken"],
            resources=["*"],
        ))
        agentcore_exec_role.add_to_policy(iam.PolicyStatement(
            actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups", "logs:DescribeLogStreams"],
            resources=["*"],
        ))
        agentcore_exec_role.add_to_policy(iam.PolicyStatement(
            actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
            resources=["*"],
        ))
        agentcore_exec_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"],
        ))
        memory_table.grant_read_data(agentcore_exec_role)

        # IAM — CodeBuild role for building the ARM64 image
        codebuild_role = iam.Role(
            self,
            "AnswerCoachBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
        )
        answer_coach_repo.grant_pull_push(codebuild_role)
        codebuild_role.add_to_policy(iam.PolicyStatement(
            actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
            resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/*"],
        ))
        codebuild_role.add_to_policy(iam.PolicyStatement(
            actions=["ecr:GetAuthorizationToken"],
            resources=["*"],
        ))

        # S3 asset — uploads the CodeBuild source (Dockerfile + main.py + requirements.txt + agents/)
        # The bundler ensures agents/ ships alongside the lambda so main.py can import from it.
        answer_coach_asset = s3_assets.Asset(
            self,
            "AnswerCoachAsset",
            path=project_root,
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                local=_AnswerCoachAssetBundler(project_root),
                command=[
                    "bash", "-c",
                    "cp /asset-input/lambda/answer_coach/Dockerfile /asset-output/"
                    " && cp /asset-input/lambda/answer_coach/main.py /asset-output/"
                    " && cp /asset-input/lambda/answer_coach/requirements.txt /asset-output/"
                    " && cp -r /asset-input/agents /asset-output/agents",
                ],
            ),
        )
        answer_coach_asset.grant_read(codebuild_role)

        # CodeBuild — builds the ARM64 Docker image and pushes to ECR
        image_tag = "latest"
        answer_coach_build = codebuild.Project(
            self,
            "AnswerCoachBuild",
            project_name=f"{prefix}-answer-coach-build",
            role=codebuild_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2_STANDARD_3_0,
                privileged=True,
            ),
            source=codebuild.Source.s3(
                bucket=answer_coach_asset.bucket,
                path=answer_coach_asset.s3_object_key,
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {"commands": [
                        f"aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {self.account}.dkr.ecr.{self.region}.amazonaws.com",
                    ]},
                    "build": {"commands": [
                        f"docker build --platform linux/arm64 -t answer-coach:{image_tag} .",
                        f"docker tag answer-coach:{image_tag} {answer_coach_repo.repository_uri}:{image_tag}",
                    ]},
                    "post_build": {"commands": [
                        f"docker push {answer_coach_repo.repository_uri}:{image_tag}",
                    ]},
                },
            }),
        )

        # Lambda — custom resource that triggers the CodeBuild build during deploy
        build_trigger_fn = lambda_.Function(
            self,
            "AnswerCoachBuildTrigger",
            function_name=f"{prefix}-answer-coach-build-trigger",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            timeout=Duration.minutes(15),
            code=lambda_.InlineCode("""
import boto3
import json
import time
import urllib.request

def _cfn_send(event, context, status, data):
    body = json.dumps({
        "Status": status,
        "Reason": f"See CloudWatch log stream: {context.log_stream_name}",
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": data,
    }).encode()
    req = urllib.request.Request(
        event["ResponseURL"],
        data=body,
        headers={"Content-Type": "", "Content-Length": len(body)},
        method="PUT",
    )
    urllib.request.urlopen(req)

def handler(event, context):
    try:
        if event["RequestType"] == "Delete":
            _cfn_send(event, context, "SUCCESS", {})
            return
        project = event["ResourceProperties"]["ProjectName"]
        cb = boto3.client("codebuild")
        build_id = cb.start_build(projectName=project)["build"]["id"]
        deadline = context.get_remaining_time_in_millis() / 1000 - 30
        start = time.time()
        while True:
            if time.time() - start > deadline:
                _cfn_send(event, context, "FAILED", {"Error": "Timeout"})
                return
            status = cb.batch_get_builds(ids=[build_id])["builds"][0]["buildStatus"]
            if status == "SUCCEEDED":
                _cfn_send(event, context, "SUCCESS", {"BuildId": build_id})
                return
            if status in ("FAILED", "FAULT", "STOPPED", "TIMED_OUT"):
                _cfn_send(event, context, "FAILED", {"Error": status})
                return
            time.sleep(30)
    except Exception as e:
        _cfn_send(event, context, "FAILED", {"Error": str(e)})
"""),
        )
        build_trigger_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
            resources=[answer_coach_build.project_arn],
        ))

        build_trigger = CustomResource(
            self,
            "TriggerAnswerCoachBuild",
            service_token=build_trigger_fn.function_arn,
            properties={"ProjectName": answer_coach_build.project_name},
        )
        build_trigger.node.add_dependency(answer_coach_build)

        # AgentCore Runtime (L1 — no higher-level CDK construct exists yet)
        answer_coach_runtime = CfnResource(
            self,
            "AnswerCoachRuntime",
            type="AWS::BedrockAgentCore::Runtime",
            properties={
                "AgentRuntimeName": f"{prefix.replace('-', '_')}_answer_coach",
                "AgentRuntimeArtifact": {
                    "ContainerConfiguration": {
                        "ContainerUri": f"{answer_coach_repo.repository_uri}:{image_tag}",
                    }
                },
                "RoleArn": agentcore_exec_role.role_arn,
                "NetworkConfiguration": {"NetworkMode": "PUBLIC"},
                "EnvironmentVariables": {
                    "BEDROCK_MODEL_ID": shared_env["BEDROCK_MODEL_ID"],
                    "DYNAMODB_MEMORY_TABLE": memory_table.table_name,
                    "AWS_REGION": self.region,
                },
            },
        )
        answer_coach_runtime.node.add_dependency(build_trigger)

        answer_coach_runtime_arn = answer_coach_runtime.get_att("AgentRuntimeArn").to_string()

        # Grant API Lambda permission to invoke the AgentCore runtime.
        # Resource must cover the endpoint ARN (runtime/<id>/runtime-endpoint/<name>),
        # not just the runtime ARN, so we use a wildcard suffix.
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:InvokeAgentRuntime"],
            resources=[
                answer_coach_runtime_arn,
                f"{answer_coach_runtime_arn}/*",
            ],
        ))

        # Inject the runtime ARN into the API Lambda environment
        api_fn.add_environment("ANSWER_COACH_RUNTIME_ARN", answer_coach_runtime_arn)

        # ── API Gateway ──────────────────────────────────────────────────────

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

        # /user
        user = api.root.add_resource("user")
        user.add_method("GET", integration)
        user.add_resource("resume").add_method("POST", integration)

        # /jobs
        jobs = api.root.add_resource("jobs")
        jobs.add_method("GET", integration)
        jobs.add_method("POST", integration)
        jobs.add_resource("{job_id}").add_method("GET", integration)

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

        # /sessions/{session_id}/coach
        session.add_resource("coach").add_method("POST", integration)

        # ── Stack outputs ────────────────────────────────────────────────────
        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="API Gateway base URL — set as VITE_API_URL in frontend/.env.local",
        )
        CfnOutput(
            self,
            "AnswerCoachRuntimeArn",
            value=answer_coach_runtime_arn,
            description="AgentCore Runtime ARN for the AnswerCoach agent",
        )
        CfnOutput(
            self,
            "PdfBucketName",
            value=pdf_bucket.bucket_name,
            description="S3 bucket name for resume PDF uploads",
        )
