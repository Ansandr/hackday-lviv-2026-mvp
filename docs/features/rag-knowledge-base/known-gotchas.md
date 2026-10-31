# Known gotchas

- The vector index is eventually consistent: records inserted seconds ago may not be found, so dedup within one run can miss duplicates.
- `vectorSearchScore` for cosine is `(1 + cos) / 2`; thresholds are on that scale (0.95 ~ cos 0.9).
- embeddinggemma needs task prefixes (`title: ... | text: ...` for docs, `task: search result | query: ...` for queries); without them retrieval quality drops.
- Injection detection is a keyword heuristic; the real protection is that limits and permissions live in the agent's code.
- `gemma3:4b` sometimes returns a string instead of a list for `resolution_steps`; `validate()` handles it.
