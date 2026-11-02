# ADR-0001: Local-first development

- Status: Accepted
- Context: Cloud resources cost money before the application is proven.
- Decision: Build and test ingestion, retrieval and answers locally first, then add AWS.
- Consequences: Debugging is faster and cheaper; cloud behaviour must still be verified later.
