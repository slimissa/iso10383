"use strict";

const fs = require("node:fs");
const path = require("node:path");

const BUNDLED = path.join(__dirname, "data", "iso10383.json");

/**
 * MICRegistry - read-only access to an iso10383 snapshot.
 *
 * Constructed with no argument, loads the bundled snapshot. Passing a
 * path reads that file. Passing an object treats it as a pre-parsed
 * snapshot.
 */
class MICRegistry {
  constructor(source) {
    let data;
    if (source === undefined || source === null) {
      data = JSON.parse(fs.readFileSync(BUNDLED, "utf8"));
    } else if (typeof source === "string") {
      data = JSON.parse(fs.readFileSync(source, "utf8"));
    } else if (typeof source === "object") {
      data = source;
    } else {
      throw new TypeError("source must be undefined, a path, or an object");
    }

    if (!data || !data.meta || !Array.isArray(data.mics)) {
      throw new Error("snapshot missing 'meta' or 'mics'");
    }

    this._meta = data.meta;
    this._mics = data.mics;
    this._byMic = new Map();
    for (const m of this._mics) {
      this._byMic.set(m.mic, m);
    }
  }

  // --- metadata ---

  get version()        { return this._meta.version; }
  get updated()        { return this._meta.updated; }
  get sourceSnapshot() { return this._meta.source_snapshot; }
  get sourceHash()     { return this._meta.source_hash; }
  get counts()         { return { ...this._meta.counts }; }
  get brokenChains()   { return [...(this._meta.broken_chains || [])]; }

  get size()           { return this._mics.length; }

  // --- queries ---

  all() {
    return this._mics.map(m => ({ ...m }));
  }

  byMic(mic) {
    const m = this._byMic.get(String(mic).toUpperCase());
    return m ? { ...m } : null;
  }

  /**
   * Direct children of an operating MIC.
   * A grandchild whose parent is another segment is not listed here.
   * Walk with operatingMic() for multi-level chains.
   */
  segments(mic) {
    const u = String(mic).toUpperCase();
    return this._mics
      .filter(m => m.mic_type === "SEGMENT" && m.operating_mic === u)
      .map(m => ({ ...m }));
  }

  operatingMic(mic) {
    const m = this._byMic.get(String(mic).toUpperCase());
    return m ? m.operating_mic : null;
  }

  expired(since) {
    let rows = this._mics.filter(m => m.status === "EXPIRED");
    if (since) {
      rows = rows.filter(m => (m.expiration_date || "") >= since);
    }
    rows.sort((a, b) =>
      (a.expiration_date || "").localeCompare(b.expiration_date || ""));
    return rows.map(m => ({ ...m }));
  }

  byCountry(code) {
    const u = String(code).toUpperCase();
    return this._mics.filter(m => m.country_code === u).map(m => ({ ...m }));
  }

  byStatus(status) {
    const u = String(status).toUpperCase();
    return this._mics.filter(m => m.status === u).map(m => ({ ...m }));
  }

  byMicType(micType) {
    const u = String(micType).toUpperCase();
    return this._mics.filter(m => m.mic_type === u).map(m => ({ ...m }));
  }

  byCategory(category) {
    return this._mics
      .filter(m => m.market_category === category)
      .map(m => ({ ...m }));
  }

  search(query) {
    const q = String(query).toLowerCase();
    return this._mics
      .filter(m =>
        (m.market_name || "").toLowerCase().includes(q) ||
        (m.acronym || "").toLowerCase().includes(q))
      .map(m => ({ ...m }));
  }

  /**
   * Returns { ok: boolean, missing: string[] }.
   * ok is true when every MIC exists.
   */
  validate(mics) {
    const missing = [];
    for (const m of mics) {
      if (!this._byMic.has(String(m).toUpperCase())) {
        missing.push(m);
      }
    }
    return { ok: missing.length === 0, missing };
  }
}

module.exports = { MICRegistry };
