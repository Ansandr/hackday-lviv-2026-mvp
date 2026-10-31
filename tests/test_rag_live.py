"""Live acceptance checks (docs/features/rag-knowledge-base/test-cases.md). Needs Mongo + Ollama and a prior
`python -m src.rag.ingest --reset`. Skipped when services are down."""
import time

import pytest

try:
    from src.rag.db import kb_global, kb_tenant
    from src.rag.llm import EMBED_MODEL, embed_doc
    from src.rag.retrieve import RequestContext, retrieve
    kb_global.database.client.admin.command("ping")
except Exception:  # noqa: BLE001 - any connection problem means "skip"
    pytest.skip("Mongo/Ollama not available", allow_module_level=True)

A, B = RequestContext("tenant_a"), RequestContext("tenant_b")


def _intents(hits):
    ids = [h["kb_id"] for h in hits]
    docs = {d["kb_id"]: d["intent"] for c in (kb_global, kb_tenant) for d in c.find({"kb_id": {"$in": ids}})}
    return [docs[i] for i in ids]


def test_tc01_promo_how_to():
    hits = retrieve("Як створити промокод", A)
    assert "promo_how_to" in _intents(hits[:2]), hits


def test_tc02_promo_not_applied():
    hits = retrieve("Промокод не проходить на касі", A)
    assert "promo_not_applied" in _intents(hits[:2]), hits


def test_tc03_double_charge():
    hits = retrieve("Двічі списали гроші за підписку", A)
    assert "double_charge" in _intents(hits[:2]), hits


def test_intent_filter_only_returns_that_intent():
    assert set(_intents(retrieve("промокод", A, intent="promo_how_to"))) == {"promo_how_to"}


def test_hits_have_contract_shape():
    hit = retrieve("промокод", A, k=1)[0]
    assert set(hit) == {"kb_id", "text", "score"} and isinstance(hit["text"], str)


def test_pending_review_never_returned():
    pending = {d["kb_id"] for d in kb_tenant.find({"status": "pending_review"})}
    assert pending, "seed should create pending ticket records"
    for q in ("Промокод не проходить на касі", "Двічі списали за підписку", "Як створити промокод"):
        assert not pending & {h["kb_id"] for h in retrieve(q, A, k=10)}


def test_tenant_isolation():
    text = "Секретна інструкція tenant_b: промокод ZEBRA99 на касі"
    kb_tenant.insert_one({"tenant_id": "tenant_b", "kb_id": "KBT-ISO-TEST", "title": "iso", "text": text,
                          "embedding": embed_doc("iso", text), "embedding_model": EMBED_MODEL,
                          "intent": "promo_not_applied", "status": "approved"})
    try:
        deadline = time.time() + 30  # vector index is eventually consistent
        while "KBT-ISO-TEST" not in {h["kb_id"] for h in retrieve(text, B, k=10)}:
            assert time.time() < deadline, "tenant_b record never indexed"
            time.sleep(1)
        assert "KBT-ISO-TEST" not in {h["kb_id"] for h in retrieve(text, A, k=10)}
    finally:
        kb_tenant.delete_one({"kb_id": "KBT-ISO-TEST"})


def test_global_has_no_tenant_or_customer_content():
    assert kb_global.count_documents({"tenant_id": {"$exists": True}}) == 0
    assert kb_global.count_documents({"kb_id": {"$regex": "^KBT-"}}) == 0
