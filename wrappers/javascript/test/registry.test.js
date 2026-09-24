"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { MICRegistry } = require("../src");
const { CASES } = require("./fixture");

// --- Sanity assertions on the bundled snapshot ---

const REG = new MICRegistry();
assert.ok(REG.size > 0, "bundled registry is empty");
assert.equal(REG.version, "0.1.0", `unexpected version: ${REG.version}`);
assert.deepEqual(REG.brokenChains, [], "bundled snapshot has broken chains");

// --- Shape of the bundled snapshot ---

test("loads bundled snapshot", () => {
  const r = new MICRegistry();
  assert.ok(r.size > 0);
  assert.equal(r.version, REG.version);
  assert.equal(r.sourceSnapshot, REG.sourceSnapshot);
  assert.ok(r.sourceHash.startsWith("sha256:"));
});

test("loads from explicit path", () => {
  const p = path.resolve(__dirname, "..", "..", "..", "iso10383.json");
  const r = new MICRegistry(p);
  assert.equal(r.size, REG.size);
});

test("rejects invalid source", () => {
  assert.throws(() => new MICRegistry(42), TypeError);
});

test("counts add up", () => {
  const c = REG.counts;
  assert.equal(c.operating + c.segment, c.total);
  assert.equal(c.active + c.updated + c.expired, c.total);
});

// --- Contract fixture cases ---

test("contract: lookup XNYS", () => {
  const c = CASES.lookup_xnys;
  const m = REG.byMic(c.args[0]);
  assert.ok(m);
  for (const [k, v] of Object.entries(c.expect)) {
    assert.equal(m[k], v, `${k}: ${m[k]} != ${v}`);
  }
});

test("contract: lookup XTKS", () => {
  const c = CASES.lookup_xtks;
  const m = REG.byMic(c.args[0]);
  assert.ok(m);
  for (const [k, v] of Object.entries(c.expect)) {
    assert.equal(m[k], v, `${k}: ${m[k]} != ${v}`);
  }
});

test("contract: lookup missing returns null", () => {
  const c = CASES.lookup_missing;
  assert.equal(REG.byMic(c.args[0]), null);
});

test("contract: segments XJPX contains XTKS", () => {
  const c = CASES.segments_xjpx_contains_xtks;
  const segs = REG.segments(c.args[0]);
  const want = c.expect_contains;
  assert.ok(segs.some(s => Object.entries(want).every(([k, v]) => s[k] === v)));
});

test("contract: segments XJPX not empty", () => {
  assert.ok(REG.segments("XJPX").length > 0);
});

test("contract: parent XTKS is XJPX", () => {
  const c = CASES.parent_xtks;
  assert.equal(REG.operatingMic(c.args[0]), c.expect);
});

test("contract: parent of operating is self", () => {
  const c = CASES.parent_of_operating_is_self;
  assert.equal(REG.operatingMic(c.args[0]), c.expect);
});

test("contract: expired since 2024", () => {
  const c = CASES.expired_since_2024;
  const rows = REG.expired(c.args[0]);
  assert.ok(rows.length >= c.expect_count_min);
  for (const r of rows) {
    assert.equal(r.status, c.expect_all_status);
    assert.ok((r.expiration_date || "") >= c.expect_all_expiration_ge);
  }
});

test("contract: search nasdaq count", () => {
  const c = CASES.search_nasdaq_count;
  assert.ok(REG.search(c.args[0]).length >= c.expect_count_min);
});

test("contract: by country US", () => {
  const c = CASES.list_by_country_us;
  const rows = REG.byCountry(c.args[0]);
  assert.ok(rows.length >= c.expect_count_min);
  for (const r of rows) {
    for (const [k, v] of Object.entries(c.expect_all_field)) {
      assert.equal(r[k], v);
    }
  }
});

test("contract: by status ACTIVE", () => {
  const c = CASES.list_by_status_active;
  const rows = REG.byStatus(c.args[0]);
  assert.ok(rows.length >= c.expect_count_min);
  for (const r of rows) {
    for (const [k, v] of Object.entries(c.expect_all_field)) {
      assert.equal(r[k], v);
    }
  }
});

test("contract: by mic_type SEGMENT", () => {
  const c = CASES.list_by_mic_type_segment;
  const rows = REG.byMicType(c.args[0]);
  assert.ok(rows.length >= c.expect_count_min);
  for (const r of rows) {
    for (const [k, v] of Object.entries(c.expect_all_field)) {
      assert.equal(r[k], v);
    }
  }
});

test("contract: validate all present", () => {
  const c = CASES.validate_all_present;
  const { ok, missing } = REG.validate(c.args[0]);
  assert.equal(ok, c.expect_ok);
  assert.deepEqual(missing, []);
});

test("contract: validate missing", () => {
  const c = CASES.validate_missing_returns_false;
  const { ok, missing } = REG.validate(c.args[0]);
  assert.equal(ok, c.expect_ok);
  assert.deepEqual(missing.sort(), c.expect_missing.slice().sort());
});

// --- Copy semantics ---

test("lookup returns a fresh object", () => {
  const a = REG.byMic("XNYS");
  const b = REG.byMic("XNYS");
  assert.ok(a && b);
  assert.notStrictEqual(a, b);
  assert.deepEqual(a, b);
});

test("all() is a defensive copy", () => {
  const rows = REG.all();
  const n = rows.length;
  rows.push(rows[0]);
  assert.equal(REG.all().length, n);
});
