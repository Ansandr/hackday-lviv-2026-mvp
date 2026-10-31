# Як запустити (демо до 17:00)

Основний варіант: версія Макса (`src/support` + `src/agent/runtime.py` + `src/backend/product.py`).
Попередня версія агента й мока (Andrii) збережена в гілці `archive/andrii-agent-mock`, у `main` її немає.

## 1. Одноразове налаштування (кожен на своїй машині)

```powershell
git pull origin main
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # потім заповнити .env, див. нижче
```

`.env` (у git не потрапляє). Значення Mongo і паролі беріть з приватного чату команди, **не з репозиторію**:

| Змінна | Навіщо | Звідки |
|---|---|---|
| `GEMINI_API_KEY` | хостована Gemma (агент, видобуток з тікетів) | свій ключ: https://aistudio.google.com/apikey |
| `GEMMA_MODEL` | модель агента, за замовчуванням `gemma-4-26b-a4b-it` | вже в `.env.example` |
| `MONGODB_URI`, `MONGODB_DB=support` | спільна база Atlas (RAG, режим `mongo`) | телеграм-чат команди |
| `EMBED_MODEL=embeddinggemma` | ембедінги для RAG | вже в `.env.example` |

## 2. Запуск застосунку (Макс, Володя, хто завгодно)

```powershell
./start-support.ps1
```

Відкрийте http://127.0.0.1:8000. У консолі друкуються **тимчасові коди входу**: `tenant_a: <код>` і `tenant_b: <код>`.
Вводьте код `tenant_a` (там дані для демо), `tenant_b` лише для перевірки ізоляції клієнтів.
Код діє, поки працює сервер, при перезапуску він інший. Щоб код був сталим, задайте `SUPPORT_ACCOUNTS` у `.env`.

За замовчуванням запуск **автономний**: стан у SQLite (`SUPPORT_PRODUCT_STORE=sqlite`), документи читаються з файлів `data/docs` (`SUPPORT_RAG_MODE=files`). Потрібен лише `GEMINI_API_KEY`.

### Режим з нашою базою знань (векторний RAG на Atlas) — для демо й номінації Gemma

Потрібно додатково: Ollama запущена, модель `embeddinggemma` завантажена (`ollama pull embeddinggemma`), база Atlas наповнена (див. п. 3).

```powershell
$env:SUPPORT_RAG_MODE = "atlas"
./start-support.ps1
```

Перевірка, що RAG бачить базу: `python -m src.rag.retrieve "Як створити промокод"` має вивести 3–4 записи зі `score`.

## 3. База знань (Andrii)

```powershell
python -m src.rag.ingest --reset
```

Створює колекції `kb_global`, `kb_tenant` та векторні індекси, завантажує `data/docs` і тікети з `data/tickets`.
Запускати лише коли змінились документи. Інструкція з Atlas: [ATLAS-SETUP.md](ATLAS-SETUP.md).

## 4. Скинути стан мока між показами

```powershell
$env:SUPPORT_PRODUCT_STORE = "sqlite"
python -m src.backend.seed --reset
```

## 5. Тести

```powershell
python -m pytest tests
```

Живі RAG-тести (`test_rag_live.py`) потребують Mongo і Ollama, без них вони пропускаються.

## 6. Сценарії для демо (вводити в чат)

1. `Промокод AUTUMN20 не проходить на касі venue_01` → докази з журналів, підтвердити синхронізацію.
2. `З нас двічі списали гроші за підписку business_01` → підтвердити скасування дубліката, потім попросити запит на повернення.
3. `Створи промокод для venue_01: знижка 15%, з сьогодні до 31 грудня 2026, максимум 50 використань` → перегляд, підтвердження.

## 7. Хто що запускає

| Роль | Що | Команда |
|---|---|---|
| Демо-ноутбук (один) | сервер для пітчу | `./start-support.ps1` (+ `SUPPORT_RAG_MODE=atlas`) |
| Andrii | RAG, база Atlas, перевірка пошуку | `python -m src.rag.ingest`, `python -m src.rag.retrieve "…"` |
| Макс | API та інтерфейс | `./start-support.ps1`, правки в `src/support`, `src/ui` |
| Усі | перед пушем | `git fetch`, `git pull --rebase origin main`, `python -m pytest tests` |

## Якщо щось не працює

- `Gemma unavailable` → перевірте `GEMINI_API_KEY` у `.env`; без ключа потрібна Ollama і `SUPPORT_LLM=local`.
- Хостована Gemma інколи повертає 500/503 → повторіть запит.
- RAG не знаходить записів у режимі `atlas` → Ollama не запущена, або база порожня (п. 3), або вашої IP немає у списку Atlas.
- Порт 8000 зайнятий → `$env:SUPPORT_PORT = "8001"`.
