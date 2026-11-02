# ADR-0009: Retrieval ablation

- Status: Accepted
- Context: We need evidence, not opinion, about which retriever is better.
- Decision: Compare BM25 only, vector only, hybrid, and hybrid plus reranking on one fixed query
  set using Recall@K, Precision@K, MRR and Hit Rate.
- Consequences: Corpus, queries and labels stay frozen between runs. Results go in docs.