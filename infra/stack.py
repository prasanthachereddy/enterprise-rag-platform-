"""CDK stack: S3 -> SQS (with DLQ) -> Lambda -> Step Functions -> DynamoDB, plus an IAM-only API."""

from typing import Any, cast

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_authorizers as authorizers
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as sources
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

TRIGGER_TIMEOUT_SECONDS = 30
MAX_RECEIVE_COUNT = 3


class IngestionStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, *, code_path: str, **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(
            self,
            "DocumentBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(7))],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        table = dynamodb.Table(
            self,
            "AuditTable",
            partition_key=dynamodb.Attribute(name="source_key", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        def make_function(
            name: str, handler: str, timeout: int, environment: dict[str, str]
        ) -> _lambda.Function:
            return _lambda.Function(
                self,
                name,
                runtime=_lambda.Runtime.PYTHON_3_11,
                handler=handler,
                code=_lambda.Code.from_asset(code_path),
                timeout=Duration.seconds(timeout),
                memory_size=256,
                environment=environment,
                log_group=logs.LogGroup(
                    self,
                    f"{name}Logs",
                    retention=logs.RetentionDays.ONE_WEEK,
                    removal_policy=RemovalPolicy.DESTROY,
                ),
            )

        process_fn = make_function(
            "ProcessFunction",
            "enterprise_rag.cloud.process_handler.handler",
            60,
            {"CHUNK_SIZE": "900", "CHUNK_OVERLAP": "120", "MAX_UPLOAD_BYTES": "10485760"},
        )
        bucket.grant_read(process_fn, "uploads/*")
        bucket.grant_put(process_fn, "processed/*")

        # Step Functions: process the file, then write one audit row (processed, rejected, failed).
        def audit(
            name: str, status: str, **extra: tasks.DynamoAttributeValue
        ) -> tasks.DynamoPutItem:
            item = {
                "source_key": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.key")
                ),
                "status": tasks.DynamoAttributeValue.from_string(status),
                "execution": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.Execution.Name")
                ),
                "updated_at": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.State.EnteredTime")
                ),
            }
            item.update(extra)
            return tasks.DynamoPutItem(
                self, name, table=table, item=item, result_path=sfn.JsonPath.DISCARD
            )

        def text(path: str) -> tasks.DynamoAttributeValue:
            return tasks.DynamoAttributeValue.from_string(sfn.JsonPath.string_at(path))

        process = tasks.LambdaInvoke(
            self,
            "ProcessDocument",
            lambda_function=process_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "bucket": sfn.JsonPath.string_at("$.bucket"),
                    "key": sfn.JsonPath.string_at("$.key"),
                }
            ),
            payload_response_only=True,
            result_path="$.process",
        )
        process.add_retry(
            errors=["States.ALL"], interval=Duration.seconds(2), max_attempts=2, backoff_rate=2.0
        )
        audit_processed = audit(
            "AuditProcessed",
            "PROCESSED",
            document_id=text("$.process.document_id"),
            output_key=text("$.process.output_key"),
            chunk_count=tasks.DynamoAttributeValue.number_from_string(
                sfn.JsonPath.string_at("$.process.chunk_count")
            ),
        )
        audit_rejected = audit("AuditRejected", "REJECTED", reason=text("$.process.reason"))
        audit_failed = audit("AuditFailed", "FAILED", reason=text("$.error.Error"))
        process.add_catch(audit_failed, errors=["States.ALL"], result_path="$.error")

        done = sfn.Succeed(self, "Done")
        choice = sfn.Choice(self, "Accepted?")
        choice.when(
            sfn.Condition.string_equals("$.process.status", "PROCESSED"),
            audit_processed.next(done),
        )
        choice.otherwise(audit_rejected.next(done))
        audit_failed.next(sfn.Fail(self, "RunFailed", error="IngestionFailed"))

        state_machine = sfn.StateMachine(
            self,
            "IngestionWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(process.next(choice)),
            timeout=Duration.minutes(5),
        )

        # S3 -> SQS (with a dead-letter queue) -> trigger Lambda -> Step Functions.
        dead_letters = sqs.Queue(
            self,
            "IngestDeadLetterQueue",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )
        queue = sqs.Queue(
            self,
            "IngestQueue",
            visibility_timeout=Duration.seconds(TRIGGER_TIMEOUT_SECONDS * 6),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=MAX_RECEIVE_COUNT, queue=dead_letters
            ),
        )
        # Only uploads/ triggers the flow; the processed/ files we write never do (no loop).
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(queue),
            s3.NotificationKeyFilter(prefix="uploads/"),
        )
        trigger_fn = make_function(
            "TriggerFunction",
            "enterprise_rag.cloud.trigger_handler.handler",
            TRIGGER_TIMEOUT_SECONDS,
            {"STATE_MACHINE_ARN": state_machine.state_machine_arn},
        )
        state_machine.grant_start_execution(trigger_fn)
        trigger_fn.add_event_source(
            sources.SqsEventSource(queue, batch_size=5, report_batch_item_failures=True)
        )

        # API: only callers who sign requests with AWS credentials (IAM) get in.
        api_fn = make_function(
            "ApiFunction",
            "enterprise_rag.cloud.api_handler.handler",
            10,
            {"BUCKET_NAME": bucket.bucket_name, "TABLE_NAME": table.table_name},
        )
        bucket.grant_put(api_fn, "uploads/*")
        table.grant_read_data(api_fn)
        api = apigw.HttpApi(self, "IngestApi", default_authorizer=authorizers.HttpIamAuthorizer())
        integration = integrations.HttpLambdaIntegration("ApiIntegration", api_fn)
        api.add_routes(path="/uploads", methods=[apigw.HttpMethod.POST], integration=integration)
        api.add_routes(path="/status", methods=[apigw.HttpMethod.GET], integration=integration)
        if api.default_stage is not None:
            stage = cast(apigw.CfnStage, api.default_stage.node.default_child)
            stage.default_route_settings = apigw.CfnStage.RouteSettingsProperty(
                throttling_burst_limit=10, throttling_rate_limit=5
            )

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "StateMachineArn", value=state_machine.state_machine_arn)
        CfnOutput(self, "DeadLetterQueueUrl", value=dead_letters.queue_url)
        CfnOutput(self, "ApiUrl", value=api.url or "")