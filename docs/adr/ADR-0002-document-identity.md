# ADR-0002: Content-derived document identity

- Status: Accepted
- Context: Uploading the same file twice must not create two different documents.
- Decision: Document ID is `doc-` plus the first 16 hex characters of the SHA-256 of the raw bytes.
- Consequences: Identical bytes give the same ID. The ID is a lookup key, not a permission check.