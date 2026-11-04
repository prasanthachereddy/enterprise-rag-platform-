from typing import Any

import pytest

from enterprise_rag.answers.evidence import coverage, select_evidence
from enterprise_rag.answers.offline import NOT_FOUND_TEXT, best_sentences, build_offline_answer
from enterprise_rag.answers.service import MAX_QUESTION_CHARS, ask
from enterprise_rag.config import Settings
from enterprise_rag.retrieval.models import SearchResult

ANNUAL = (
    "Full-time employees receive 24 days of paid annual leave per calendar year. "
    "Leave must be requested in the HR portal at least five working days in advance.\n\n"
    "Unused leave of up to 5 days may be carried forward to the next calendar year."
)
SICK = (
    "Employees receive 10 days of paid sick leave per year. "
    "A medical certificate is required for absences longer than three consecutive days."
)
QUESTION = "how many days of annual leave"


def make(chunk_id: str, text: str, heading: str, rank: int = 1) -> SearchResult:
    return SearchResult(chunk_id, "doc-1", "leave.html", heading, text, 1.0, rank)


def two_results() -> list[SearchResult]:
    return [make("c-sick", SICK, "Sick Leave", 1), make("c-annual", ANNUAL, "Annual Leave", 2)]


def test_coverage_is_the_share_of_question_words_found() -> None:
    words = {"day", "annual", "leave"}
    assert coverage(words, make("a", ANNUAL, "Annual Leave")) == 1.0
    assert coverage(words, make("s", SICK, "Sick Leave")) == pytest.approx(2 / 3)
    assert coverage(set(), make("a", ANNUAL, "")) == 0.0


def test_select_evidence_puts_the_best_passage_first() -> None:
    kept = select_evidence(QUESTION, two_results(), min_coverage=0.5)
    assert [r.chunk_id for r in kept] == ["c-annual", "c-sick"]


def test_select_evidence_drops_weak_passages() -> None:
    kept = select_evidence(QUESTION, two_results(), min_coverage=0.9)
    assert [r.chunk_id for r in kept] == ["c-annual"]


def test_best_sentences_keep_original_order_and_skip_unrelated_ones() -> None:
    sentences = best_sentences(QUESTION, ANNUAL)
    assert len(sentences) == 2
    assert sentences[0].startswith("Full-time employees")
    assert sentences[1].startswith("Leave must be requested")


def test_found_answer_has_a_citation_marker_and_source() -> None:
    answer = build_offline_answer(QUESTION, two_results(), 0.5)
    assert answer.found is True
    assert "24 days" in answer.text
    assert answer.text.endswith("[1]")
    assert answer.citations[0].chunk_id == "c-annual"
    assert answer.citations[0].heading == "Annual Leave"
    assert len(answer.retrieved) == 2


def test_unrelated_question_gets_a_safe_refusal() -> None:
    answer = build_offline_answer("what is the dress code for office parties", two_results(), 0.5)
    assert answer.found is False
    assert answer.text == NOT_FOUND_TEXT
    assert answer.citations == []


def test_question_with_only_stopwords_is_refused() -> None:
    assert build_offline_answer("what is the", two_results(), 0.5).found is False


class FakeClient:
    def search(self, index: str, body: dict[str, Any]) -> dict[str, Any]:
        def source(chunk_id: str, text: str, heading: str) -> dict[str, Any]:
            return {
                "_score": 1.0,
                "_source": {
                    "chunk_id": chunk_id,
                    "document_id": "doc-1",
                    "source_filename": "leave.html",
                    "heading": heading,
                    "text": text,
                },
            }

        hits = [source("c-sick", SICK, "Sick Leave"), source("c-annual", ANNUAL, "Annual Leave")]
        return {"hits": {"hits": hits}}


class FakeEmbedder:
    model_name = "fake"
    dimensions = 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_ask_runs_search_then_answers() -> None:
    settings = Settings(_env_file=None)
    answer = ask("  how many   days of annual leave? ", settings, FakeClient(), FakeEmbedder())
    assert answer.found is True
    assert answer.question == "how many days of annual leave?"
    assert answer.citations[0].chunk_id == "c-annual"


@pytest.mark.parametrize("question", ["   ", "x" * (MAX_QUESTION_CHARS + 1)])
def test_ask_rejects_empty_and_oversized_questions(question: str) -> None:
    with pytest.raises(ValueError):
        ask(question, Settings(_env_file=None), FakeClient(), FakeEmbedder())
'''

def test_ask_refuses_bedrock_mode_until_it_is_built() -> None:
    settings = Settings(_env_file=None, answer_mode="bedrock")
    with pytest.raises(NotImplementedError):
        ask(QUESTION, settings, FakeClient(), FakeEmbedder())'''