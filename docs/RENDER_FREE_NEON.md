# Free Render deployment with Neon

This is the zero-paid-worker deployment path. It uses:

- Vercel for the customer web application
- one free Render Web Service for FastAPI and the background worker
- Neon for PostgreSQL
- one free Render Key Value instance for Redis

Free Render services sleep after 15 minutes without inbound traffic. While the service is asleep,
scheduled reminders and WooCommerce synchronization pause and the first API request can take about
one minute. Upgrade to the standard `render.yaml` topology before relying on time-critical orders.

## 1. Prepare Neon

Create a Neon project and copy its PostgreSQL connection string. Use the direct connection string
for this long-running Render service. Keep `sslmode=require` if Neon includes it. Never commit the
connection string.

## 2. Create Redis manually

In Render select **New > Key Value**, choose the **Free** instance, name it `cakecity-redis`, and
copy its internal connection string after creation.

## 3. Create the API manually

In Render select **New > Web Service**, connect `MnD-Software/Cakecity`, then configure:

```text
Name: cakecity-api
Region: Singapore
Branch: main
Runtime: Docker
Dockerfile Path: backend/api/Dockerfile
Docker Build Context Directory: .
Docker Command: python start_free.py
Health Check Path: /health
Instance Type: Free
```

`start_free.py` safely applies append-only migrations, starts the lightweight worker, and binds
Uvicorn to Render's assigned port.

## 4. Add Render environment variables

Required:

```text
ENVIRONMENT=production
DATABASE_URL=<Neon connection string>
REDIS_URL=<Render Key Value internal connection string>
JWT_SECRET=<at least 32 random characters>
WOOCOMMERCE_URL=https://cakecity.co.ke
WOOCOMMERCE_CONSUMER_KEY=<secret>
WOOCOMMERCE_CONSUMER_SECRET=<secret>
WOOCOMMERCE_WEBHOOK_SECRET=<new random secret>
SECURE_COOKIES=true
COOKIE_SAMESITE=none
DATABASE_POOL_SIZE=3
DATABASE_MAX_OVERFLOW=2
PUBLIC_API_URL=https://cakecity-api.onrender.com
STOREFRONT_URL=<your Vercel production URL>
ALLOWED_HOSTS=["cakecity-api.onrender.com"]
ALLOWED_ORIGINS=["<your exact Vercel production URL>"]
```

Add payment, email, Web Push, and Cloudinary secrets only when those integrations are enabled.
Do not place WooCommerce secrets in Vercel or any `NEXT_PUBLIC_` variable.

## 5. Verify and connect Vercel

After Render deploys, verify:

```text
https://cakecity-api.onrender.com/health
https://cakecity-api.onrender.com/ready
```

`/ready` must report both database and Redis as healthy. In Vercel set:

```text
NEXT_PUBLIC_API_URL=https://cakecity-api.onrender.com
```

Redeploy Vercel, then update `STOREFRONT_URL` and `ALLOWED_ORIGINS` in Render with the exact final
Vercel URL. Redeploy Render once more before testing accounts or checkout.
