# Release strategy

Cake City uses small, verified releases on `main`. Every release must pass web tests,
strict TypeScript, a production Next.js build, API tests, and deployment configuration validation.

## 0.2.0 — Platform foundation and installable preview

- Premium responsive customer storefront
- WooCommerce synchronization and PostgreSQL browse boundary
- Signed and idempotent webhook ingestion
- PWA manifest, install prompt, service worker, offline route and app icons
- Vercel and Render blueprints
- GitHub Actions verification

## 0.3.0 — Identity and checkout foundation

- Secure customer registration, sign-in, short access tokens and rotating refresh sessions
- Saved delivery-address domain and protected account endpoints
- Persistent offline-friendly browser cart plus authenticated server cart
- Server-authoritative checkout quotes using synchronized price and stock
- Cake size, inscription, add-on and delivery-fee calculation
- Premium account and delivery-time checkout experiences
- Append-only, checksum-protected production migration runner

## 0.4.0 — Payments and WooCommerce order authority

- Idempotent payment intents for signed-in and guest customers
- Safaricom M-Pesa STK Push with amount-bound callback processing
- Flutterwave hosted card checkout with HMAC webhook verification
- Server-side Flutterwave transaction verification before order release
- Payment recovery, polling, cancellation, mismatch and manual-review states
- Transactional outbox with leases, exponential retries and dead-letter state
- Paid-order creation in WooCommerce with duplicate-reference recovery
- Installable PWA checkout and card-return experiences

## 0.5.0 — Post-purchase journey and notifications

- Owner-scoped order history, detail and current-catalogue quick reorder
- Append-only nine-stage production and delivery timeline
- Worker processing for signed WooCommerce product and order webhooks
- Live animated PWA order tracking with automatic refresh
- In-app notification inbox and per-channel customer preferences
- Brevo transactional email and VAPID Web Push dispatch
- Expired push-subscription cleanup and notification deep links

## 0.6.0 — Rewards, wallet and recurring celebrations

- Immutable points and store-credit ledgers with concurrency-safe balances
- Silver, Gold, Diamond and Platinum membership progression from delivered spend
- Points-to-wallet redemption with idempotency and spendable wallet checkout
- Referral codes, pre-first-order attribution and delivery-settled two-sided rewards
- Owner-scoped family birthday, anniversary and milestone calendar
- Nairobi-time annual reminder automation with duplicate-delivery protection
- Annual birthday points for the account holder’s single self moment
- Premium Rewards and My Moments PWA account experiences

## Next releases

- 0.7: admin, CRM, marketing automation and analytics
- 0.8: kitchen production and driver operations
- 0.9: corporate ordering and approval workflows
- 1.0: hardened public launch, load/security/accessibility evidence
