"""Retrieval metrics. A passage is identified by (file name, section heading)."""

Key = tuple[str, str]


def recall_at_k(relevant: set[Key], retrieved: list[Key], k: int) -> float:
    """Share of the relevant sections that appear in the top k."""
    if not relevant:
        return 0.0
    return len(relevant & set(retrieved[:k])) / len(relevant)


def precision_at_k(relevant: set[Key], retrieved: list[Key], k: int) -> float:
    """Share of the top k slots that hold a relevant passage."""
    return sum(1 for key in retrieved[:k] if key in relevant) / k


def hit_at_k(relevant: set[Key], retrieved: list[Key], k: int) -> float:
    """1.0 if any relevant section is in the top k, else 0.0."""
    return 1.0 if relevant & set(retrieved[:k]) else 0.0


def reciprocal_rank(relevant: set[Key], retrieved: list[Key]) -> float:
    """1 / rank of the first relevant passage, or 0.0 if none was retrieved."""
    for rank, key in enumerate(retrieved, start=1):
        if key in relevant:
            return 1 / rank
    return 0.0