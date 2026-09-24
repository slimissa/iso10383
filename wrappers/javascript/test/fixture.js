"use strict";

// Fixture-anchor rule: tests read every expected value from CASES,
// which is derived from the shared contract file. Nothing in
// registry.test.js hardcodes a MIC, count, or country code.

const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const FIXTURE   = path.join(REPO_ROOT, "tests", "cross_language_consistency.json");

if (!fs.existsSync(FIXTURE)) {
  throw new Error(`missing shared fixture: ${FIXTURE}`);
}

const contract = JSON.parse(fs.readFileSync(FIXTURE, "utf8"));

const CASES = {};
for (const c of contract.cases) {
  CASES[c.id] = c;
}

module.exports = { CASES };
