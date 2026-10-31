"""retrieve(query, tenant_id, product_area, k) -> kb hits (see docs/CONTRACTS.md)."""
import sys

from .db import vector_search
from .llm import embed_query
from .sanitize import redact

FIELDS = ["kb_id", "type", "title", "symptom", "cause", "resolution_steps", "action_tool", "score"]


def retrieve(query: str, tenant_id: str, product_area: str | None = None, k: int = 4) -> list[dict]:
    # tenant pre-filter is a security boundary: never drop it
    filters = {"status": "approved", "tenant_scope": {"$in": ["global", tenant_id]}}
    if product_area:
        filters["product_area"] = product_area
    hits = vector_search(embed_query(redact(query)), filters, k)
    return [{f: h.get(f) for f in FIELDS} for h in hits]


if __name__ == "__main__":
    for hit in retrieve(" ".join(sys.argv[1:]) or "промокод не проходить на касі", "venue-chain-17"):
        print(f"{hit['score']:.3f}  {hit['kb_id']}  {hit['title']}")
