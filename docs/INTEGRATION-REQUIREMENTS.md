# Вимоги до інтеграції: RAG + mock SaaS + агент/UI

Статус: робочий документ інтеграції, 2026-10-31. Не є контрактом.
Усі форми даних, маршрути, інструменти й колекції визначає лише [CONTRACTS.md](CONTRACTS.md) (v1.1.0); тут є тільки посилання на його розділи.
Обґрунтування архітектури: [ARCHITECTURE.md](ARCHITECTURE.md). Правила: [../AGENTS.md](../AGENTS.md). Стан реалізації: [TEAM-SYNC.md](TEAM-SYNC.md).

## 0. Виправлені припущення

| Припущення | Як насправді за документами | Джерело |
|---|---|---|
| Mock SaaS це окремий сервер/API, до якого агент ходить по HTTP | Це **модуль усередині одного FastAPI-застосунку** (`src/backend/`) за сервісним інтерфейсом. HTTP-адаптер можна додати пізніше без змін інструментів агента | ARCHITECTURE.md, "Components and ownership" |
| Агент це окремий процес на іншій машині | Агент живе **в тому ж API-процесі**: API автентифікує, будує RequestContext, крутить tool loop і диспетчер | ARCHITECTURE.md, flow `UI -> API -> agent -> dispatcher -> mock / RAG -> MongoDB` |
| Mock SaaS у пам'яті (`fake_saas.py`), refund з лімітом суми, `create_venue_draft`, суддя, тон | Застаріло (notes/ лише історія). Стан у MongoDB, реальні записи без руху грошей; refund **не виконується**, лише `create_refund_request` зі статусом `pending_review`; venue onboarding, суддя й тон поза MVP | AGENTS.md "Product scope"; CONTRACTS.md "Migration from the initial sketch" |
| "Ліміти грошей" = поріг суми повернення | Порогу немає: сервер сам бере `amount_minor`/`currency` з платежу, лише повна сума, лише після окремого підтвердження, гроші не рухаються | CONTRACTS.md "Refund request within double_charge" |
| UI передає `tenant_id` | Ні. Tenant і actor лише з серверної сесії | CONTRACTS.md "Shared types and ownership" |
| Агент викликає дії (refund, resync) як інструменти | Модель має лише `propose_action`; виконання тільки через `POST /api/v1/actions/{id}/confirm` | CONTRACTS.md "Agent tool contracts" |

Різні машини потрібні тільки на час розробки. Спільна межа між людьми це **MongoDB Atlas** (одна база `support`) і контракти, а не мережеві виклики між модулями. Демо запускається як **один процес на одній машині**.

## 1. Карта компонентів і власники

| Компонент | Папка | Відповідальність | Власник |
|---|---|---|---|
| RAG | `src/rag/`, `data/docs/` | Ingestion, embeddinggemma, `kb_global`/`kb_tenant`, `retrieve()` з tenant prefilter, redaction | Andrii |
| Mock product + DB | `src/backend/` (ще немає) | Колекції promos, pos_state, checkouts, subscriptions, payments, refund_requests, logs, actions, audit_events; seed двох тенантів; read-методи для інструментів; транзакційне виконання 4 дій | Макс (denisk0m), включно з FastAPI `/api/v1` |
| API + агент | `src/agent/` (ще немає) | FastAPI, сесії/демо-логін, conversations, Gemma tool loop, диспетчер, `search_kb`-обгортка, confirm endpoint | Володя (Husiak-V); FastAPI-роути пише Макс |
| UI | `src/ui/` (ще немає) | Чат, questions, evidence, preview дії, кнопки confirm/reject, ActionResult | Володя (Husiak-V) |

CLAUDE.md перелічує тільки `src/agent`, `src/rag`, `src/ui`; README пропонує ще `src/backend/`. Хто пише mock і seed, не призначено.

## 2. Runtime-топологія

### Демо (ціль)

