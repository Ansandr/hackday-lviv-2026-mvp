"""retrieve(query, context, intent=None, k=4) -> list[KbHit] (docs/CONTRACTS.md, RAG module interface)."""
import sys
from dataclasses import dataclass

from .db import kb_global, kb_tenant, vector_search
from .llm import embed_query
from .sanitize import redact

INTENTS = {"promo_how_to", "promo_not_applied", "double_charge", "other"}


@dataclass(frozen=True)
class RequestContext:
    """Server-derived identity; the dispatcher builds it, the model never does."""
    tenant_id: str
    actor_id: str = ""
    role: str = "viewer"
    request_id: str = ""


def retrieve(query: str, context, intent: str | None = None, k: int = 4) -> list[dict]:
    if not 1 <= k <= 10:
        raise ValueError("k must be between 1 and 10")
    if intent is not None and intent not in INTENTS:
        raise ValueError(f"unknown intent {intent!r}")
    tenant_id = context["tenant_id"] if isinstance(context, dict) else context.tenant_id
    if not tenant_id:
        raise ValueError("context.tenant_id is required")
    base = {"status": "approved", **({"intent": intent} if intent else {})}
    vec = embed_query(redact(query))
    # tenant pre-filter is a security boundary: never drop it
    hits = vector_search(kb_global, vec, base, k) + vector_search(kb_tenant, vec, {**base, "tenant_id": tenant_id}, k)
    hits.sort(key=lambda h: h["score"], reverse=True)
    return [{"kb_id": h["kb_id"], "text": h["text"], "score": h["score"]} for h in hits[:k]]


if __name__ == "__main__":
    for hit in retrieve(" ".join(sys.argv[1:]) or "промокод не проходить на касі", RequestContext("tenant_a")):
        print(f"{hit['score']:.3f}  {hit['kb_id']}  {hit['text'][:70]!r}")
