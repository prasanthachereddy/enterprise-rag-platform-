from typing import Any

import pytest
from aws_cdk import App
from aws_cdk.assertions import Match, Template

from infra.stack import MAX_RECEIVE_COUNT, TRIGGER_TIMEOUT_SECONDS, IngestionStack


@pytest.fixture(scope="module")
def template(tmp_path_factory: pytest.TempPathFactory) -> Template:
    code = tmp_path_factory.mktemp("lambda_code")
    (code / "placeholder.py").write_text("x = 1\n", encoding="utf-8")
    stack = IngestionStack(App(), "TestStack", code_path=str(code))
    return Template.from_stack(stack)


def resources(template: Template, kind: str) -> dict[str, Any]:
    return dict(template.find_resources(kind))


def test_bucket_blocks_public_access_and_expires_objects(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "LifecycleConfiguration": {
                "Rules": [Match.object_like({"ExpirationInDays": 7, "Status": "Enabled"})]
            },
        },
    )


def test_only_the_uploads_prefix_triggers_the_queue(template: Template) -> None:
    template.has_resource_properties(
        "Custom::S3BucketNotifications",
        {
            "NotificationConfiguration": {
                "QueueConfigurations": [
                    Match.object_like(
                        {
                            "Events": ["s3:ObjectCreated:*"],
                            "Filter": {
                                "Key": {"FilterRules": [{"Name": "prefix", "Value": "uploads/"}]}
                            },
                        }
                    )
                ]
            }
        },
    )


def test_queue_has_a_dead_letter_queue_and_a_safe_visibility_timeout(template: Template) -> None:
    template.resource_count_is("AWS::SQS::Queue", 2)
    template.has_resource_properties(
        "AWS::SQS::Queue",
        {
            "RedrivePolicy": Match.object_like({"maxReceiveCount": MAX_RECEIVE_COUNT}),
            "VisibilityTimeout": TRIGGER_TIMEOUT_SECONDS * 6,
        },
    )


def test_trigger_reports_partial_batch_failures(template: Template) -> None:
    template.has_resource_properties(
        "AWS::Lambda::EventSourceMapping",
        {"FunctionResponseTypes": ["ReportBatchItemFailures"], "BatchSize": 5},
    )


def test_audit_table_is_on_demand_and_removable(template: Template) -> None:
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "BillingMode": "PAY_PER_REQUEST",
            "KeySchema": [{"AttributeName": "source_key", "KeyType": "HASH"}],
        },
    )
    for table in resources(template, "AWS::DynamoDB::Table").values():
        assert table["DeletionPolicy"] == "Delete"


def test_state_machine_exists_with_a_timeout(template: Template) -> None:
    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    machine = next(iter(resources(template, "AWS::StepFunctions::StateMachine").values()))
    definition = str(machine["Properties"]["DefinitionString"])
    for state in ("ProcessDocument", "AuditProcessed", "AuditRejected", "AuditFailed"):
        assert state in definition
    assert "TimeoutSeconds" in definition


def test_every_api_route_requires_iam_signing(template: Template) -> None:
    routes = resources(template, "AWS::ApiGatewayV2::Route")
    assert len(routes) == 2
    for route in routes.values():
        assert route["Properties"]["AuthorizationType"] == "AWS_IAM"


def test_api_stage_is_throttled(template: Template) -> None:
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Stage",
        {"DefaultRouteSettings": {"ThrottlingBurstLimit": 10, "ThrottlingRateLimit": 5}},
    )


def test_no_policy_grants_every_action_on_every_resource(template: Template) -> None:
    for policy in resources(template, "AWS::IAM::Policy").values():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            actions = statement["Action"]
            actions = [actions] if isinstance(actions, str) else actions
            assert "*" not in actions
