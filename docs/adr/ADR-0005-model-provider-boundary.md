# ADR-0005: Model provider boundary

- Status: Superseded in part by ADR-0013 (answer model). Embeddings: a local model is used first; Bedrock Titan is a later upgrade.
- Context: Model IDs and regional availability change.
- Decision: Use Claude Haiku 4.5 on Amazon Bedrock for answers and Titan Text Embeddings v2 for
  vectors. Read model IDs from settings and call Bedrock only through small functions. From
  Mumbai (ap-south-1) use the global inference profile ID.
- Consequences: Tests use fakes. Global profiles may process requests in other regions, so only
  synthetic or public documents are used.
-Local embeddings (TEI, bge-small-en-v1.5) are used first; Bedrock embeddings are a later upgrade behind the same Embedder protocol.- Update: the answer model is now Amazon Nova Micro (see ADR-0013). Embeddings use a local model (BAAI/bge-small-en-v1.5) behind the same Embedder protocol.