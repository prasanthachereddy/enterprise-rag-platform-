# ADR-0007: Security baseline

- Status: Accepted
- Context: The repository is public.
- Decision: Never commit secrets or private documents. Validate uploads. Use least-privilege IAM.
  Do not log document text, prompts or credentials. WAF, customer-managed KMS keys, Secrets
  Manager and WebSocket are design-only topics, documented but not built.
- Consequences: The project stays honest about what is implemented.