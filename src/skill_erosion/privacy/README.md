# Privacy and observability boundary

Implement allowlisted event logging before ingesting real data. Log operation,
duration, result status, and opaque request IDs, never raw response text,
embeddings, full tool arguments, or exception payloads containing submissions.
Teacher-facing summaries must not expose raw student answers through logs.

Authentication, role checks, consent, retention/deletion, and deployment security
are future work. The local scaffold is for synthetic data only. MCP binding to
127.0.0.1 is a development default, not an authorization mechanism.
