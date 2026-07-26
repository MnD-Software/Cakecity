import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("admin console uses staff authentication and all operational APIs", () => {
  const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  const client = readFileSync(new URL("../lib/api.ts", import.meta.url), "utf8");
  assert.match(client, /staffLogin/);
  assert.match(client, /admin.*manager.*marketing.*support/);
  for (const contract of ["/v1/admin/overview", "/v1/admin/customers", "/v1/admin/crm/leads", "/v1/admin/campaigns", "/v1/admin/analytics/revenue", "/v1/admin/analytics/retention", "/v1/admin/audit"]) {
    assert.match(page, new RegExp(contract.replaceAll("/", "\\/")));
  }
});

test("staff mutations expose CRM and campaign workflows", () => {
  const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /method: "PATCH"/);
  assert.match(page, /stage: next/);
  assert.match(page, /scheduled_at: new Date\(\)\.toISOString\(\)/);
  assert.match(page, /Role-secured access/);
  assert.match(page, /Every change audited/);
});

test("staff can visibly provision governed corporate accounts", () => {
  const source = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(source, /\/v1\/corporate\/admin\/accounts/);
  assert.match(source, /Corporate partnerships/);
  assert.match(source, /Grant company access/);
});
