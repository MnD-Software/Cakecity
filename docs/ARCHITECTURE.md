# Cake City platform architecture

WooCommerce remains the commercial authority for products, prices, coupons, inventory, customers, and orders. Webhooks enter through a signature-verifying ingestion service, are placed on RabbitMQ, and are handled by idempotent workers. Workers upsert a query-optimized PostgreSQL read model and invalidate Redis keys. Customer browsing reads only PostgreSQL/Redis; it never waits on WooCommerce.

## Bounded applications

- `apps/web`: premium customer storefront and PWA
- `apps/admin`: merchandising, CRM, loyalty, marketing, and analytics (planned)
- `apps/kitchen`: production queue and quality workflow (planned)
- `apps/mobile`: Flutter customer app (planned)
- `apps/driver`: Flutter delivery app (planned)
- `backend/api`: authenticated FastAPI gateway
- `backend/webhook-sync`: WooCommerce ingestion boundary

## Delivery order

1. Catalog synchronization, discovery, personalization, cart, checkout, M-Pesa, and analytics instrumentation.
2. Account, order tracking, loyalty/referrals, recovery automation, and corporate ordering.
3. Kitchen and driver operations with status events and live tracking.
4. AI search, recommendation ranking, prediction, and support assistants after sufficient consented behavioral data exists.

All privileged state transitions are server-side, role checked, and audit logged. Payment and webhook operations require idempotency keys. Secrets stay in managed environment variables.

## Identity and checkout authority

- Passwords are salted and hashed with scrypt; plaintext passwords are never stored or logged.
- Access tokens are signed, expire after 15 minutes, and carry only customer ID, role and token metadata.
- Refresh tokens are opaque, stored only as SHA-256 hashes, delivered through HTTP-only cookies, and rotated on every use.
- A customer can revoke the active refresh session by signing out.
- The browser cart is an offline continuity layer. Products, stock, prices, configuration surcharges, delivery fees and final totals are recalculated by the API before payment.
- Saved addresses are owner-scoped by customer ID and never accepted from an access-token claim without reloading the active customer.
- Database migrations are append-only and checksum protected during Render pre-deploy.

## Payments and order release

- Every payment creation requires an idempotency key and recalculates the checkout from synchronized product records.
- Client secrets are stored only as hashes and are sent in headers rather than query strings during status recovery.
- M-Pesa STK callbacks must match both the provider request ID and exact expected amount before an order becomes paid.
- Card data never enters Cake City systems. Flutterwave hosts card collection, signs webhook payloads, and is queried server-side to verify status, exact amount, KES currency and Cake City reference.
- Provider callbacks persist minimal state and return quickly. Network work is performed by the outbox worker.
- A paid local order is an orchestration projection. The worker creates the authoritative WooCommerce order and records its WooCommerce ID.
- WooCommerce retries search for the private Cake City reference before creating an order, reducing duplicate creation after ambiguous network failures.
- Outbox events use row locking, five-minute processing leases, exponential retry and a dead state after eight failed attempts.

## Synchronization guarantees

- Webhook signatures are verified with HMAC-SHA256 using constant-time comparison.
- Payload size and JSON validity are checked before persistence.
- A delivery key derived from webhook ID, topic, and payload hash makes ingestion idempotent.
- Raw events are committed before worker notification, so RabbitMQ downtime cannot lose changes.
- Workers lock events with `SKIP LOCKED`, upsert by WooCommerce ID, retry failures, and dead-letter after eight attempts.
- Product deletion is soft because historical orders must retain their product relationship.
- Initial synchronization walks every WooCommerce result page and commits bounded batches.
- Public catalog endpoints expose only published, in-stock PostgreSQL records with bounded pagination.
