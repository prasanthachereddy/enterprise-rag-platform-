from enterprise_rag.retrieval.models import SearchResult
from enterprise_rag.retrieval.rerank import rerank, tokens
from enterprise_rag.retrieval.search import rrf_fuse


def make(chunk_id: str, text: str = "text", heading: str = "", rank: int = 1) -> SearchResult:
    return SearchResult(chunk_id, "doc", "f.txt", heading, text, 1.0, rank)


def test_rrf_rewards_chunks_found_by_both_lists() -> None:
    bm25 = [make("a"), make("b"), make("c")]
    vector = [make("c"), make("a"), make("d")]
    fused = rrf_fuse([bm25, vector], k=60, top_k=4)
    assert [r.chunk_id for r in fused][:2] == ["a", "c"]
    assert [r.rank for r in fused] == [1, 2, 3, 4]
    assert fused[0].score > fused[-1].score


def test_rrf_respects_top_k_and_handles_empty_lists() -> None:
    assert len(rrf_fuse([[make("a"), make("b")], []], k=60, top_k=1)) == 1
    assert rrf_fuse([[], []], k=60, top_k=5) == []


def test_tokens_drop_stopwords_and_plurals() -> None:
    assert tokens("How many days of annual leave?") == ["day", "annual", "leave"]


def test_reranker_promotes_the_chunk_that_answers_the_question() -> None:
    generic = make("generic", "Leave requests are handled by HR.", "Overview", rank=1)
    answer = make("answer", "Employees receive 24 days of annual leave.", "Annual Leave", rank=2)
    ranked = rerank("how many days of annual leave", [generic, answer], top_k=2)
    assert [r.chunk_id for r in ranked] == ["answer", "generic"]
    assert [r.rank for r in ranked] == [1, 2]


def test_reranker_handles_empty_input() -> None:
    assert rerank("anything", [], top_k=3) == []
    assert [r.chunk_id for r in rerank("the of", [make("a")], top_k=3)] == ["a"]