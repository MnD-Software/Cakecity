# Release strategy

Cake City uses small, verified releases on `main`. Every release must pass web tests,
strict TypeScript, a production Next.js build, API tests, and deployment configuration validation.

## 1.0.3 — Authoritative migration execution

- Resolves the deployment runner to the repository's real `database/migrations` directory.
- Fails deployment when no SQL migrations are found instead of accepting an empty schema.
- Tests the exact ordered migration inventory used by Render and integration CI.

## 1.0.2 — Portable release automation

- Moves GitHub JavaScript actions to their Node 24-compatible major releases.
- Uses a repeatable 200-request, 25-way integration load sample with a 3 second p95 ceiling and
  explicit failure diagnostics for shared runners.

## 1.0.1 — Stable launch gates

- Calibrates cold-run Lighthouse performance enforcement to 90 while retaining 95 for
  accessibility, best practices and SEO plus strict Core Web Vitals limits.
- Calibrates the API load gate for shared CI runners.

## 1.0.0 — Launch-hardening baseline

- Redis-backed fixed-window throttling with stricter authentication limits, request-size guards,
  request IDs and fail-open degraded signalling.
- Dependency-aware `/ready` checks for PostgreSQL and Redis, separate from the liveness endpoint.
- Managed-production validation for PostgreSQL, Redis, HTTPS origins, WooCommerce credentials,
  webhook secrets and secure cookies.
- Bounded database pools, trusted hosts, CSP, HSTS, origin isolation and private-response controls.
- Canonical metadata, Open Graph, structured bakery/search data, robots and XML sitemap routes.
- A 91 KB responsive WebP hero replacing the 1.9 MB primary asset transfer.
- Enforced 90+ performance and 95+ accessibility/best-practice/SEO Lighthouse budgets,
  JavaScript and Python dependency audits, CodeQL analysis, migration-backed integration checks
  and a concurrent API load smoke test.

## 0.9.0 — Corporate commerce

- Premium company workspace with credit visibility, purchasing controls and account-manager access.
- Bulk order requests priced from the synchronized WooCommerce catalogue.
- Requester, approver and company-admin roles with locked approval decisions and audit history.
- Purchase orders, invoice billing, partial settlement records, credit-limit enforcement and
  monthly statement aggregates.
- Recurring weekly/monthly order generation with minute-level worker scheduling.
- Staff provisioning for managed company accounts and member access in Cake City Command.
- Approved corporate orders enter the existing durable WooCommerce, kitchen and delivery pipeline.

## 0.8.0 — Fulfilment operations

- Premium kitchen production lanes, ownership, recipe snapshots, quality controls, inventory
  consumption, and low-stock alerts.
- WooCommerce-authoritative, idempotent stage command pipeline through final delivery.
- Manager dispatch overview with driver availability, vehicles, destinations, and ETA.
- Flutter driver app with secure mobile sessions, live GPS, navigation, calls, chat, camera,
  signature, delivery OTP, and proof upload.
- Customer live driver position, ETA, identity, vehicle, and two-way delivery chat.
- Automatic tested Flutter Web and Android APK artifacts in GitHub Actions.

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

## 0.7.0 — Cake City Command, CRM and growth operations

- Separate premium Next.js admin application with responsive command-centre UX
- Database-enforced staff roles for admin, manager, marketing and support
- Trusted-origin checks for cross-site refresh-cookie operations
- CRM opportunity pipeline, activities, follow-up tasks and stage workflows
- Segment-aware in-app, email and Web Push campaign scheduling
- Idempotent worker expansion and per-customer campaign delivery records
- Customer segments for new, repeat, VIP, lapsed and upcoming birthdays
- Revenue, AOV, repeat purchase, product, loyalty, referral and campaign analytics
- Append-only staff audit trail with actor, request and target evidence
- Secure one-time administrator bootstrap command and separate Vercel configuration

## Next releases

- 1.0: hardened public launch, load/security/accessibility evidence
- 1.1: consented behavioral intelligence, natural-language discovery and recommendation ranking
