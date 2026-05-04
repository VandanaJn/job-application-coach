import os
import aws_cdk as cdk
from stacks.job_coach_stack import JobCoachStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region="us-east-1",
)

JobCoachStack(app, "JobCoachDev", env_name="dev", env=env)
JobCoachStack(app, "JobCoachProd", env_name="prod", env=env)

app.synth()
