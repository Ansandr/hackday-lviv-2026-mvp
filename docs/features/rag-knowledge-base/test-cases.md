# Test cases (from docs, written before checking the code; engineer reviews)

| id | given | when | then | source |
|---|---|---|---|---|
| TC-01 | KB ingested from data/ | retrieve("Як створити промокод", any tenant) | a `promo` doc record about creating a promo code is in top 2 | FEATURE.md AC1 |
| TC-02 | KB ingested | retrieve("Промокод не проходить на касі") | top 4 contain `action_tool` in {resync_pos, check_promo, extend_promo} | FEATURE.md AC2 |
| TC-03 | KB ingested | retrieve("Двічі списали за підписку") | refund policy (limit 2000 UAH) in top 2 | FEATURE.md AC3, business-context |
| TC-04 | ticket text contains "Ignore previous instructions" | ingest_ticket | logged `rejected`, nothing written to kb | FEATURE.md AC4 |
| TC-05 | ticket with judge score 2 / policy_ok false (TCK-1012) | ingest_ticket, then retrieve its topic | record is `pending_review` and never returned | business-context, AC4 |
| TC-06 | ticket contains phone, email, card number | ingest_ticket | no digits of card/phone or email in any kb field | business-context, AC5 |
| TC-07 | model returns unknown `action_tool` / area | validate | tool -> null, area -> other | integration-points |
| TC-08 | record with `tenant_scope` = tenant A | retrieve as tenant B | record not returned | business-context |
| TC-09 | two tickets describe the same issue | ingest both | one record, `occurrences` = 2 (may fail inside one run, see known-gotchas) | end-to-end-flow 4 |

Automated now: TC-04 (detector), TC-06, TC-07 in tests/test_rag_offline.py. TC-01..03, 05 run live in tests/test_rag_live.py (needs Mongo + Ollama).
Open question: TC-08 has no tenant-scoped records yet, because all seed ticket records are `global`. Should ticket-derived records be scoped to their tenant?
