# ADR-0004: Retrieval progression

- Status: Accepted
- Context: A more complex retriever is not automatically better.
- Decision: Build BM25, then vector search, then hybrid search using Reciprocal Rank Fusion,
  then a reranking stage, and keep each one switchable.
- Consequences: Every mode can be tested and compared (see ADR-0009).