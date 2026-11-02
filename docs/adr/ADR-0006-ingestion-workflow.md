# ADR-0006: Queue-driven ingestion workflow

- Status: Accepted
- Context: Ingestion can take longer than a web request.
- Decision: Cloud path is S3 upload, SQS message, Lambda trigger, then Step Functions. Failed
  messages go to a dead-letter queue. Start with a simple state machine; use Distributed Map only
  if the workload justifies it.
- Consequences: Work is retried safely only if each step is idempotent; this is tested.