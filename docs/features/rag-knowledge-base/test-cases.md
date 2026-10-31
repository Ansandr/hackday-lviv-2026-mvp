# Test cases (from docs and CONTRACTS.md v1; engineer reviews)

| id | given | when | then | source |
|---|---|---|---|---|
| TC-01 | KB ingested | retrieve "Як створити промокод" as tenant_a | a `promo_how_to` record in top 2 | FEATURE AC1 |
| TC-02 | KB ingested | retrieve "Промокод не проходить на касі" as tenant_a | a `promo_not_applied` record in top 2 | FEATURE AC2 |
| TC-03 | KB ingested | retrieve "Двічі списали гроші за підписку" as tenant_a | a `double_charge` record in top 2 | FEATURE AC3 |
| TC-04 | ticket text contains injection | ingest_ticket | logged `rejected`, nothing written | security |
| TC-05 | tickets ingested | retrieve any scenario query, k=10 | no `pending_review` record returned | CONTRACTS: auto publication disabled |
| TC-06 | ticket contains phone/email/card | ingest_ticket | redacted before model and storage | business-context |
| TC-07 | model returns unknown intent or tool | validate | intent -> other, tool -> null | integration-points |
| TC-08 | approved kb_tenant record of tenant_b | retrieve as tenant_a | not returned (returned for tenant_b) | CONTRACTS: tenant boundary |
| TC-09 | k=0 or 11, unknown intent, empty tenant | retrieve | ValueError | CONTRACTS: reject k outside 1..10 |
| TC-10 | KB ingested | inspect kb_global | no tenant_id, no ticket-derived ids | CONTRACTS: no customer-derived content |
| TC-11 | intent filter given | retrieve with intent=promo_how_to | only that intent returned | CONTRACTS |
| TC-12 | hit returned | inspect keys | exactly kb_id, text, score | CONTRACTS KbHit |

Automated offline: TC-04 (detector), TC-06, TC-07, TC-09 in tests/test_rag_offline.py.
Automated live: TC-01..03, 05, 08, 10..12 in tests/test_rag_live.py (needs Mongo + Ollama).
