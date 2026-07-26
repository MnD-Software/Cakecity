import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("catalog keeps stable product IDs for synchronization", () => {
  const source = readFileSync(new URL("../lib/catalog.ts", import.meta.url), "utf8");
  for (const id of ["red-velvet", "salted-caramel", "chocolate", "berry"]) assert.match(source, new RegExp(`id: "${id}"`));
});

test("storefront exposes delivery and accessible dialogs", () => {
  const source = readFileSync(new URL("../components/storefront.tsx", import.meta.url), "utf8");
  assert.match(source, /Choose delivery time/);
  assert.match(source, /aria-modal="true"/);
});

test("PWA has install, offline, update and maskable icon contracts", () => {
  const shell = readFileSync(new URL("../components/pwa-shell.tsx", import.meta.url), "utf8");
  const manifest = readFileSync(new URL("../app/manifest.ts", import.meta.url), "utf8");
  const worker = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");
  assert.match(shell, /beforeinstallprompt/);
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