| Процес | Де | Порт | Примітка |
|---|---|---|---|
| FastAPI (`uvicorn`): API + агент + mock + `import src.rag` | демо-ноутбук | `8000` (пропозиція, Q3) | Один процес, один `MongoClient` на модуль |
| UI | віддається тим самим FastAPI як static | `8000` | Same-origin: без CORS, cookie-сесія + CSRF працюють просто (Q3) |
| Ollama | демо-ноутбук | `11434` | `embeddinggemma` (обов'язково для запитів RAG), `gemma3:4b` (fallback LLM) |
| MongoDB Atlas M0 | хмара | — | Спільна для всіх; fallback: `mongodb-atlas-local` на `27017` |
| Hosted Gemma (Gemini API) | хмара | — | Основна модель агента |

### Змінні середовища

Значення лише у власному `.env` кожного; `.env` не комітимо. Імена з `.env.example`, `docs/SETUP.md`, `docs/ATLAS-SETUP.md`, `src/rag/*.py`.

| Змінна | Хто читає | Значення / примітка |
|---|---|---|
| `GEMINI_API_KEY` | агент, RAG ingest | Hosted Gemma |
| `GEMMA_MODEL` | агент, RAG | `gemma-4-26b-a4b-it` за замовчуванням |
| `LOCAL_MODEL` | RAG (і агент, якщо повторить патерн) | `gemma3:4b`, офлайн fallback |
| `MONGODB_URI` / `MONGODB_DB` | RAG, backend, API | Atlas URI; `support`. Порожньо = локальний atlas-local |
| `EMBED_MODEL` | RAG | **Має бути `embeddinggemma`** (768 dims). У `.env.example` стоїть `nomic-embed-text`: це розходиться з індексом, виправити свій `.env` (Q4) |
| `OLLAMA_HOST` | бібліотека `ollama` (неявно) | Стандартно `http://localhost:11434`. Якщо на машині агента немає Ollama, вказати хост з embeddinggemma |
| `RAG_LLM` | RAG ingest | `api` або інше значення для лише локальної моделі |
| Демо-облікові дані двох тенантів | API | Імена змінних ще не визначені (Q5) |

## 3. Інтерфейси між частинами

### 3.1 Агент → RAG (`search_kb`)

**Рішення: in-process `from src.rag.retrieve import retrieve`, без HTTP.**

- Так вимагає контракт: CONTRACTS.md "RAG module interface" описує Python-функцію, ARCHITECTURE.md "Integration order" каже експонувати її через typed adapter.
- "Через різні машини" працює без HTTP: кожен запускає той самий репозиторій зі своїм `.env`, а дані спільні через Atlas. Потрібні тільки `MONGODB_URI` і Ollama з `embeddinggemma`.
- HTTP-сервіс RAG додав би ще один процес, порт, автентифікацію і проброс tenant без жодного виграшу для демо.

Вимоги до обгортки (власник: агент):

| # | Вимога | Посилання |
|---|---|---|
| R1 | Модель дає лише `query` і `intent`; `context` = RequestContext із сесії, `k` фіксує диспетчер (1-10) | CONTRACTS.md "RAG module interface" |
| R2 | Результат у конверті `{ok, data: {hits}, evidence_ids: [kb_id...], error}` | "Agent tool contracts" |
| R3 | `ValueError` (k, intent, tenant) → `ok:false`, `VALIDATION_ERROR`; недоступність Mongo/Ollama → `DEPENDENCY_UNAVAILABLE`, без вигаданої відповіді | "Frontend API v1", коди помилок |
| R4 | `kb_id` стають evidence `{kind:"kb", id, summary}` в AgentTurn; невідомі id не потрапляють у відповідь | "Agent tool contracts" |
| R5 | Текст хітів вставляється в промпт як дані в розмежувачах, не як інструкції | AGENTS.md "Safety invariants" |
| R6 | RequestContext: поки API не має свого, використовувати dataclass з `src/rag/retrieve.py` або будь-який об'єкт з `tenant_id` (Q6) | TEAM-SYNC.md, запис про merge RAG |

### 3.2 Агент → mock SaaS (read-інструменти і дії)

Агент **не ходить по HTTP** до mock: диспетчер викликає Python-методи `src/backend/` з RequestContext першим аргументом (ARCHITECTURE.md "Tenant isolation and authorization").

| Інструмент моделі | Метод backend (назви узгодити, Q2) | Контракт |
|---|---|---|
| `find_checkout`, `get_trace`, `get_promo_state`, `get_billing_context`, `validate_checkout` | read-методи, кожен фільтрує по `tenant_id` | "Agent tool contracts" |
| `propose_action` | backend валідує варіант, будує preconditions з поточних записів, зберігає в `actions` | "Agent tool contracts", "Action integrity" |
| (не інструмент) виконання | викликає лише confirm endpoint API | "Action integrity" |

Вимоги:
- Чотири варіанти дій рівно як у CONTRACTS.md; валідатор вичерпний, невідомий тип відхиляється.
- Назви подій у seed-логах збігаються з `data/docs/error-codes.md` (зокрема `SUBSCRIPTION_CREATE_RETRY`, `PROMO_CACHE_MISS`, `PROMO_LOOKUP_OK`, `POS_SYNC_FAILED`). Інакше RAG і логи "говорять різними словами".
- Seed: tenant_a з трьома happy path, tenant_b з подібними кодами для перевірки ізоляції (ARCHITECTURE.md "Demo data and acceptance"). Скрипт reset лише локально, не інструмент і не endpoint.

### 3.3 UI → API/агент

- Лише маршрути з CONTRACTS.md "Frontend API v1"; відповідь на повідомлення це `AgentTurn`.
- UI рендерить `questions`, `evidence`, `proposed_action` (усі 4 типи, включно з `create_refund_request`), `ActionResult`.
- Confirm/reject надсилає лише `{decision}`; параметри з UI не приймаються.
- Для refund request UI показує ID і "Awaiting review; funds have not been returned", стан розмови `unresolved`.
- Поки API немає, UI працює на JSON-прикладі з CONTRACTS.md як заглушці.

### 3.4 RAG ↔ mock

Прямого зв'язку немає. RAG не читає логи і стан продукту; backend не пише в `kb_*` (docs/features/rag-knowledge-base/per-app-responsibility.md). Єдина спільна річ: одна база `support` і словник кодів подій.

## 4. Безпека (перевіряється кодом, не промптом)

| # | Вимога | Де забезпечується |
|---|---|---|
| S1 | Tenant і actor лише з серверної сесії; модель і браузер не можуть їх задати | API |
| S2 | Кожен read/mutation/log/action/RAG-запит з `tenant_id`; чужий об'єкт повертає той самий `NOT_FOUND` | backend, RAG (prefilter у `retrieve`) |
| S3 | Текст клієнта, логи, KB-тексти це дані: розмежувачі в промпті + allowlist інструментів + серверна валідація | агент, диспетчер |
| S4 | Модель не отримує credentials, сирих Mongo-фільтрів, HTTP чи shell | диспетчер |
| S5 | Мутація лише після confirm точного preview; лише role `owner`; перевірка expiry і версій; action_id як ключ ідемпотентності; транзакція mutation+result+audit | API + backend |
| S6 | Гроші: сума і валюта з платежу, лише повна сума, `funds_moved:false`, unique `(tenant_id, payment_id)`; жодного виконання refund | backend |
| S7 | `retrieve` повертає лише `status: approved`; записи `kb_tenant` зі статусом `pending_review` (ticket extractions) **ніколи** не повертаються. Не плутати з `pending_review` у `refund_requests` | RAG (є тест) |
| S8 | Успіх лише з persisted стану і read-back верифікації; збій моделі/БД = явна помилка | агент, backend |
| S9 | Секрети й платіжні дані поза логами, промптом і комітами | усі |

## 5. Нефункціональні вимоги

| Тема | Вимога |
|---|---|
| Ліміти ходу | ≤ 8 tool calls, 1 спроба schema repair, дедлайн ходу (ARCHITECTURE.md). Пропозиція дедлайну: 30 с на хід (Q7) |
| Latency | Ціль для демо: відповідь ≤ 15 с; `search_kb` ≤ 2 с (локальний embed + 2 vector search). Не вимірювалось |
| Офлайн / збої | Hosted Gemma 500/503: retry, потім локальний `gemma3:4b` (патерн `src/rag/llm.py`). Atlas недоступний: `mongodb-atlas-local` + `python -m src.rag.ingest --reset` + seed. Embeddinggemma завжди локально |
| Демо-режим | Два seed-тенанти, детерміновані trace_id, reset-скрипт; записати резервне відео до 16:30 |
| Конкурентність | `409 CONVERSATION_BUSY` на паралельний хід; повторний confirm повертає збережений результат |
| Модель | Перевірити tool calling / strict JSON обраної Gemma до інтеграції; якщо native tool calling нестабільний, JSON-режим з валідацією схеми |

## 6. Definition of Done інтеграції

Інтеграція готова, коли на **одному запущеному процесі** з реальною MongoDB (Atlas або atlas-local) у UI проходить:

| # | Сценарій (CONTRACTS.md intents) | Критерій |
|---|---|---|
| D1 | `promo_not_applied` | Агент цитує логи `POS_SYNC_FAILED` і KB-документ, пропонує `resync_pos`, після confirm `validate_checkout` проходить, стан `resolved` |
| D2 | `double_charge` | Знаходить дубль, пропонує `cancel_duplicate_subscription` (retained лишається active) і **окремо** `create_refund_request`; результат `pending_review`, `funds_moved:false`, стан `unresolved`, UI не каже "гроші повернуто" |
| D3 | `promo_how_to` / створення | Питає відсутні поля, показує preview, після confirm повертає код, збережений у `promos` |
| D4 | Ізоляція | Сесія tenant_a не бачить даних, логів, KB чи дій tenant_b |
| D5 | Ін'єкція | Лог або повідомлення з інструкцією не викликає неперелічений інструмент і не обходить confirm |
| D6 | Ідемпотентність | Подвійний confirm дає одну мутацію; прострочений/stale preview падає без мутації |
| D7 | Тести | `python -m pytest tests` зелені; додано хоча б по одному тесту на D4-D6 від власників agent/backend |

Повний список приймальних перевірок: ARCHITECTURE.md "Demo data and acceptance" (1-15).

## 7. Порядок робіт до 17:00

1. Backend: seed + read-методи (контракти вже є). UI паралельно на прикладі AgentTurn.
2. Агент: read-інструменти + `search_kb` → AgentTurn без дій.
3. `propose_action` → confirm → виконання → read-back.
4. D1-D7, потім полірування. Заморозка коду 16:30.

## 8. Відкриті питання для команди

| # | Питання | Кому |
|---|---|---|
| Q1 | Хто пише `src/backend/` (mock + seed + дії)? CLAUDE.md його не перелічує. Хто власник агента й UI поіменно? | **Вирішено:** backend + FastAPI = Макс (denisk0m); agent + UI = Володя (Husiak-V); RAG = Andrii |
| Q2 | Сигнатури Python-методів backend для 5 read-інструментів і `propose_action`/`execute` (форми даних уже в CONTRACTS.md) | backend + агент |
| Q3 | Порт API (`8000`?) і чи UI віддається тим самим FastAPI, чи окремий dev-сервер (тоді потрібні CORS + CSRF) | агент + UI |
| Q4 | Виправити `EMBED_MODEL` у `.env.example` на `embeddinggemma`; привести ім'я користувача в URI (`app_reader`) до ATLAS-SETUP (`app_writer`/`rag_reader`) | Andrii |
| Q5 | Механізм демо-логіну і імена змінних для облікових даних двох тенантів | агент |
| Q6 | Де живе канонічний `RequestContext`: залишити в `src/rag/retrieve.py` чи перенести в API | агент + Andrii |
| Q7 | Дедлайн ходу агента і що показувати UI при `MODEL_UNAVAILABLE` | агент + UI |
| Q8 | RAG використовує той самий `MONGODB_URI`, що й API (writer). Контракт хоче read-only для retrieval: окрема змінна чи прийняти ризик на демо | Andrii |
| Q9 | Чи Atlas M0 уже створений і всі мають доступ (IP allowlist для мережі хакатону) | хто робить ATLAS-SETUP |
