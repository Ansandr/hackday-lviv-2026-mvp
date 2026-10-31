# Known gotchas

- Vector indexes are eventually consistent: records inserted seconds ago may not be found, so dedup within one run can miss duplicates and tests must wait.
- `vectorSearchScore` for cosine is `(1 + cos) / 2`; thresholds are on that scale (0.95 ~ cos 0.9). Scores from the two collections are comparable because both use the same model and similarity.
- embeddinggemma needs task prefixes (`title: ... | text: ...` for docs, `task: search result | query: ...` for queries).
- Injection detection is a keyword heuristic; the real protection is server-side validation and confirmation in the agent.
- The hosted Gemma API intermittently returns 500/503; `chat_json` retries, then falls back to local `gemma3:4b`.
- Changing the embedding model requires re-embedding everything and matching the index dimension.
