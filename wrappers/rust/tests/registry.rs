//! Rust wrapper tests.
//!
//! Fixture-anchor rule: every expected value reads from the shared
//! contract file at tests/cross_language_consistency.json. Nothing
//! in this file hardcodes a MIC, count, or country code.

use iso10383_registry::Registry;
use serde_json::Value;

fn contract() -> Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../tests/cross_language_consistency.json"
    );
    let s = std::fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("read {}: {}", path, e));
    serde_json::from_str(&s).expect("parse contract fixture")
}

fn case<'a>(c: &'a Value, id: &str) -> &'a Value {
    c["cases"]
        .as_array()
        .expect("cases array")
        .iter()
        .find(|x| x["id"] == id)
        .unwrap_or_else(|| panic!("case {} not found", id))
}

fn args_one(c: &Value) -> String {
    c["args"].as_array().expect("args").first()
        .and_then(|v| v.as_str()).expect("arg str").to_string()
}

fn args_list(c: &Value) -> Vec<String> {
    c["args"].as_array().expect("args").first()
        .and_then(|v| v.as_array()).expect("arg list")
        .iter().map(|v| v.as_str().unwrap().to_string()).collect()
}

// --- shape of the bundled snapshot ---

#[test]
fn load_bundled() {
    let r = Registry::load().expect("bundled snapshot loads");
    assert!(!r.is_empty());
    let version = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"), "/../../VERSION"
    )).expect("VERSION file").trim().to_string();
    assert_eq!(r.meta().version, version);
    assert!(r.meta().source_hash.starts_with("sha256:"));
    assert_eq!(r.meta().broken_chains.len(), 0);
}

#[test]
fn load_from_file() {
    let p = concat!(env!("CARGO_MANIFEST_DIR"), "/../../iso10383.json");
    let r = Registry::load_from_file(p).expect("load from path");
    assert!(!r.is_empty());
}

