"""MongoDB connection and vector indexes for kb_global / kb_tenant (docs/CONTRACTS.md, MongoDB contracts).

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
_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/?directConnection=true"))
db = _client[os.getenv("MONGODB_DB", "support")]
kb_global, kb_tenant, ingest_log = db["kb_global"], db["kb_tenant"], db["ingest_log"]

# global docs have no tenant_id, so their index cannot filter on it
INDEXES = {"kb_global": ["status", "intent"], "kb_tenant": ["tenant_id", "status", "intent"]}
INDEX = "kb_vector"


def ensure_indexes(timeout: int = 120) -> None:
    """Create both vector indexes once and wait until they are queryable."""
    for name, filters in INDEXES.items():
        coll = db[name]
        if name not in db.list_collection_names():
            db.create_collection(name)
        if INDEX not in {i["name"] for i in coll.list_search_indexes()}:
            coll.create_search_index(SearchIndexModel(name=INDEX, type="vectorSearch", definition={"fields": [
                {"type": "vector", "path": "embedding", "numDimensions": EMBED_DIMS, "similarity": "cosine"},
                *({"type": "filter", "path": f} for f in filters),
            ]}))
    deadline = time.time() + timeout
    for name in INDEXES:
        while not next(iter(db[name].list_search_indexes(INDEX)), {}).get("queryable"):
            if time.time() > deadline:
                raise TimeoutError(f"vector index {name}.{INDEX} not ready")
            time.sleep(2)


def vector_search(coll, vector: list[float], filters: dict, k: int = 4) -> list[dict]:
    return list(coll.aggregate([
        {"$vectorSearch": {"index": INDEX, "path": "embedding", "queryVector": vector,
                           "numCandidates": k * 20, "limit": k, "filter": filters}},
        {"$project": {"embedding": 0, "_id": 0, "score": {"$meta": "vectorSearchScore"}}},
    ]))
