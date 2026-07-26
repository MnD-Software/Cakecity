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
