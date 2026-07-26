# Cake City Platform

A premium, Kenya-first commerce platform with WooCommerce as the source of truth and a locally owned high-performance browsing model.

## Run the customer experience

```powershell
corepack pnpm install
corepack pnpm run dev
```

Open `http://localhost:3000`.

## Run Cake City Command

```powershell
corepack pnpm --filter @cakecity/admin dev
```

Open `http://localhost:3001`. Staff authentication uses the same secure identity service, but
every `/v1/admin` operation enforces the `admin`, `manager`, `marketing`, or `support` role.
Create the first administrator from a secure Render shell or local deployment environment:

```powershell
$env:ADMIN_EMAIL = "operations@cakecity.co.ke"
$env:ADMIN_PASSWORD = "<strong one-time secret>"
python -m app.bootstrap_admin
```

Run that command from `backend/api`. Remove the one-time password environment value afterward.

## Run the kitchen production board

```powershell
corepack pnpm --filter @cakecity/kitchen dev
```

Open `http://localhost:3002`. Kitchen, manager, and administrator accounts can claim tickets,
follow versioned recipes, complete quality controls, and advance orders through WooCommerce.

## Build the driver app

The Flutter app in `apps/driver` provides secure sessions, assignments, GPS sharing, navigation,
calling, customer chat, camera/signature capture, delivery OTP verification, and proof upload.

```powershell
cd apps/driver
flutter create --platforms=android,web --project-name cakecity_driver .
flutter pub get
flutter run --dart-define=API_URL=http://127.0.0.1:8000
```

Every push to `main` analyzes/tests the app and publishes a release APK plus Flutter Web bundle as
the versioned `cakecity-driver` Actions artifact, configured for the Render API service.

## Install the PWA representation

Open the website in Chrome or Edge on localhost or HTTPS. Use the **Install app**
prompt shown by Cake City, or choose **Install Cake City** from the browser menu.
The installed experience launches in its own window and includes an offline fallback.

## Deployment

- Vercel: import this repository and use the root `vercel.json`.
- Admin Vercel project: set Root Directory to `apps/admin`, use its `vercel.json`, configure
  `NEXT_PUBLIC_API_URL`, and map the deployment to `admin.cakecity.co.ke`.
- Kitchen Vercel project: set Root Directory to `apps/kitchen`, configure `NEXT_PUBLIC_API_URL`,
  and map the deployment to `kitchen.cakecity.co.ke`.
- Render: create a Blueprint from the root `render.yaml`, then provide the WooCommerce webhook secret.
- Both services deploy only after the repository verification checks pass.
- Follow the production sequence and rollback checklist in `docs/DEPLOYMENT.md`.

## Run supporting services

```powershell
docker compose -f docker/docker-compose.yml up
```

The API liveness endpoint is `http://localhost:8000/health`; dependency readiness is
`http://localhost:8000/ready`. Copy `.env.example` to `.env` and supply real secrets only in the
deployment environment.

## Validate the synchronization boundary

```powershell
$env:PYTHONPATH = (Resolve-Path backend/api)
python -m pytest backend/api/tests -q
```

Create WooCommerce webhooks for product created, updated, and deleted events pointing to:

`https://<api-host>/v1/webhooks/woocommerce`

Use the same strong random secret for WooCommerce and `WOOCOMMERCE_WEBHOOK_SECRET`.

## Current executable slice

The web app includes premium responsive discovery, occasion navigation, search, favourites,
configurable products, an offline-persistent cart, secure customer accounts, delivery/pickup
selection, delivery slots and server-confirmed checkout quotes. It is installable as a PWA.

The API includes WooCommerce synchronization, signed webhooks, secure identity, rotating
refresh sessions, owner-scoped saved addresses and orders, persistent carts, authoritative checkout
pricing, M-Pesa STK Push, hosted card checkout and outbox-driven WooCommerce order creation.
WooCommerce order changes feed an append-only nine-stage customer timeline. The installed PWA
includes live tracking, safe quick reorder, an in-app inbox, email preferences and Web Push.
Delivered orders now settle immutable reward points, membership progress and qualifying referrals.
Customers can convert points to spendable Cake City wallet credit, pay fully from that credit at
checkout, and save recurring family moments for automated birthday and anniversary reminders.

Release v0.8 adds the kitchen board, recipe/inventory controls, manager dispatch, native Flutter
driver operations, secure proof of delivery, live driver position, and customer chat. Corporate
commerce is now available at `/corporate` with company accounts, governed bulk orders, approvals,
PO-linked invoice billing, credit controls, statements, account managers, and recurring schedules.
AI ranking remains a subsequent release.

Release v1.0 adds production readiness checks, Redis throttling, bounded database pools, request
guards and security headers. Search metadata, structured data, robots and sitemap routes are
included, the main hero transfer is reduced by more than 95%, and CI now enforces Lighthouse
budgets, dependency audits, CodeQL, migrations and a concurrent API load smoke test.

## Configure delivery proof

Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` on the API and
worker. Create driver accounts through `POST /v1/admin/staff`, then use
`/v1/driver/dispatch/overview` and `/v1/driver/dispatch/assignments`.

## Configure customer notifications

Email delivery uses Brevo when `BREVO_API_KEY` and `BREVO_SENDER_EMAIL` are configured.
Browser/device push requires a VAPID key pair in `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY`;
set `VAPID_SUBJECT` to a monitored `mailto:` contact. In-app notifications work without either
provider. SMS and WhatsApp preferences are stored for their provider integration release and are
labelled provider-ready in the customer interface.

Create WooCommerce webhooks for order created and updated events in addition to the product
webhooks. Cake City maps standard Woo statuses and supports `_cakecity_stage` metadata for the
full kitchen and delivery journey.

## Configure payments

M-Pesa requires a Daraja consumer key, consumer secret, shortcode, passkey and a strong callback
secret. Configure the callback URL as:

`https://<api-host>/v1/payments/callbacks/mpesa/<MPESA_CALLBACK_SECRET>`

Flutterwave requires its server secret key and webhook secret. Configure its webhook URL as:

`https://<api-host>/v1/payments/callbacks/flutterwave`

Payment endpoints deliberately return `503` until all credentials for the selected provider are
configured. Never expose either provider secret to the browser.
