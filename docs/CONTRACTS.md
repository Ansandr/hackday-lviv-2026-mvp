# Contracts between parts (agent / RAG / UI)

All shapes are JSON. Field names are fixed; add optional fields freely, rename only after telling the team.

## Ticket (what the customer sends; produced by UI, stored by RAG)
```json
{
  "ticket_id": "TCK-1042",
  "tenant_id": "venue-chain-17",
  "venue_id": "venue-17-2",
  "channel": "chat",
  "created_at": "2026-10-31T12:40:00Z",
  "messages": [{"role": "customer", "text": "Промокод AUTUMN20 не проходить на касі", "ts": "..."}],
  "status": "open"
}
```
`status`: open | answered | action_done | proposed | escalated_human | dev_ticket | closed

## Analysis (RAG/tone -> agent, UI)
```json
{"intent": "promo_not_applied", "product_area": "promo", "sentiment": "negative",
 "aggression": 0.6, "urgency": 0.7, "churn_risk": 0.4, "injection_suspected": false}
```
`intent`: promo_how_to | promo_not_applied | venue_connect | double_charge | other

## Retrieval (RAG -> agent)
`retrieve(query, tenant_id, product_area=None, k=4) -> [kb_hit]`
```json
{"kb_id": "KB-PROMO-003", "type": "known_issue", "title": "...", "symptom": "...", "cause": "...",
 "resolution_steps": ["..."], "action_tool": "resync_pos", "score": 0.83}
```

## Agent result (agent -> UI, judge)
```json
{"reply": "...", "sources": ["KB-PROMO-003"],
 "actions": [{"tool": "check_promo", "args": {"code": "AUTUMN20"}, "result": {"status": "expired"}}],
 "escalation": null, "dev_ticket": null}
```
`escalation`: null | {"to": "human", "reason": "..."}; `dev_ticket`: null | {"title", "repro_steps", "logs", "priority"}

## Judge (RAG/judge -> UI, ingestion)
```json
{"ticket_id": "TCK-1042", "score": 4, "resolved": true, "policy_ok": true, "reason": "...", "tags": ["promo"]}
```
Only tickets with `score >= 4` and `policy_ok` are ingested into the knowledge base automatically.
