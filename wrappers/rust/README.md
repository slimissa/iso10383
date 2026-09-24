# iso10383-registry (Rust)

Rust wrapper for the [ISO 10383 MIC registry](https://github.com/slimissa/iso10383).

```rust
use iso10383_registry::Registry;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let reg = Registry::load()?;                  // bundled snapshot

    let xnys = reg.by_mic("XNYS").unwrap();
    println!("{} {}", xnys.mic_type, xnys.country_code.as_deref().unwrap_or(""));
    // OPERATING US

    for seg in reg.segments("XJPX") {
        println!("{}", seg.mic);
    }

    println!("{:?}", reg.operating_mic("XTKS"));  // Some("XJPX")
    println!("{}", reg.expired(Some("2024-01-01")).len());

    Ok(())
}

No runtime file dependency. The snapshot is embedded via include_str!.
