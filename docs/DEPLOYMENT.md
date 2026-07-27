# Production deployment

Cake City deploys the customer, admin and kitchen Next.js applications to Vercel and the FastAPI
API, worker, PostgreSQL and Redis services through the root Render Blueprint.

## Required release order

1. Push a commit only after the `Verify Cake City` and CodeQL workflows pass.
2. In Render, choose **New > Blueprint**, connect `MnD-Software/Cakecity`, and apply the root
   `render.yaml`. Use the Singapore region for the API, worker, PostgreSQL and Key Value service.
3. Enter every `sync: false` secret when Render prompts. Never add these values to Git or Vercel.
4. Deploy the Render Blueprint first. Its pre-deploy command runs `migrate.py`; the web service
   binds Render's runtime `PORT`.
5. Confirm `GET https://<api-host>/health` returns `200` and
   `GET https://<api-host>/ready` returns `{"status":"ready"}`.
6. In Vercel, import the same repository as a project named `cakecity-web`. Leave the Root
   Directory at the repository root so Vercel uses the root `vercel.json`.
7. Add `NEXT_PUBLIC_API_URL=https://cakecity-api.onrender.com` to Production, Preview and
   Development, then deploy. After adding `api.cakecity.co.ke`, replace this value with the custom
   API origin and redeploy.
8. Optionally create separate Vercel projects for `apps/admin` and `apps/kitchen`; set each project
   Root Directory to its app directory and add the same `NEXT_PUBLIC_API_URL`.
9. Confirm the storefront, `/corporate`, `/manifest.webmanifest`, `/sw.js`, `/robots.txt` and
   `/sitemap.xml` return successfully.
10. Install the PWA from Chrome or Edge and verify an offline reload reaches `/offline`.

## Domain and browser session setup

Use `app.cakecity.co.ke` for the customer Vercel project and `api.cakecity.co.ke` for Render.
Keeping them on the same parent domain makes secure session cookies significantly more reliable
than mixing `vercel.app` and `onrender.com` origins.

Once DNS is active, keep these Render values:

```text
PUBLIC_API_URL=https://api.cakecity.co.ke
STOREFRONT_URL=https://app.cakecity.co.ke
ALLOWED_HOSTS=["cakecity-api.onrender.com","api.cakecity.co.ke"]
ALLOWED_ORIGINS=["https://app.cakecity.co.ke","https://admin.cakecity.co.ke","https://kitchen.cakecity.co.ke"]
SECURE_COOKIES=true
COOKIE_SAMESITE=none
```

For the initial Vercel-generated URL, add that exact HTTPS origin to `ALLOWED_ORIGINS` in Render
before testing login or checkout. Do not use a wildcard when credentials are enabled.

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
