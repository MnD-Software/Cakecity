import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("kitchen UI uses authority-safe production contracts", () => {
  const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /\/v1\/kitchen\/queue/);
  assert.match(page, /\/transition/);
  assert.match(page, /Idempotency-Key/);
  assert.match(page, /\/checklist/);
  assert.match(page, /\/v1\/kitchen\/inventory/);
});
