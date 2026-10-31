"""Live acceptance checks (docs/features/rag-knowledge-base/test-cases.md). Needs Mongo + Ollama and a prior
`python -m src.rag.ingest --reset`. Skipped when services are down."""
import pytest

try:
    from src.rag.db import kb
    from src.rag.retrieve import retrieve
    kb.database.client.admin.command("ping")
except Exception:  # noqa: BLE001 - any connection problem means "skip"
    pytest.skip("Mongo/Ollama not available", allow_module_level=True)

T = "venue-chain-17"


def test_tc01_promo_how_to():
    hits = retrieve("Як створити промокод", T)
    assert any(h["title"] and "створ" in h["title"].lower() for h in hits[:2]), hits


def test_tc02_promo_not_applied_has_tool():
    hits = retrieve("Промокод не проходить на касі", T)
    assert {h["action_tool"] for h in hits} & {"resync_pos", "check_promo", "extend_promo"}, hits


def test_tc03_double_charge_policy():
    hits = retrieve("Двічі списали гроші за підписку", T)
    assert any("2000" in " ".join(h["resolution_steps"] or []) for h in hits[:2]), hits


def test_tc05_pending_never_returned():
    assert kb.count_documents({"source_ids": "TCK-1012", "status": "approved"}) == 0


def test_tc04_injection_not_in_kb():
    assert kb.count_documents({"source_ids": {"$in": ["TCK-1013", "TCK-1014"]}}) == 0
