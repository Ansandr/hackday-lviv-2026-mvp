# Per-app responsibility

- **rag (this feature):** builds and searches `kb_global` / `kb_tenant`; owns redaction, injection rejection, allowlists, tenant pre-filter.
- **agent / API:** builds RequestContext from the verified session and passes it to `retrieve()` via the `search_kb` tool; the model supplies only query and intent. Cites `kb_id` as evidence.
- **backend:** owns logs and product state; RAG does not read or write them.
- **ui:** shows `kb` evidence items returned in AgentTurn.
