# ADR-0005: Model provider boundary

- Status: Accepted
- Context: Model IDs and regional availability change.
- Decision: Use Claude Haiku 4.5 on Amazon Bedrock for answers and Titan Text Embeddings v2 for
  vectors. Read model IDs from settings and call Bedrock only through small functions. From
  Mumbai (ap-south-1) use the global inference profile ID.
- Consequences: Tests use fakes. Global profiles may process requests in other regions, so only
  synthetic or public documents are used.
-Local embeddings (TEI, bge-small-en-v1.5) are used first; Bedrock embeddings are a later upgrade behind the same Embedder protocol.