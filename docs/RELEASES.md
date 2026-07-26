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

## Next releases

- 0.4: M-Pesa/card payment orchestration and WooCommerce order authority
- 0.5: accounts, animated tracking, notifications and quick reorder
- 0.6: loyalty, wallet, referrals, memberships and event reminders
- 0.7: admin, CRM, marketing automation and analytics
- 0.8: kitchen production and driver operations
- 0.9: corporate ordering and approval workflows
- 1.0: hardened public launch, load/security/accessibility evidence
