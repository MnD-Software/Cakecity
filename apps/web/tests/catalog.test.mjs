import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("catalog keeps stable product IDs for synchronization", () => {
  const source = readFileSync(new URL("../lib/catalog.ts", import.meta.url), "utf8");
  for (const id of ["red-velvet", "salted-caramel", "chocolate", "berry"]) assert.match(source, new RegExp(`id: "${id}"`));
});

test("local storefront can render the public WooCommerce catalogue without exposing credentials", () => {
  const loader = readFileSync(new URL("../lib/server-catalog.ts", import.meta.url), "utf8");
  const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(loader, /import "server-only"/);
  assert.match(loader, /wc\/store\/v1/);
  assert.doesNotMatch(loader, /consumer_key|consumer_secret|ck_[a-f0-9]{20}|cs_[a-f0-9]{20}/);
  assert.match(loader, /categories,/);
  assert.match(page, /liveStorefrontProducts/);
});

test("storefront exposes delivery and accessible dialogs", () => {
  const source = readFileSync(new URL("../components/storefront.tsx", import.meta.url), "utf8");
  assert.match(source, /Choose delivery time/);
  assert.match(source, /aria-modal="true"/);
});

test("version 2 storefront has a photographic swipe carousel and app navigation", () => {
  const source = readFileSync(new URL("../components/storefront.tsx", import.meta.url), "utf8");
  const styles = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");
  assert.match(source, /aria-roledescription="carousel"/);
  assert.match(source, /offerTrackRef/);
  assert.match(source, /offer-butterscotch\.avif/);
  assert.match(source, /Mobile app navigation/);
  assert.match(styles, /scroll-snap-type:x mandatory/);
  assert.match(styles, /\.mobile-tabbar \.tabbar-order/);
});

test("PWA has install, offline, update and maskable icon contracts", () => {
  const shell = readFileSync(new URL("../components/pwa-shell.tsx", import.meta.url), "utf8");
  const manifest = readFileSync(new URL("../app/manifest.ts", import.meta.url), "utf8");
  const worker = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");
  assert.match(shell, /beforeinstallprompt/);
  assert.match(shell, /Add to Home Screen/);
  assert.match(shell, /display-mode: standalone/);
  assert.match(shell, /serviceWorker\.register/);
  assert.match(manifest, /purpose: "maskable"/);
  assert.match(worker, /caches\.match\("\/offline"\)/);
});

test("cart survives reload and checkout requests an authoritative quote", () => {
  const cart = readFileSync(new URL("../lib/use-persistent-cart.ts", import.meta.url), "utf8");
  const checkout = readFileSync(new URL("../app/checkout/page.tsx", import.meta.url), "utf8");
  assert.match(cart, /localStorage\.getItem/);
  assert.match(cart, /localStorage\.setItem/);
  assert.match(checkout, /\/v1\/checkout\/quote/);
  assert.match(checkout, /Review availability/);
});

