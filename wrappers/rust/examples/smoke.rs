//! End-to-end smoke test. Run with:
//!   cargo run --example smoke --quiet

use iso10383_registry::Registry;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let r = Registry::load()?;
    println!("version: {}", r.meta().version);
    println!("mics: {}", r.len());
    println!("XNYS: {}", r.by_mic("XNYS").unwrap().mic_type);
    println!("XTKS parent: {}", r.operating_mic("XTKS").unwrap());
    println!("expired since 2024: {}", r.expired(Some("2024-01-01")).len());
    println!("search nasdaq: {}", r.search("nasdaq").len());
    Ok(())
}
