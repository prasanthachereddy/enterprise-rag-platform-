# ADR-0003: Paragraph-aware chunking

- Status: Accepted
- Context: Fixed-size character splitting cut words and separated questions from answers.
- Decision: Keep headings, group whole paragraphs up to the chunk size, split long paragraphs at
  sentence boundaries, and use word boundaries only as a last resort. Never split a word.
- Consequences: Chunks read naturally and cite well. The code is longer than a simple splitter.