#[test]
fn load_rejects_garbage() {
    assert!(Registry::from_str("not json").is_err());
    assert!(Registry::from_str(r#"{"mics":[]}"#).is_err());
}

#[test]
fn counts_add_up() {
    let r = Registry::load().unwrap();
    let c = &r.meta().counts;
    assert_eq!(c.operating + c.segment, c.total);
    assert_eq!(c.active + c.updated + c.expired, c.total);
}

// --- contract fixture cases ---

#[test]
fn contract_lookup_xnys() {
    let c = contract();
    let cs = case(&c, "lookup_xnys");
    let mic = args_one(cs);
    let r = Registry::load().unwrap();
    let m = r.by_mic(&mic).expect("XNYS present");
    let e = &cs["expect"];
    assert_eq!(m.mic, e["mic"].as_str().unwrap());
    assert_eq!(m.mic_type, e["mic_type"].as_str().unwrap());
    assert_eq!(m.country_code.as_deref(), e["country_code"].as_str());
    assert_eq!(m.operating_mic, e["operating_mic"].as_str().unwrap());
}

#[test]
fn contract_lookup_xtks() {
    let c = contract();
    let cs = case(&c, "lookup_xtks");
    let mic = args_one(cs);
    let r = Registry::load().unwrap();
    let m = r.by_mic(&mic).expect("XTKS present");
    let e = &cs["expect"];
    assert_eq!(m.mic_type, e["mic_type"].as_str().unwrap());
    assert_eq!(m.operating_mic, e["operating_mic"].as_str().unwrap());
}

#[test]
fn contract_lookup_missing() {
    let c = contract();
    let cs = case(&c, "lookup_missing");
    let mic = args_one(cs);
    assert!(Registry::load().unwrap().by_mic(&mic).is_none());
}

#[test]
fn contract_segments_xjpx_contains_xtks() {
    let c = contract();
    let cs = case(&c, "segments_xjpx_contains_xtks");
    let parent = args_one(cs);
    let want_mic = cs["expect_contains"]["mic"].as_str().unwrap();
    let r = Registry::load().unwrap();
    let segs = r.segments(&parent);
    assert!(segs.iter().any(|s| s.mic == want_mic),
            "{} not in segments of {}", want_mic, parent);
}

#[test]
fn contract_segments_xjpx_not_empty() {
    assert!(!Registry::load().unwrap().segments("XJPX").is_empty());
}

#[test]
fn contract_parent_xtks() {
    let c = contract();
    let cs = case(&c, "parent_xtks");
    let mic = args_one(cs);
    let want = cs["expect"].as_str().unwrap();
    assert_eq!(Registry::load().unwrap().operating_mic(&mic), Some(want));
}

#[test]
fn contract_parent_of_operating_is_self() {
    let c = contract();
    let cs = case(&c, "parent_of_operating_is_self");
    let mic = args_one(cs);
    let want = cs["expect"].as_str().unwrap();
    assert_eq!(Registry::load().unwrap().operating_mic(&mic), Some(want));
}

#[test]
fn contract_expired_since_2024() {
    let c = contract();
    let cs = case(&c, "expired_since_2024");
    let since = args_one(cs);
    let min = cs["expect_count_min"].as_u64().unwrap() as usize;
    let want_status = cs["expect_all_status"].as_str().unwrap();
    let floor = cs["expect_all_expiration_ge"].as_str().unwrap();

    let r = Registry::load().unwrap();
    let rows = r.expired(Some(&since));
    assert!(rows.len() >= min, "count {} < {}", rows.len(), min);
    for m in &rows {
        assert_eq!(m.status, want_status);
        let d = m.expiration_date.as_deref().unwrap_or("");
        assert!(d >= floor, "{} < {}", d, floor);
    }
}

#[test]
fn contract_search_nasdaq() {
    let c = contract();
    let cs = case(&c, "search_nasdaq_count");
    let q = args_one(cs);
    let min = cs["expect_count_min"].as_u64().unwrap() as usize;
    assert!(Registry::load().unwrap().search(&q).len() >= min);
}

#[test]
fn contract_by_country_us() {
    let c = contract();
    let cs = case(&c, "list_by_country_us");
    let code = args_one(cs);
    let min = cs["expect_count_min"].as_u64().unwrap() as usize;
    let want = cs["expect_all_field"]["country_code"].as_str().unwrap();

    let r = Registry::load().unwrap();
    let rows = r.by_country(&code);
    assert!(rows.len() >= min, "count {} < {}", rows.len(), min);
    for m in &rows {
        assert_eq!(m.country_code.as_deref(), Some(want));
    }
}

#[test]
fn contract_by_status_active() {
    let c = contract();
    let cs = case(&c, "list_by_status_active");
    let status = args_one(cs);
    let min = cs["expect_count_min"].as_u64().unwrap() as usize;
    let want = cs["expect_all_field"]["status"].as_str().unwrap();

    let r = Registry::load().unwrap();
    let rows = r.by_status(&status);
    assert!(rows.len() >= min);
    for m in &rows {
        assert_eq!(m.status, want);
    }
}

#[test]
fn contract_by_mic_type_segment() {
    let c = contract();
    let cs = case(&c, "list_by_mic_type_segment");
    let t = args_one(cs);
    let min = cs["expect_count_min"].as_u64().unwrap() as usize;
    let want = cs["expect_all_field"]["mic_type"].as_str().unwrap();

    let r = Registry::load().unwrap();
    let rows = r.by_mic_type(&t);
    assert!(rows.len() >= min);
    for m in &rows {
        assert_eq!(m.mic_type, want);
    }
}

#[test]
fn contract_validate_all_present() {
    let c = contract();
    let cs = case(&c, "validate_all_present");
    let mics = args_list(cs);
    let want_ok = cs["expect_ok"].as_bool().unwrap();

    let r = Registry::load().unwrap();
    let refs: Vec<&str> = mics.iter().map(|s| s.as_str()).collect();
    let (ok, missing) = r.validate(refs);
    assert_eq!(ok, want_ok);
    assert!(missing.is_empty());
}

#[test]
fn contract_validate_missing() {
    let c = contract();
    let cs = case(&c, "validate_missing_returns_false");
    let mics = args_list(cs);
    let want_ok = cs["expect_ok"].as_bool().unwrap();
    let want_missing: Vec<&str> = cs["expect_missing"]
        .as_array().unwrap().iter()
        .map(|v| v.as_str().unwrap()).collect();

    let r = Registry::load().unwrap();
    let refs: Vec<&str> = mics.iter().map(|s| s.as_str()).collect();
    let (ok, missing) = r.validate(refs);
    assert_eq!(ok, want_ok);
    assert_eq!(missing, want_missing);
}

// --- case-insensitivity ---

#[test]
fn by_mic_is_case_insensitive() {
    let r = Registry::load().unwrap();
    let lower = r.by_mic("xnys").expect("lowercase lookup");
    let upper = r.by_mic("XNYS").expect("uppercase lookup");
    assert_eq!(lower.mic, upper.mic);
}
