# Integration points

- **support-agent:** consumes `retrieve()` output (`kb_hit` in docs/CONTRACTS.md). Tool names in `action_tool` must match the agent's tools: `check_promo`, `extend_promo`, `resync_pos`, `create_venue_draft`, `get_invoices`, `refund`. Adding a tool = update `TOOLS` in `src/rag/ingest.py`.
- **judge:** its output (`score`, `policy_ok`) decides `approved` vs `pending_review`.
- **support-ui:** calls `ingest_ticket(ticket_with_judge)` after closing a ticket.
