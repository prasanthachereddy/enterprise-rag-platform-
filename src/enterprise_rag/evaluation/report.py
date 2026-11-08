"""Turn evaluation results into a Markdown report for docs/EVALUATION.md."""

from enterprise_rag.evaluation.runner import AnswerReport, RetrievalReport


def _ids(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def render_report(
    retrieval: list[RetrievalReport],
    answers: list[AnswerReport],
    settings_info: dict[str, str],
    generated_at: str,
    corpus_documents: int,
    golden_file: str = "data/eval/golden.jsonl",
) -> str:
    lines = [
        "# Evaluation results",
        "",
        f"Generated: {generated_at}. Corpus: {corpus_documents} synthetic documents. "
        f"Questions and labels are frozen in `{golden_file}` (ADR-0009).",
        "",
        "## Settings",
        "",
    ]
    lines += [f"- {name}: `{value}`" for name, value in settings_info.items()]
    if retrieval:
        count = retrieval[0].questions
        lines += [
            "",
            f"## Retrieval ({count} answerable questions)",
            "",
            "| Mode | Recall@3 | Recall@5 | Precision@3 | Precision@5 | MRR | Hit@1 | Hit@5 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in retrieval:
            lines.append(
                f"| {r.mode} | {r.recall[3]:.2f} | {r.recall[5]:.2f} | {r.precision[3]:.2f} | "
                f"{r.precision[5]:.2f} | {r.mrr:.2f} | {r.hit_rate[1]:.2f} | {r.hit_rate[5]:.2f} |"
            )
        lines += ["", "Questions with no relevant passage in the top 5:", ""]
        lines += [f"- {r.mode}: {_ids(r.misses)}" for r in retrieval]
    if answers:
        lines += [
            "",
            "## Answers",
            "",
            "| Answer mode | Answered | Key fact present | Right section cited "
            "| Unanswerable refused | Errors |",
            "|---|---|---|---|---|---|",
        ]
        for a in answers:
            lines.append(
                f"| {a.label} | {a.answered_rate:.0%} | {a.fact_accuracy:.0%} | "
                f"{a.citation_accuracy:.0%} | {a.refusal_accuracy:.0%} | {a.errors} |"
            )
        lines += [
            "",
            f"Rates use {answers[0].answerable} answerable and "
            f"{answers[0].unanswerable} unanswerable questions.",
            "",
        ]
        for a in answers:
            lines += [
                f"**{a.label}**",
                "",
                f"- Answerable but refused: {_ids(a.false_refusals)}",
                f"- Key fact missing from the answer: {_ids(a.wrong_facts)}",
                f"- Right section not cited: {_ids(a.wrong_citations)}",
                f"- Unanswerable but answered: {_ids(a.wrongly_answered)}",
                "",
            ]
    lines += [
        "## How to read this",
        "",
        "- A key-fact check is a substring match, so a correct answer worded differently "
        "(for example 2000 instead of 2,000) counts as a miss.",
        "- The corpus is small and synthetic. Treat the numbers as a regression check "
        "and a comparison between modes, not as production accuracy.",
    ]
    return "\n".join(lines) + "\n"