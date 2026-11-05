# Evaluation results

Generated: 2026-11-05 15:57 UTC. Corpus: 15 synthetic documents. Questions and labels are frozen in `data/eval/golden.jsonl` (ADR-0009).

## Settings

- chunk_size: `900`
- chunk_overlap: `120`
- retrieval_top_k: `5`
- retrieval_candidates: `20`
- rrf_k: `60`
- min_query_coverage: `0.5`
- embedding_model: `BAAI/bge-small-en-v1.5`
- answer_model: `apac.amazon.nova-micro-v1:0`

## Retrieval (24 answerable questions)

| Mode | Recall@3 | Recall@5 | Precision@3 | Precision@5 | MRR | Hit@1 | Hit@5 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.92 | 0.92 | 0.31 | 0.18 | 0.89 | 0.88 | 0.92 |
| vector | 1.00 | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | 1.00 |
| hybrid | 1.00 | 1.00 | 0.33 | 0.20 | 0.96 | 0.92 | 1.00 |
| rerank | 1.00 | 1.00 | 0.33 | 0.20 | 0.96 | 0.92 | 1.00 |

Questions with no relevant passage in the top 5:

- bm25: q04, q06
- vector: none
- hybrid: none
- rerank: none

## Answers

| Answer mode | Answered | Key fact present | Right section cited | Unanswerable refused | Errors |
|---|---|---|---|---|---|
| offline | 88% | 88% | 88% | 83% | 0 |
| bedrock (apac.amazon.nova-micro-v1:0) | 88% | 88% | 88% | 100% | 0 |

Rates use 24 answerable and 6 unanswerable questions.

**offline**

- Answerable but refused: q04, q05, q06
- Key fact missing from the answer: none
- Right section not cited: none
- Unanswerable but answered: u06

**bedrock (apac.amazon.nova-micro-v1:0)**

- Answerable but refused: q04, q05, q06
- Key fact missing from the answer: none
- Right section not cited: none
- Unanswerable but answered: none

## How to read this

- A key-fact check is a substring match, so a correct answer worded differently (for example 2000 instead of 2,000) counts as a miss.
- The corpus is small and synthetic. Treat the numbers as a regression check and a comparison between modes, not as production accuracy.
