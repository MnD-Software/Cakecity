import { readFile } from "node:fs/promises";
import { basename } from "node:path";

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

const median = values => {
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.floor(ordered.length / 2)];
};
const groupedReports = new Map();
for (const reportPath of reports) {
  const report = JSON.parse(await readFile(reportPath, "utf8"));
  const group = basename(reportPath, ".json").replace(/-\d+$/, "");
  const entries = groupedReports.get(group) ?? [];
  entries.push({ report, reportPath });
  groupedReports.set(group, entries);
}

let failed = false;
for (const [group, entries] of groupedReports) {
  console.log(`Lighthouse median budgets for ${group} (${entries.length} sample${entries.length === 1 ? "" : "s"})`);

  for (const [category, minimum] of Object.entries(categoryBudgets)) {
    const values = entries.map(({ report }) => report.categories?.[category]?.score);
    const score = values.every(value => typeof value === "number") ? median(values) : undefined;
    const passed = typeof score === "number" && score >= minimum;
    console.log(`  ${category}: ${score ?? "missing"} (minimum ${minimum}) ${passed ? "PASS" : "FAIL"}`);
    if (!passed) console.log(`::error title=Lighthouse ${category}::median=${score ?? "missing"} samples=${values.join(",")} minimum=${minimum} route=${group}`);
    failed ||= !passed;
  }

  for (const [audit, maximum] of Object.entries(metricBudgets)) {
    const values = entries.map(({ report }) => report.audits?.[audit]?.numericValue);
    const value = values.every(sample => typeof sample === "number") ? median(values) : undefined;
    const passed = typeof value === "number" && value <= maximum;
    console.log(`  ${audit}: ${value ?? "missing"} (maximum ${maximum}) ${passed ? "PASS" : "FAIL"}`);
    if (!passed) console.log(`::error title=Lighthouse ${audit}::median=${value ?? "missing"} samples=${values.join(",")} maximum=${maximum} route=${group}`);
    failed ||= !passed;
  }
}

if (failed) {
  process.exitCode = 1;
}
