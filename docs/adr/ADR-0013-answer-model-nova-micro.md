# ADR-0013: Answer model changed to Amazon Nova Micro

- Status: Accepted (supersedes the model choice in ADR-0005 and ADR-0012)
- Context: Anthropic models on Bedrock needed extra agreements and approvals in this account. Amazon Nova Micro worked immediately and costs little.
- Decision: Use apac.amazon.nova-micro-v1:0 through the Converse API. The model ID is a setting, so Claude Haiku 4.5 or another model can be used by changing BEDROCK_CHAT_MODEL_ID.
- Consequences: Verified live on a cited answer and a refusal, and measured on the golden set (docs/EVALUATION.md). The apac. profile may route requests to other Asia-Pacific regions, so only synthetic or public documents are used.