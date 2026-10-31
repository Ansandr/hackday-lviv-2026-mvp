# Checks

See tests/test_support.py: tenant isolation, all four actions, question flow, no execution before confirmation, repeat/concurrent confirmation, stale/rejected previews, viewer restrictions, message deduplication, timeout recovery, typed allowlist, adapter headers, persistence and UI assets.
Live integration with the real agent/SaaS and MongoDB is a separate outstanding check.

Browser regressions: tests/support_ui.browser.cjs holds the API response, verifies immediate rendering and empty composer, preserves a new draft, retries failed requests with the same ID, and handles failed history refresh after successful submission. Requires Playwright and a running local server; uses isolated API fixtures.
