"""MongoDB connection and the vector index for the knowledge base.

Local: docker run -d --name support-mongo -p 27017:27017 mongodb/mongodb-atlas-local
Cloud: put an Atlas URI in MONGODB_URI.
"""
import os
import time

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel

from .llm import EMBED_DIMS

load_dotenv()
INDEX = "kb_vector"
FILTER_FIELDS = ["status", "tenant_scope", "product_area", "type"]

_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/?directConnection=true"))
db = _client[os.getenv("MONGODB_DB", "support")]
kb, tickets, ingest_log = db["kb"], db["tickets"], db["ingest_log"]


def ensure_index(timeout: int = 120) -> None:
    """Create the vector index once and wait until it is queryable."""
    if INDEX not in {i["name"] for i in kb.list_search_indexes()}:
        if "kb" not in db.list_collection_names():
            db.create_collection("kb")
        kb.create_search_index(SearchIndexModel(name=INDEX, type="vectorSearch", definition={"fields": [
            {"type": "vector", "path": "embedding", "numDimensions": EMBED_DIMS, "similarity": "cosine"},
            *({"type": "filter", "path": f} for f in FILTER_FIELDS),
        ]}))
    deadline = time.time() + timeout
    while not next(iter(kb.list_search_indexes(INDEX)), {}).get("queryable"):
        if time.time() > deadline:
            raise TimeoutError(f"vector index {INDEX} not ready")
        time.sleep(2)


def vector_search(vector: list[float], filters: dict, k: int = 4) -> list[dict]:
    return list(kb.aggregate([
        {"$vectorSearch": {"index": INDEX, "path": "embedding", "queryVector": vector,
                           "numCandidates": k * 20, "limit": k, "filter": filters}},
        {"$project": {"embedding": 0, "_id": 0, "score": {"$meta": "vectorSearchScore"}}},
    ]))
