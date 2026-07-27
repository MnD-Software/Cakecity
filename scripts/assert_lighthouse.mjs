import { readFile } from "node:fs/promises";

const reports = process.argv.slice(2);
if (reports.length === 0) {
  throw new Error("Provide at least one Lighthouse JSON report.");
}

const categoryBudgets = {
  performance: 0.9,
  accessibility: 0.95,
  "best-practices": 0.95,
  seo: 0.95,
};
const metricBudgets = {
  "largest-contentful-paint": 2500,
  "cumulative-layout-shift": 0.1,
  "total-blocking-time": 200,
};

let failed = false;
for (const reportPath of reports) {
  const report = JSON.parse(await readFile(reportPath, "utf8"));
  console.log(`Lighthouse budgets for ${report.finalDisplayedUrl ?? report.requestedUrl}`);

  for (const [category, minimum] of Object.entries(categoryBudgets)) {
    const score = report.categories?.[category]?.score;
    const passed = typeof score === "number" && score >= minimum;
    console.log(`  ${category}: ${score ?? "missing"} (minimum ${minimum}) ${passed ? "PASS" : "FAIL"}`);
    if (!passed) console.log(`::error title=Lighthouse ${category}::score=${score ?? "missing"} minimum=${minimum} report=${reportPath}`);
    failed ||= !passed;
  }

  for (const [audit, maximum] of Object.entries(metricBudgets)) {
    const value = report.audits?.[audit]?.numericValue;
    const passed = typeof value === "number" && value <= maximum;
    console.log(`  ${audit}: ${value ?? "missing"} (maximum ${maximum}) ${passed ? "PASS" : "FAIL"}`);
    if (!passed) console.log(`::error title=Lighthouse ${audit}::value=${value ?? "missing"} maximum=${maximum} report=${reportPath}`);
    failed ||= !passed;
  }
}

if (failed) {
  process.exitCode = 1;
}
