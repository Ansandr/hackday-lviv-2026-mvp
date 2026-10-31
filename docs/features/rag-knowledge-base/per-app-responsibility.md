# Per-app responsibility

- **rag (this feature):** builds and searches the KB; owns redaction, injection rejection, judge gate, tenant filter.
- **agent:** calls `retrieve()`, cites `kb_id`, decides on tools; re-checks tool permissions and money limits in its own code (does not trust `action_tool` blindly).
- **ui:** shows the cited records and `ingest_log`; after a ticket is judged, sends it to `ingest_ticket()`.
