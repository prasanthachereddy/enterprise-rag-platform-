"""CDK entry point. Run through the CDK CLI: cdk synth / cdk deploy / cdk destroy."""

import os
from pathlib import Path

import aws_cdk as cdk

from infra.stack import IngestionStack

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    code_path = ROOT / "build" / "lambda"
    if not code_path.is_dir():
        raise SystemExit("build\\lambda is missing. Run: python scripts\\build_lambda.py")
    app = cdk.App()
    IngestionStack(
        app,
        "EnterpriseRagIngest",
        code_path=str(code_path),
        env=cdk.Environment(
            account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
            region=os.environ.get("CDK_DEFAULT_REGION"),
        ),
    )
    cdk.Tags.of(app).add("project", "enterprise-rag-platform")
    app.synth()


if __name__ == "__main__":
    main()