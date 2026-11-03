# ADR-0010: Evidence check before answering

- Status: Accepted
- Context: Vector search always returns results, so a similarity score cannot show that a question is unanswerable.
- Decision: Before answering, count how many of the question's content words appear in a passage (query coverage). If no passage reaches MIN_QUERY_COVERAGE, refuse with a fixed not-found message.
- Consequences: Refusals are predictable and testable offline. The check is lexical, so synonyms and word forms can cause false refusals; Phase 5 measures this and the threshold can be tuned.