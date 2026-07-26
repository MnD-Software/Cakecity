# Cake City Platform

A premium, Kenya-first commerce platform with WooCommerce as the source of truth and a locally owned high-performance browsing model.

## Run the customer experience

```powershell
corepack pnpm install
corepack pnpm run dev
```

Open `http://localhost:3000`.

## Install the PWA representation

Open the website in Chrome or Edge on localhost or HTTPS. Use the **Install app**
prompt shown by Cake City, or choose **Install Cake City** from the browser menu.
The installed experience launches in its own window and includes an offline fallback.

## Deployment

- Vercel: import this repository and use the root `vercel.json`.
- Render: create a Blueprint from the root `render.yaml`, then provide the WooCommerce webhook secret.
- Both services deploy only after the repository verification checks pass.

## Run supporting services

```powershell
docker compose -f docker/docker-compose.yml up
```

The API health endpoint is `http://localhost:8000/health`. Copy `.env.example` to `.env` and supply real secrets only in the deployment environment.

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
refresh sessions, owner-scoped saved addresses, persistent carts, authoritative checkout pricing,
M-Pesa STK Push, hosted card checkout and outbox-driven WooCommerce order creation.

Live production credentials, persistent loyalty, mobile apps, kitchen/driver surfaces, and AI ranking remain
subsequent releases and are deliberately not represented as complete.

## Configure payments

M-Pesa requires a Daraja consumer key, consumer secret, shortcode, passkey and a strong callback
secret. Configure the callback URL as:

`https://<api-host>/v1/payments/callbacks/mpesa/<MPESA_CALLBACK_SECRET>`

Flutterwave requires its server secret key and webhook secret. Configure its webhook URL as:

`https://<api-host>/v1/payments/callbacks/flutterwave`

Payment endpoints deliberately return `503` until all credentials for the selected provider are
configured. Never expose either provider secret to the browser.
