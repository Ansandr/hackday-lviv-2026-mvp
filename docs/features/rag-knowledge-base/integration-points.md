# Integration points

- **agent (`search_kb` tool):** calls `retrieve(query, context, intent, k)`, wraps the hits in the standard tool-result envelope; `kb_id`s become evidence ids.
- **API:** supplies RequestContext (tenant from the verified session). RAG trusts only `context.tenant_id`.
- **action types:** extracted `action_tool` is limited to the `propose_action` variants (`resync_pos`, `cancel_duplicate_subscription`, `create_promo`) and only appears inside text; RAG never executes actions.
