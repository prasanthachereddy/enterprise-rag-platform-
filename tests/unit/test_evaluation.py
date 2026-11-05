import json
from pathlib import Path

import pytest

from enterprise_rag.answers.bedrock import AnswerGenerationError
from enterprise_rag.answers.models import Answer, Citation
from enterprise_rag.evaluation.golden import GoldenQuestion, load_golden
from enterprise_rag.evaluation.metrics import (
    hit_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from enterprise_rag.evaluation.report import render_report
from enterprise_rag.evaluation.runner import evaluate_answers, evaluate_retrieval
from enterprise_rag.retrieval.models import SearchResult

WANTED = {("leave.html", "Annual Leave")}
RETRIEVED = [("a.md", "X"), ("leave.html", "Annual Leave"), ("b.md", "Y")]


def test_metrics_on_a_known_ranking() -> None:
    assert recall_at_k(WANTED, RETRIEVED, 1) == 0.0
    assert recall_at_k(WANTED, RETRIEVED, 2) == 1.0
    assert precision_at_k(WANTED, RETRIEVED, 2) == 0.5
    assert precision_at_k(WANTED, RETRIEVED, 5) == pytest.approx(0.2)
    assert hit_at_k(WANTED, RETRIEVED, 1) == 0.0
    assert hit_at_k(WANTED, RETRIEVED, 3) == 1.0
    assert reciprocal_rank(WANTED, RETRIEVED) == 0.5


def test_metrics_handle_nothing_relevant() -> None:
    assert reciprocal_rank(WANTED, [("a.md", "X")]) == 0.0
    assert recall_at_k(set(), RETRIEVED, 3) == 0.0


def write(path: Path, *rows: dict[str, object]) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


GOOD = {"id": "q1", "question": "Q?", "answerable": True, "source": "f.md", "heading": "H",
        "must_contain": ["24 days"]}  # fmt: skip
NO_ANSWER = {"id": "u1", "question": "Q?", "answerable": False}


def test_golden_loads_both_kinds_of_question(tmp_path: Path) -> None:
    questions = load_golden(write(tmp_path / "g.jsonl", GOOD, NO_ANSWER))
    assert [q.answerable for q in questions] == [True, False]
    assert questions[0].must_contain == ("24 days",)


@pytest.mark.parametrize(
    "rows",
    [
        [GOOD, GOOD],
        [{**GOOD, "must_contain": []}],
        [{**NO_ANSWER, "source": "f.md"}],
        [{"id": "x"}],
        [],
    ],
)
def test_golden_rejects_bad_files(tmp_path: Path, rows: list[dict[str, object]]) -> None:
    with pytest.raises(ValueError):
        load_golden(write(tmp_path / "g.jsonl", *rows))


def result(source: str, heading: str) -> SearchResult:
    return SearchResult("c", "d", source, heading, "text", 1.0, 1)


QUESTIONS = [
    GoldenQuestion("q1", "leave?", True, "leave.html", "Annual Leave", ("24 days",)),
    GoldenQuestion("q2", "pass?", True, "sec.md", "Passwords", ("14 characters",)),
    GoldenQuestion("u1", "dress?", False),
]


def test_retrieval_report_averages_over_answerable_questions_only() -> None:
    def fake_search(query: str) -> list[SearchResult]:
        if query == "leave?":
            return [result("leave.html", "Annual Leave")]
        return [result("x.md", "X"), result("sec.md", "Passwords")]

    report = evaluate_retrieval("fake", QUESTIONS, fake_search)
    assert report.questions == 2
    assert report.hit_rate[1] == 0.5
    assert report.hit_rate[3] == 1.0
    assert report.mrr == pytest.approx(0.75)
    assert report.misses == []
    empty = evaluate_retrieval("none", QUESTIONS, lambda q: [])
    assert empty.misses == ["q1", "q2"]


def answer(text: str, found: bool, source: str = "", heading: str = "") -> Answer:
    citations = [Citation(1, "c", source, heading, "s")] if source else []
    return Answer(question="q", text=text, found=found, citations=citations)


def test_answer_report_counts_each_kind_of_outcome() -> None:
    replies = {
        "leave?": answer("Employees get 24 days [1].", True, "leave.html", "Annual Leave"),
        "pass?": answer("Use a long one [1].", True, "other.md", "Other"),
        "dress?": answer("Suits [1].", True, "x.md", "X"),
    }
    report = evaluate_answers("test", QUESTIONS, lambda q: replies[q])
    assert report.answerable == 2
    assert report.unanswerable == 1
    assert report.answered_rate == 1.0
    assert report.fact_accuracy == 0.5
    assert report.citation_accuracy == 0.5
    assert report.refusal_accuracy == 0.0
    assert report.wrong_facts == ["q2"]
    assert report.wrong_citations == ["q2"]
    assert report.wrongly_answered == ["u1"]


def test_answer_report_counts_refusals_and_model_errors() -> None:
    def ask_fn(question: str) -> Answer:
        if question == "pass?":
            raise AnswerGenerationError("model call failed (X)")
        return answer("not found", False)

    report = evaluate_answers("test", QUESTIONS, ask_fn)
    assert report.errors == 1
    assert report.false_refusals == ["q1"]
    assert report.refusal_accuracy == 1.0


def test_report_renders_tables_and_failure_lists() -> None:
    only_leave = [result("leave.html", "Annual Leave")]
    retrieval = evaluate_retrieval("bm25", QUESTIONS, lambda q: only_leave)
    answers = evaluate_answers("offline", QUESTIONS, lambda q: answer("none", False))
    text = render_report([retrieval], [answers], {"rrf_k": "60"}, "now", 15)
    assert "| bm25 |" in text
    assert "| offline |" in text
    assert "- rrf_k: `60`" in text
    assert "Answerable but refused: q1, q2" in text