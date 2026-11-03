# ADR-0011: Cloud ingestion safety

- Status: Accepted
- Context: Queue-driven work is retried, so duplicates and poison messages are normal, not rare.
- Decision: Name each Step Functions run from a hash of bucket, key and ETag. Trigger only on the uploads/ prefix. Send messages that fail 3 times to a dead-letter queue. Return SQS partial-batch failures. Protect the API with IAM signing and throttling. Never return or log document text from Lambda.
- Consequences: Re-delivered events are harmless. The API needs signed requests (scripts/cloud_smoke.py does this). A presigned upload link cannot cap file size, so the process Lambda rejects oversized files after upload. WAF and KMS customer keys stay design-only.