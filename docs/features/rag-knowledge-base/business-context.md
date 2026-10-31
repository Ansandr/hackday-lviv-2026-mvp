# Business context

- Customers are venue owners using our SaaS; they write to the vendor's support. MVP covers three intents: promo_how_to, promo_not_applied, double_charge (plus `other`).
- Shared product documentation is curated by us and goes to `kb_global`. Customer tickets never enter `kb_global`.
- Ticket-derived knowledge stays inside its tenant (`kb_tenant`) and is `pending_review`; nothing is published automatically in the MVP.
- Cancelling a duplicate subscription does not refund a captured payment; docs and extracted records must not claim it does.
- Customer data (phones, emails, cards) must not be stored in the KB or sent to a model unredacted.
