# Production deployment

Cake City deploys the customer, admin and kitchen Next.js applications to Vercel and the FastAPI
API, worker, PostgreSQL and Redis services through the root Render Blueprint.

## Required release order

1. Merge a commit only after the `Verify Cake City` and CodeQL workflows pass.
2. Deploy the Render Blueprint first. The API start command runs `migrate.py` before Uvicorn.
3. Confirm `GET https://<api-host>/health` returns `200` and
   `GET https://<api-host>/ready` returns `{"status":"ready"}`.
4. Deploy the Vercel projects with `NEXT_PUBLIC_API_URL` set to that HTTPS API origin.
5. Confirm the storefront, `/corporate`, `/manifest.webmanifest`, `/sw.js`, `/robots.txt` and
   `/sitemap.xml` return successfully.
6. Install the PWA from Chrome or Edge and verify an offline reload reaches `/offline`.

## Mandatory Render secrets

Supply strong production values for `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`,
`WOOCOMMERCE_URL`, `WOOCOMMERCE_CONSUMER_KEY`, `WOOCOMMERCE_CONSUMER_SECRET` and
`WOOCOMMERCE_WEBHOOK_SECRET`. Production startup rejects local databases, local Redis,
insecure WooCommerce URLs, insecure cookies and HTTP browser origins.

`ALLOWED_HOSTS` must contain the exact Render API hostname. Configure payment, email, Web Push
and Cloudinary credentials only in Render; none belong in Vercel or browser bundles.

## Rollback

Roll the Vercel projects back to the preceding deployment and select the preceding Render deploy.
Database migrations are append-only and remain forward-compatible; never reverse them by deleting
tables or columns. Keep workers stopped only while diagnosing a failed migration, then restore the
last verified API and worker commit together.
