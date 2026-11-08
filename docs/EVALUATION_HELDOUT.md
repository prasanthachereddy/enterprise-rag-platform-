# Evaluation results

Generated: 2026-11-08 00:38 UTC. Corpus: 15 synthetic documents. Questions and labels are frozen in `data/eval/heldout.jsonl` (ADR-0009).

## Settings

- chunk_size: `900`
- chunk_overlap: `120`
- retrieval_top_k: `5`
- retrieval_candidates: `20`
- rrf_k: `60`
- min_query_coverage: `0.5`
- embedding_model: `BAAI/bge-small-en-v1.5`
- answer_model: `apac.amazon.nova-micro-v1:0`

## Retrieval (16 answerable questions)

| Mode | Recall@3 | Recall@5 | Precision@3 | Precision@5 | MRR | Hit@1 | Hit@5 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.88 | 0.94 | 0.29 | 0.19 | 0.86 | 0.81 | 0.94 |
| vector | 1.00 | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | 1.00 |
| hybrid | 0.94 | 0.94 | 0.31 | 0.19 | 0.88 | 0.81 | 0.94 |
| rerank | 1.00 | 1.00 | 0.33 | 0.20 | 0.91 | 0.81 | 1.00 |

Questions with no relevant passage in the top 5:

- bm25: h03
- vector: none
- hybrid: h03
- rerank: none

## Answers

| Answer mode | Answered | Key fact present | Right section cited | Unanswerable refused | Errors |
|---|---|---|---|---|---|
| offline | 50% | 50% | 50% | 75% | 0 |
| bedrock (apac.amazon.nova-micro-v1:0) | 50% | 44% | 50% | 100% | 0 |

Rates use 16 answerable and 4 unanswerable questions.

**offline**

- Answerable but refused: h02, h03, h07, h08, h10, h11, h13, h15
- Key fact missing from the answer: none
- Right section not cited: none
- Unanswerable but answered: v01

**bedrock (apac.amazon.nova-micro-v1:0)**

- Answerable but refused: h02, h03, h07, h08, h10, h11, h13, h15
- Key fact missing from the answer: h05
- Right section not cited: none
- Unanswerable but answered: none

## How to read this

- A key-fact check is a substring match, so a correct answer worded differently (for example 2000 instead of 2,000) counts as a miss.
- The corpus is small and synthetic. Treat the numbers as a regression check and a comparison between modes, not as production accuracy.
