# Evaluation results

Generated: 2026-11-08 01:56 UTC. Corpus: 15 synthetic documents. Questions and labels are frozen in `data\eval\newset.jsonl` (ADR-0009).

## Settings

- chunk_size: `900`
- chunk_overlap: `120`
- retrieval_top_k: `5`
- retrieval_candidates: `20`
- rrf_k: `60`
- min_query_coverage: `0.5`
- embedding_model: `BAAI/bge-small-en-v1.5`
- answer_model: `apac.amazon.nova-micro-v1:0`

## Retrieval (14 answerable questions)

| Mode | Recall@3 | Recall@5 | Precision@3 | Precision@5 | MRR | Hit@1 | Hit@5 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.79 | 0.79 | 0.26 | 0.16 | 0.75 | 0.71 | 0.79 |
| vector | 0.93 | 0.93 | 0.31 | 0.19 | 0.93 | 0.93 | 0.93 |
| hybrid | 0.86 | 0.86 | 0.29 | 0.17 | 0.79 | 0.71 | 0.86 |
| rerank | 1.00 | 1.00 | 0.33 | 0.20 | 0.86 | 0.71 | 1.00 |

Questions with no relevant passage in the top 5:

- bm25: n04, n07, n11
- vector: n08
- hybrid: n04, n11
- rerank: none

## Answers

| Answer mode | Answered | Key fact present | Right section cited | Unanswerable refused | Errors |
|---|---|---|---|---|---|
| offline | 50% | 50% | 50% | 83% | 0 |

Rates use 14 answerable and 6 unanswerable questions.

**offline**

- Answerable but refused: n04, n07, n08, n09, n11, n12, n14
- Key fact missing from the answer: none
- Right section not cited: none
- Unanswerable but answered: u06

## How to read this

- A key-fact check is a substring match, so a correct answer worded differently (for example 2000 instead of 2,000) counts as a miss.
- The corpus is small and synthetic. Treat the numbers as a regression check and a comparison between modes, not as production accuracy.
