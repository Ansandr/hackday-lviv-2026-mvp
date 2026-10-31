"""Local Gemma calls via Ollama: embeddings (embeddinggemma) and JSON chat."""
import json
import os

import ollama
from dotenv import load_dotenv

load_dotenv()
EMBED_MODEL = os.getenv("EMBED_MODEL", "embeddinggemma")
CHAT_MODEL = os.getenv("LOCAL_MODEL", "gemma3:4b")
EMBED_DIMS = 768


def embed_doc(title: str, text: str) -> list[float]:
    # embeddinggemma expects task prefixes; docs and queries use different ones
    return ollama.embed(model=EMBED_MODEL, input=f"title: {title or 'none'} | text: {text}")["embeddings"][0]


def embed_query(query: str) -> list[float]:
    return ollama.embed(model=EMBED_MODEL, input=f"task: search result | query: {query}")["embeddings"][0]


def chat_json(system: str, user: str, retries: int = 1) -> dict:
    """Ask Gemma for a JSON object; one retry on invalid JSON, then raise."""
    for attempt in range(retries + 1):
        r = ollama.chat(model=CHAT_MODEL, format="json", options={"temperature": 0},
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        try:
            return json.loads(r["message"]["content"])
        except json.JSONDecodeError:
            if attempt == retries:
                raise
