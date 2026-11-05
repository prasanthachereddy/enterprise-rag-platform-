"""The golden question set: fixed questions with the section that answers each one."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    question: str
    answerable: bool
    source: str = ""
    heading: str = ""
    must_contain: tuple[str, ...] = ()


def load_golden(path: Path) -> list[GoldenQuestion]:
    """Read one JSON object per line. Answerable questions name a section and key facts."""
    questions: list[GoldenQuestion] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            item = GoldenQuestion(
                id=raw["id"],
                question=raw["question"],
                answerable=bool(raw["answerable"]),
                source=raw.get("source", ""),
                heading=raw.get("heading", ""),
                must_contain=tuple(raw.get("must_contain", [])),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"golden file line {number} is invalid") from exc
        if item.id in seen:
            raise ValueError(f"duplicate question id: {item.id}")
        if item.answerable and not (item.source and item.must_contain):
            raise ValueError(f"{item.id}: an answerable question needs a source and key facts")
        if not item.answerable and (item.source or item.must_contain):
            raise ValueError(f"{item.id}: an unanswerable question must not name a source")
        seen.add(item.id)
        questions.append(item)
    if not questions:
        raise ValueError("golden file is empty")
    return questions