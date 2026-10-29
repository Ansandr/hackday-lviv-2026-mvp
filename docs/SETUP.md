# Gemma cheatsheet + full setup

## 1. Models
- Hosted (Gemini API) IDs: `gemma-4-31b-it`, `gemma-4-26b-a4b-it` (A4B = MoE, cheaper/faster; docs recommend it as default).
- Gemma 4: E2B/E4B (text+image+audio, phones/laptops), 12B (+audio), A4B and 31B (text+image).
- Gemma 3/3n: 270M-27B. Specialised: FunctionGemma, EmbeddingGemma, MedGemma, PaliGemma, ShieldGemma, TranslateGemma, CodeGemma.
- Capabilities: chat, function calling, image/video/audio understanding, thinking mode.
- Licence: Apache 2.0 (Gemma 4, per MLH page).
- Other ways to run: LM Studio, llama.cpp, MLX, HF Transformers, Unsloth (LoRA/QLoRA), Vertex AI.
- Caveat: ai.google.dev docs are marked deprecated -> newer docs at gemma.ai.

## 2. Setup checklist (do before Sat 2026-10-31)
### A. Python env (project folder)
```
cd <your clone of this repo>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### B. Hosted API key (Google AI Studio)
1. Sign in at https://aistudio.google.com/api-keys with a PERSONAL Google account (org/university accounts may block key creation). Accept the ToS.
2. Project: every key lives in a Google Cloud project.
   - No Cloud account yet -> a default project is auto-created; use it.
   - Already have Google Cloud -> no default: Dashboard -> Projects -> Import projects -> pick/create a fresh project.
   - Name suggestion: `hackday-lviv-2026`.
3. Create API key in that project. Name: `hackday-lviv-laptop` (unnamed keys show as "unknown" on the Usage page). One key is enough; teammates get their own (`hackday-lviv-<name>`).
4. Key type: AI Studio now issues "auth" keys (since 2026-05-28). Old "Standard" keys must be restricted to the Gemini API only.
5. "No permission to create a key" -> you're on an org account; switch to a personal one.
6. Save the key:
   ```
   copy .env.example .env   (macOS/Linux: cp)
   ```
   then edit `.env`: `GEMINI_API_KEY=<key>` (and optionally `GEMMA_MODEL=...`). `.env` is git-ignored. Never commit/share the key; if leaked, delete it on the keys page and recreate.
7. Verify: `python src/hello_gemma.py` -> should print a greeting.
   - Model not found -> check exact Gemma IDs in AI Studio model list, set `GEMMA_MODEL`.
   - 429 / quota -> wait a minute, shorten prompts, cache responses. Free-tier limits: see Pricing page.

### C. Local/offline fallback (Ollama)
1. Install from https://ollama.com/download (Windows installer).
2. `ollama pull gemma3:4b` (or a Gemma 4 tag from https://ollama.com/library/gemma4 if it exists; smaller = faster on a laptop).
3. `ollama list` -> put the exact tag into `MODEL` in `src/hello_local.py`.
4. Verify: `python src/hello_local.py`.
5. Ollama also serves an HTTP API on http://localhost:11434 (handy from any language).

### D. Day-of
- Charge laptop, bring charger. Download the Ollama model at home, not on venue wifi.
- Keep `.env` out of any repo you push (check `git status` before the first commit).

## 3. Code snippets
Python (hosted):
```python
from google import genai
client = genai.Client()  # reads GEMINI_API_KEY / GOOGLE_API_KEY (GOOGLE_API_KEY wins if both set)
r = client.models.generate_content(model="gemma-4-26b-a4b-it", contents="Hello")
print(r.text)
```
JavaScript: `npm i @google/genai`
```js
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI();
const r = await ai.models.generateContent({ model: "gemma-4-26b-a4b-it", contents: "Hello" });
console.log(r.text);
```
REST: `POST https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent` with the key in the `x-goog-api-key` header.

## 4. Links
- https://ai.google.dev/gemma/docs/get_started
- https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
- https://ai.google.dev/gemini-api/docs/api-key
- https://github.com/google-gemma/cookbook  (tutorials/, apps/, experiments/, responsible/)
- https://www.mlh.com/partners/gemma
- Keys: https://aistudio.google.com/api-keys
