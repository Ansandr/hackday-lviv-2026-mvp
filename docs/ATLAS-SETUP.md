# Shared MongoDB Atlas setup (one person does this, ~10 min)

Collections, fields and indexes are defined in [CONTRACTS.md](CONTRACTS.md). This file is only the account setup.

## 1. Account and project
1. Open https://www.mongodb.com/cloud/atlas/register and sign up (Google or GitHub login is fine).
2. Skip or answer the onboarding survey. Create an organization (any name) and a project: `hackday-team14`.

## 2. Free cluster
1. In the project open **Database** (left menu "Clusters") -> **Create** / **Build a Database**.
2. Choose **Free (M0)**. Provider **AWS**, region **Frankfurt (eu-central-1)** (closest to Lviv). Name: `support`.
3. Click **Create Deployment**. Takes 1-3 minutes.
   M0 limits that matter: 512 MB storage, max 3 search/vector indexes (we need 2: global + tenant KB).

## 3. Database users (left menu: Security -> **Database Access** -> **Add New Database User**)
Authentication: Password. Use **Autogenerate Secure Password** and copy it immediately.

| User | Built-in role / privilege | Who uses it |
|---|---|---|
| `app_writer` | Specific Privileges -> `readWrite` on database `support` | API, mock product, RAG ingestion |
| `rag_reader` | Specific Privileges -> `read` on database `support` | RAG retrieval (contract: read-only) |

Send passwords to teammates only in a private chat. Never put them in the repo.

## 4. Network access (Security -> **Network Access** -> **Add IP Address**)
- Venue Wi-Fi IPs change, so for the hackathon click **Allow Access from Anywhere** (`0.0.0.0/0`) and set it as temporary (Atlas offers an expiry, choose 1 day).
- Mention in the pitch: next step is restricting to the app server IP (ARCHITECTURE.md requires it for production).

## 5. Connection string
1. **Database** -> cluster `support` -> **Connect** -> **Drivers** -> Driver: Python, latest version.
2. Copy the URI: `mongodb+srv://<user>:<password>@support.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=support`
3. Each teammate puts it in their own `.env`:
   ```
   MONGODB_URI=mongodb+srv://app_writer:<password>@support.xxxxx.mongodb.net/?retryWrites=true&w=majority
   MONGODB_DB=support
   ```
   If the password has special characters, URL-encode them (`@` -> `%40`, `:` -> `%3A`).

## 6. Give teammates UI access (optional)
Project -> **Project Access** (Access Manager) -> **Invite to Project** -> their emails, role **Project Read Only**.
They browse data in **Data Explorer**; their code still uses the DB users above.

## 7. Check
```
python -m src.rag.ingest --reset      # creates collections + vector indexes, loads curated docs
python -m src.rag.retrieve "Як створити промокод"
```
The vector index needs up to a minute to become queryable on first run; the script waits for it.

## Local fallback (no internet)
`docker run -d --name support-mongo -p 27017:27017 mongodb/mongodb-atlas-local` and leave `MONGODB_URI` empty
(default `mongodb://localhost:27017/?directConnection=true`). Same API, including `$vectorSearch`.
