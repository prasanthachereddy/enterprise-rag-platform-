INTERVIEW_NOTES# Interview notes (keep honest, fill the brackets from docs/EVALUATION.md)

## 60-second pitch

I built an internal policy assistant end to end. Documents are validated, chunked by paragraph and indexed in OpenSearch. Questions go through BM25, vector and hybrid search with Reciprocal Rank Fusion and a reranker. A check on the retrieved evidence decides whether to answer or refuse, so unanswerable questions are refused and cost nothing. Answers come either from an offline extractor or from an Amazon Bedrock model with citations I validate. I measured every retrieval mode on a fixed golden set, and I defined the cloud ingestion path as CDK code: S3, SQS with a dead-letter queue, Lambda, Step Functions and a DynamoDB audit table. I deployed it once, smoke-tested it and destroyed it to control cost.

## What I can say with evidence

| Claim | Evidence |
|---|---|
| Tests, lint and strict types pass | `python scripts\verify_all.py` summary; CI run on GitHub |
| Retrieval modes compared | `docs/EVALUATION.md`: vector alone was best |
| Refusal behaviour measured | `docs/EVALUATION.md`: 5 of 6 offline, 6 of 6 with the Nova answer step |
| Cloud stack deployed once | Smoke test returned PROCESSED with 2 chunks, then `cdk destroy` |
| Bedrock verified live | Cited answer and a refusal without a model call; Amazon Nova Micro |

## What not to claim

- Not "production", not "deployed" (it was torn down), not "high accuracy" (the corpus is 15 synthetic documents).
- The reranker is a simple word-overlap scorer, not a cross-encoder.
- The evidence check is word-based and can refuse answerable questions. The golden set shows how often.
- Cloud ingestion stops at chunks in S3 plus an audit row. OpenSearch is local only.

## Design decisions and trade-offs

1. **Evidence check before the model.** Vector search always returns results, so scores cannot prove a question is unanswerable. Counting question words in the passages is simple and testable. Trade-off: synonyms cause false refusals.
2. **Idempotency.** Document IDs come from content hashes, and Step Functions runs are named from a hash of bucket, key and ETag, so re-delivered events are harmless.
3. **Dead-letter queue and partial batch failures.** One bad message does not block the others.
4. **Model ID is a setting.** I changed from Claude Haiku 4.5 to Amazon Nova Micro without code changes, because Anthropic access needed extra agreements in my account (ADR-0013).
5. **Offline default.** Anyone can clone the repository and run the tests without AWS.
6. **Cost control.** Local first, one short deploy, destroy afterwards, capped output tokens.
7. **Labels by section, not chunk ID.** Chunk IDs change when chunking changes; (file, heading) pairs do not.

## Likely questions

- *Why hybrid search?* BM25 catches exact terms (numbers, names); vectors catch paraphrase; RRF merges ranks without needing comparable scores.
- *How do you stop hallucination?* Evidence gate, "only use passages" prompt, passages treated as untrusted data, and a check that every answer cites a real passage. A citation proves the source exists, not that the claim is right, so I also check key facts on the golden set.
- *How would you scale it?* Managed OpenSearch or a vector store, batching and a cross-encoder reranker, Step Functions Distributed Map for large uploads, and real monitoring. I did not build these.
- *What would you improve first?* Replace the word-based evidence check with a semantic relevance check, and grow the golden set.
- *What went wrong?* [Pick one real item from docs/MISTAKES_LOG.md, for example the embedding-dimension validator bug found in Phase 1.]

## Resume bullets (edit the brackets; keep only true statements)

- Built a retrieval-augmented question-answering system in Python with BM25, vector and hybrid (RRF) search over OpenSearch; compared modes on a 24-question golden set (Hit@5 0.92 to 1.00, MRR 0.89 to 1.00 across modes).
- Designed an evidence check that refuses unanswerable questions before any model call (5 of 6 refused by the check alone; 6 of 6 with the model step).
- Defined a serverless ingestion workflow in AWS CDK (S3, SQS with DLQ, Lambda, Step Functions, DynamoDB); deployed once, smoke-tested and destroyed to control cost.
- Added Amazon Bedrock answer generation through the Converse API with citation validation, prompt-injection defences and capped token usage.
- Set up one-command verification and GitHub Actions CI: Ruff, strict mypy, 120 tests tests and CDK synth.