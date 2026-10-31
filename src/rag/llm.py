"""Gemma calls: embeddings via local Ollama (embeddinggemma), JSON chat via the hosted Gemma API with local fallback."""
import json
import os
import re
import time

import ollama
from dotenv import load_dotenv

load_dotenv()
EMBED_MODEL = os.getenv("EMBED_MODEL", "embeddinggemma")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "gemma3:4b")
API_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")  # hosted; gemma-4-31b-it is bigger but often 503
USE_API = bool(os.getenv("GEMINI_API_KEY")) and os.getenv("RAG_LLM", "api") == "api"
EMBED_DIMS = 768
API_TRIES = 3


def embed_doc(title: str, text: str) -> list[float]:
    # embeddinggemma expects task prefixes; docs and queries use different ones
    return ollama.embed(model=EMBED_MODEL, input=f"title: {title or 'none'} | text: {text}")["embeddings"][0]


def embed_query(query: str) -> list[float]:
    return ollama.embed(model=EMBED_MODEL, input=f"task: search result | query: {query}")["embeddings"][0]


def _parse(raw: str) -> dict:
    return json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()))


def _api_json(system: str, user: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    # Gemma has no system role on this API, so the rules go first in the user turn
    cfg = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
    for attempt in range(API_TRIES):
        try:
            return _parse(client.models.generate_content(
                model=API_MODEL, contents=f"{system}\n\n{user}", config=cfg).text)
        except Exception:  # noqa: BLE001 - API throws 500/503 under load; retry, then let the caller fall back
            if attempt == API_TRIES - 1:
                raise
            time.sleep(2 ** attempt)


def _local_json(system: str, user: str) -> dict:
    r = ollama.chat(model=LOCAL_MODEL, format="json", options={"temperature": 0},
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return _parse(r["message"]["content"])


def chat_json(system: str, user: str) -> dict:
    """Hosted Gemma first (callers pass already-redacted text); on any failure use local Gemma."""
    if USE_API:
        try:
            return _api_json(system, user)
        except Exception as e:  # noqa: BLE001
            print(f"[llm] hosted Gemma failed ({type(e).__name__}), using local {LOCAL_MODEL}")
    return _local_json(system, user)
