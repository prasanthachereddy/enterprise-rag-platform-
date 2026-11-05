"""Run the golden set against retrieval and against answers."""

from collections.abc import Callable
from dataclasses import dataclass, field

from enterprise_rag.answers.bedrock import AnswerGenerationError
from enterprise_rag.answers.models import Answer
from enterprise_rag.evaluation.golden import GoldenQuestion
from enterprise_rag.evaluation.metrics import (
    Key,
    hit_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from enterprise_rag.retrieval.models import SearchResult

DEFAULT_KS = (1, 3, 5)


@dataclass(frozen=True)
class RetrievalReport:
    mode: str
    questions: int
    recall: dict[int, float]
    precision: dict[int, float]
    hit_rate: dict[int, float]
    mrr: float
    misses: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnswerReport:
    label: str
    answerable: int
    unanswerable: int
    answered_rate: float
    fact_accuracy: float
    citation_accuracy: float
    refusal_accuracy: float
    errors: int
    false_refusals: list[str] = field(default_factory=list)
    wrong_facts: list[str] = field(default_factory=list)
    wrong_citations: list[str] = field(default_factory=list)
    wrongly_answered: list[str] = field(default_factory=list)


def _average(values: list[float]) -> float:
    return sum(values) / len(values)


def evaluate_retrieval(
    mode: str,
    questions: list[GoldenQuestion],
    search_fn: Callable[[str], list[SearchResult]],
    ks: tuple[int, ...] = DEFAULT_KS,
) -> RetrievalReport:
    """Score one retrieval mode on the answerable questions."""
    answerable = [q for q in questions if q.answerable]
    if not answerable:
        raise ValueError("no answerable questions to evaluate")
    scores: dict[str, list[float]] = {"rr": []}
    for k in ks:
        scores.update({f"recall{k}": [], f"precision{k}": [], f"hit{k}": []})
    misses: list[str] = []
    for question in answerable:
        relevant: set[Key] = {(question.source, question.heading)}
        results = search_fn(question.question)
        retrieved: list[Key] = [(r.source_filename, r.heading) for r in results]
        scores["rr"].append(reciprocal_rank(relevant, retrieved))
        for k in ks:
            scores[f"recall{k}"].append(recall_at_k(relevant, retrieved, k))
            scores[f"precision{k}"].append(precision_at_k(relevant, retrieved, k))
            scores[f"hit{k}"].append(hit_at_k(relevant, retrieved, k))
        if not relevant & set(retrieved[: max(ks)]):
            misses.append(question.id)
    return RetrievalReport(
        mode=mode,
        questions=len(answerable),
        recall={k: _average(scores[f"recall{k}"]) for k in ks},
        precision={k: _average(scores[f"precision{k}"]) for k in ks},
        hit_rate={k: _average(scores[f"hit{k}"]) for k in ks},
        mrr=_average(scores["rr"]),
        misses=misses,
    )


def evaluate_answers(
    label: str, questions: list[GoldenQuestion], ask_fn: Callable[[str], Answer]
) -> AnswerReport:
    """Score answers: found, key facts present, right section cited, unanswerable refused."""
    answered = facts = cited = refused = errors = 0
    false_refusals: list[str] = []
    wrong_facts: list[str] = []
    wrong_citations: list[str] = []
    wrongly_answered: list[str] = []
    for question in questions:
        try:
            answer = ask_fn(question.question)
        except AnswerGenerationError:
            errors += 1
            continue
        if not question.answerable:
            if answer.found:
                wrongly_answered.append(question.id)
            else:
                refused += 1
            continue
        if not answer.found:
            false_refusals.append(question.id)
            continue
        answered += 1
        lowered = answer.text.lower()
        if all(fact.lower() in lowered for fact in question.must_contain):
            facts += 1
        else:
            wrong_facts.append(question.id)
        expected = (question.source, question.heading)
        if any((c.source_filename, c.heading) == expected for c in answer.citations):
            cited += 1
        else:
            wrong_citations.append(question.id)
    answerable = sum(1 for q in questions if q.answerable)
    unanswerable = len(questions) - answerable
    return AnswerReport(
        label=label,
        answerable=answerable,
        unanswerable=unanswerable,
        answered_rate=answered / answerable if answerable else 0.0,
        fact_accuracy=facts / answerable if answerable else 0.0,
        citation_accuracy=cited / answerable if answerable else 0.0,
        refusal_accuracy=refused / unanswerable if unanswerable else 0.0,
        errors=errors,
        false_refusals=false_refusals,
        wrong_facts=wrong_facts,
        wrong_citations=wrong_citations,
        wrongly_answered=wrongly_answered,
    )