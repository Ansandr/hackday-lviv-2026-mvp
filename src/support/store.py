"""SQLite persistence for the independently runnable support service (single worker)."""
import json
import sqlite3
import threading


class Store:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, tenant TEXT, body TEXT, PRIMARY KEY(kind,id))")
        self.db.execute("CREATE INDEX IF NOT EXISTS tenant_records ON records(kind,tenant)")
        self.db.commit()

    def get(self, kind, key, tenant):
        with self.lock:
            row = self.db.execute("SELECT body FROM records WHERE kind=? AND id=? AND tenant=?", (kind, key, tenant)).fetchone()
            return json.loads(row[0]) if row else None

    def put(self, kind, key, tenant, value):
        with self.lock, self.db:
            self.db.execute("INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body", (kind, key, tenant, json.dumps(value, ensure_ascii=False)))

    def list(self, kind, tenant):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute("SELECT body FROM records WHERE kind=? AND tenant=? ORDER BY rowid DESC", (kind, tenant))]
