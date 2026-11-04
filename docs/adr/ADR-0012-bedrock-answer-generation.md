# ADR-0012: Bedrock answer generation

- Status: Accepted
- Context: Offline answers only quote sentences. A model can phrase an answer, but it can invent facts and costs money per call.
- Decision: Use Claude Haiku 4.5 through the Bedrock Converse API with the India inference profile. Run the evidence check first and call the model only when evidence exists. Cap output at 400 tokens, temperature 0, one call per question. Treat passages as untrusted data. Refuse any reply that is NOT_FOUND or has no valid citation. Keep ANSWER_MODE=offline as the default.
- Consequences: Unanswerable questions cost nothing. Tests use fakes, so the repository tests pass without AWS access. The model sees document text, so only synthetic or public documents are used.