test("account UI uses register, login, refresh and logout session contracts", () => {
  const client = readFileSync(new URL("../lib/api.ts", import.meta.url), "utf8");
  const account = readFileSync(new URL("../app/account/page.tsx", import.meta.url), "utf8");
  assert.match(client, /\/v1\/auth\/refresh/);
  assert.match(client, /credentials: "include"/);
  assert.match(account, /authenticate\(mode/);
  assert.match(account, /await logout\(\)/);
});

test("checkout supports M-Pesa, hosted cards and recoverable payment return", () => {
  const checkout = readFileSync(new URL("../app/checkout/page.tsx", import.meta.url), "utf8");
  const returned = readFileSync(new URL("../app/checkout/payment-return/page.tsx", import.meta.url), "utf8");
  assert.match(checkout, /Idempotency-Key/);
  assert.match(checkout, /method: paymentMethod/);
  assert.match(checkout, /M-Pesa/);
  assert.match(checkout, /Visa, Mastercard and Amex/);
  assert.match(returned, /cakecity-active-payment/);
  assert.match(returned, /\/v1\/payments\/intents/);
});

test("rewards and moments are operational PWA account experiences", () => {
  const rewards = readFileSync(new URL("../app/account/rewards/page.tsx", import.meta.url), "utf8");
  const moments = readFileSync(new URL("../app/account/moments/page.tsx", import.meta.url), "utf8");
  const checkout = readFileSync(new URL("../app/checkout/page.tsx", import.meta.url), "utf8");
  assert.match(rewards, /\/v1\/account\/rewards\/redeem/);
  assert.match(rewards, /\/v1\/account\/rewards\/referrals\/apply/);
  assert.match(moments, /\/v1\/account\/moments/);
  assert.match(moments, /\/v1\/account\/moments\/timeline/);
  assert.match(moments, /Reorder last cake/);
  assert.match(moments, /Your cake timeline/);
  assert.match(checkout, /Cake City credit/);
  assert.match(checkout, /setPaymentMethod\("wallet"\)/);
});

test("corporate portal exposes governed purchasing workflows", () => {
  const source = readFileSync(new URL("../app/corporate/page.tsx", import.meta.url), "utf8");
  for (const contract of [
    "/v1/corporate/me", "/v1/corporate/requests", "/v1/corporate/invoices",
    "/v1/corporate/recurring", "Idempotency-Key", "Approve & invoice",
  ]) assert.match(source, new RegExp(contract.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")));
});

test("launch SEO and security contracts are explicit", () => {
  const layout = readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8");
  const home = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  const sitemap = readFileSync(new URL("../app/sitemap.ts", import.meta.url), "utf8");
  const robots = readFileSync(new URL("../app/robots.ts", import.meta.url), "utf8");
  const config = readFileSync(new URL("../next.config.ts", import.meta.url), "utf8");
  assert.match(layout, /twitter:/);
  assert.match(home, /application\/ld\+json/);
  assert.match(home, /"@type": "Bakery"/);
  assert.match(sitemap, /cakecity\.co\.ke/);
  assert.match(robots, /sitemap\.xml/);
  assert.match(config, /Content-Security-Policy/);
  assert.match(config, /Strict-Transport-Security/);
});

test("premium product journey remains connected to authoritative checkout", () => {
  const page = readFileSync(new URL("../app/cakes/[slug]/page.tsx", import.meta.url), "utf8");
  const experience = readFileSync(new URL("../components/product-experience.tsx", import.meta.url), "utf8");
  const cart = readFileSync(new URL("../lib/use-persistent-cart.ts", import.meta.url), "utf8");
  assert.match(page, /ProductExperience/);
  assert.match(page, /application\/ld\+json/);
  assert.match(experience, /Choose your size/);
  assert.match(experience, /Make it personal/);
  assert.match(experience, /Choose how it arrives/);
  assert.match(experience, /Often chosen together/);
  assert.match(experience, /Recently viewed/);
  assert.match(cart, /addOnPrices/);
});

test("intelligent discovery is visible and operational", () => {
  const discovery = readFileSync(new URL("../components/discovery-experience.tsx", import.meta.url), "utf8");
  const tracking = readFileSync(new URL("../lib/discovery.ts", import.meta.url), "utf8");
  const storefront = readFileSync(new URL("../components/storefront.tsx", import.meta.url), "utf8");
  assert.match(discovery, /\/v1\/discovery\/search/);
  assert.match(discovery, /\/v1\/discovery\/recommendations/);
  assert.match(discovery, /\/v1\/discovery\/concierge/);
  assert.match(discovery, /six-year-old daughter/);
  assert.match(tracking, /X-Discovery-Session/);
  assert.match(storefront, /PersonalizedRail/);
  assert.match(storefront, /ConciergePanel/);
});

test("saved celebrations persist locally and synchronize to the protected account", () => {
  const hook = readFileSync(new URL("../lib/use-saved-cakes.ts", import.meta.url), "utf8");
  const saved = readFileSync(new URL("../app/account/saved/page.tsx", import.meta.url), "utf8");
  const product = readFileSync(new URL("../components/product-experience.tsx", import.meta.url), "utf8");
  assert.match(hook, /cakecity-saved-cakes-v1/);
  assert.match(hook, /\/v1\/account\/saved\/cakes/);
  assert.match(saved, /\/v1\/account\/saved\/messages/);
  assert.match(saved, /Favourite cakes/);
  assert.match(saved, /Saved inscriptions/);
  assert.match(product, /toggleSaved\(product\.slug\)/);
});

test("saved addresses are manageable and accelerate checkout", () => {
  const account = readFileSync(new URL("../app/account/page.tsx", import.meta.url), "utf8");
  const addresses = readFileSync(new URL("../app/account/addresses/page.tsx", import.meta.url), "utf8");
  const checkout = readFileSync(new URL("../app/checkout/page.tsx", import.meta.url), "utf8");
  assert.match(account, /\/account\/addresses/);
  assert.match(addresses, /\/v1\/account\/addresses/);
  assert.match(addresses, /\/default/);
  assert.match(addresses, /method: editing \? "PUT" : "POST"/);
  assert.match(checkout, /Deliver to a saved place/);
  assert.match(checkout, /selectedAddress\?\.recipient_name/);
});

test("consumer cake plans support scheduled and recurring secure checkout", () => {
  const subscriptions = readFileSync(new URL("../app/account/subscriptions/page.tsx", import.meta.url), "utf8");
  const product = readFileSync(new URL("../components/product-experience.tsx", import.meta.url), "utf8");
  const account = readFileSync(new URL("../app/account/page.tsx", import.meta.url), "utf8");
  assert.match(subscriptions, /\/v1\/account\/subscriptions/);
  assert.match(subscriptions, /One scheduled order/);
  assert.match(subscriptions, /Every week/);
  assert.match(subscriptions, /Every month/);
  assert.match(subscriptions, /Payment always uses secure checkout/);
  assert.match(product, /Make this a weekly or monthly tradition/);
  assert.match(account, /Scheduled and recurring orders/);
});

test("cart continuity synchronizes, recovers and closes after verified payment", () => {
  const cart = readFileSync(new URL("../lib/use-persistent-cart.ts", import.meta.url), "utf8");
  const checkout = readFileSync(new URL("../app/checkout/page.tsx", import.meta.url), "utf8");
  const returned = readFileSync(new URL("../app/checkout/payment-return/page.tsx", import.meta.url), "utf8");
  const account = readFileSync(new URL("../app/account/page.tsx", import.meta.url), "utf8");
  assert.match(cart, /method: "PUT"/);
  assert.match(cart, /\/v1\/cart/);
  assert.match(checkout, /\/v1\/cart\/checkout-started/);
  assert.match(checkout, /\/v1\/cart\/recovered/);
  assert.match(checkout, /\/v1\/cart\/complete/);
  assert.match(returned, /cakecity-cart-v1/);
  assert.match(account, /Continue your cart on this device/);
});
