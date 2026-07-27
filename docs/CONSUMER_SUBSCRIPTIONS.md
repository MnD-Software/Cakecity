# Consumer scheduled and recurring orders

Cake City v1.5 adds customer cake plans for one-time future orders and weekly, monthly, quarterly or
annual traditions.

## Lifecycle

Customers create and manage plans at `/account/subscriptions` or begin from a product page. Each
plan stores an authoritative synchronized product reference, bounded cake configuration, optional
owner-scoped delivery address, cadence, preferred window and next renewal time.

The worker claims due plans with row locks and creates one unique renewal run per scheduled time.
It then sends an in-app/email/push-capable notification through the existing transactional outbox.
Paused and cancelled plans never produce renewals. One-time plans become completed after their run.

## Payment boundary

Renewals deliberately require customer confirmation through the existing server-priced checkout.
Cake City does not store raw card numbers or silently create provider charges. Clicking “Order this
delivery” restores the exact configured cake into the durable PWA cart and marks the renewal ready
for checkout. Current stock and price are revalidated before payment.

This architecture can later support tokenized provider mandates or explicit wallet auto-pay without
changing the schedule or renewal-run contracts.

## Operations

The Render worker evaluates due consumer and corporate schedules every minute. Unique
`(subscription_id, scheduled_for)` storage plus `SKIP LOCKED` claims makes renewal creation safe
under horizontal worker scaling.
