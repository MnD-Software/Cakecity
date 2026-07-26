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

## Synchronization guarantees

- Webhook signatures are verified with HMAC-SHA256 using constant-time comparison.
- Payload size and JSON validity are checked before persistence.
- A delivery key derived from webhook ID, topic, and payload hash makes ingestion idempotent.
- Raw events are committed before worker notification, so RabbitMQ downtime cannot lose changes.
- Workers lock events with `SKIP LOCKED`, upsert by WooCommerce ID, retry failures, and dead-letter after eight attempts.
- Product deletion is soft because historical orders must retain their product relationship.
- Initial synchronization walks every WooCommerce result page and commits bounded batches.
- Public catalog endpoints expose only published, in-stock PostgreSQL records with bounded pagination.
