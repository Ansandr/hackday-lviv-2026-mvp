# Business context

- Customers are venue owners using our SaaS; they write to the vendor's support.
- Refund policy: auto refund only for a confirmed duplicate, max 2000 UAH per ticket; above goes to a billing manager.
- A bank hold (`pending`) is not a charge; two venues = two subscriptions, not a duplicate.
- Knowledge must never come from an unverified ticket: only judge score >= 4 and `policy_ok` enters the KB as `approved`.
- Customer data (phones, emails, cards) must not be stored in the KB.
- Tenants never see each other's ticket-derived knowledge (`tenant_scope`).
