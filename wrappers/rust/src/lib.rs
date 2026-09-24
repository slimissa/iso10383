//! iso10383-registry - Rust wrapper for the ISO 10383 MIC registry.
//!
//! Load the bundled snapshot with [`Registry::load`], or read a
//! snapshot from disk with [`Registry::load_from_file`].
//!
//! The registry is read-only and cheap to construct. Lookups return
//! borrowed references, so the snapshot is loaded once and shared.

use serde::Deserialize;
use std::collections::HashMap;

const BUNDLED: &str = include_str!("../data/iso10383.json");

/// One entry of the registry.
///
/// Every JSON key that can be `null` in the source is an `Option`.
/// `#[serde(default)]` keeps deserialization tolerant when a key is
/// missing entirely.
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct MIC {
    pub mic: String,
    pub mic_type: String,
    pub status: String,
    pub operating_mic: String,

    #[serde(default)] pub market_name: Option<String>,
    #[serde(default)] pub legal_entity_name: Option<String>,
    #[serde(default)] pub lei: Option<String>,
    #[serde(default)] pub market_category: Option<String>,
    #[serde(default)] pub acronym: Option<String>,
    #[serde(default)] pub country_code: Option<String>,
    #[serde(default)] pub city: Option<String>,
    #[serde(default)] pub website: Option<String>,
    #[serde(default)] pub creation_date: Option<String>,
    #[serde(default)] pub last_update_date: Option<String>,
    #[serde(default)] pub last_validation_date: Option<String>,
    #[serde(default)] pub expiration_date: Option<String>,
    #[serde(default)] pub note: Option<String>,
}

/// A segment whose parent chain does not terminate at an operating MIC.
/// The bundled snapshot has zero of these.
#[derive(Debug, Clone, Deserialize, Default, PartialEq, Eq)]
pub struct BrokenChain {
    pub mic: String,
    pub operating_mic: String,
    pub reason: String,
    #[serde(default)] pub chain: Vec<String>,
}

/// Counts from `meta.counts`.
#[derive(Debug, Clone, Deserialize, Default, PartialEq, Eq)]
pub struct Counts {
    pub operating: u32,
    pub segment: u32,
    pub active: u32,
    pub updated: u32,
    pub expired: u32,
    pub total: u32,
}

/// Registry metadata.
#[derive(Debug, Clone, Deserialize, Default, PartialEq, Eq)]
pub struct Meta {
    pub version: String,
    pub updated: String,
    pub source_snapshot: String,
    pub source_url: String,
    pub source_hash: String,
    pub counts: Counts,
    #[serde(default)] pub broken_chains: Vec<BrokenChain>,
}

#[derive(Debug, Deserialize)]
struct Raw {
    meta: Meta,
    mics: Vec<MIC>,
}

/// Read-only view over a MIC snapshot.
#[derive(Debug)]
pub struct Registry {
    meta: Meta,
    mics: Vec<MIC>,
    by_mic: HashMap<String, usize>,
}

impl Registry {
    /// Load the bundled snapshot.
    pub fn load() -> Result<Self, serde_json::Error> {
        Self::from_str(BUNDLED)
    }

    /// Load a snapshot from a file on disk.
    pub fn load_from_file<P: AsRef<std::path::Path>>(
        path: P,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let s = std::fs::read_to_string(path)?;
        Ok(Self::from_str(&s)?)
    }

    /// Parse a snapshot from a JSON string.
    pub fn from_str(s: &str) -> Result<Self, serde_json::Error> {
        let raw: Raw = serde_json::from_str(s)?;
        if raw.meta.version.is_empty() {
            return Err(serde::de::Error::custom("missing meta.version"));
        }
        let mut by_mic = HashMap::with_capacity(raw.mics.len());
        for (i, m) in raw.mics.iter().enumerate() {
            by_mic.insert(m.mic.clone(), i);
        }
        Ok(Self { meta: raw.meta, mics: raw.mics, by_mic })
    }

    /// Snapshot metadata.
    pub fn meta(&self) -> &Meta { &self.meta }

    /// Number of entries.
    pub fn len(&self) -> usize { self.mics.len() }

    /// Whether the registry is empty.
    pub fn is_empty(&self) -> bool { self.mics.is_empty() }

    /// Every entry, in the source order.
    pub fn all(&self) -> &[MIC] { &self.mics }

    /// Look up a MIC. Case-insensitive.
    pub fn by_mic(&self, mic: &str) -> Option<&MIC> {
        self.by_mic
            .get(&mic.to_ascii_uppercase())
            .map(|i| &self.mics[*i])
    }

    /// Direct children of an operating MIC.
    ///
    /// A grandchild whose parent is another segment is not listed here.
    /// Walk with [`Self::operating_mic`] for multi-level chains.
    pub fn segments(&self, mic: &str) -> Vec<&MIC> {
        let u = mic.to_ascii_uppercase();
        self.mics
            .iter()
            .filter(|m| m.mic_type == "SEGMENT" && m.operating_mic == u)
            .collect()
    }

    /// The `operating_mic` field of a MIC.
    ///
    /// Operating MICs self-reference (D3).
    pub fn operating_mic(&self, mic: &str) -> Option<&str> {
        self.by_mic(mic).map(|m| m.operating_mic.as_str())
    }

    /// Expired entries, sorted by `expiration_date` ascending.
    ///
    /// Pass `None` for every expired entry.
    pub fn expired(&self, since: Option<&str>) -> Vec<&MIC> {
        let mut rows: Vec<&MIC> = self
            .mics
            .iter()
            .filter(|m| m.status == "EXPIRED")
            .filter(|m| match since {
                None => true,
                Some(s) => m.expiration_date.as_deref().unwrap_or("") >= s,
            })
            .collect();
        rows.sort_by(|a, b| {
            a.expiration_date
                .as_deref()
                .unwrap_or("")
                .cmp(b.expiration_date.as_deref().unwrap_or(""))
        });
        rows
    }

    /// Entries whose ISO 3166 alpha-2 country matches `code`.
    pub fn by_country(&self, code: &str) -> Vec<&MIC> {
        let u = code.to_ascii_uppercase();
        self.mics
            .iter()
            .filter(|m| m.country_code.as_deref() == Some(u.as_str()))
            .collect()
    }

    /// Entries whose status matches `status`.
    pub fn by_status(&self, status: &str) -> Vec<&MIC> {
        let u = status.to_ascii_uppercase();
        self.mics.iter().filter(|m| m.status == u).collect()
    }

    /// Entries whose `mic_type` matches `mic_type`.
    pub fn by_mic_type(&self, mic_type: &str) -> Vec<&MIC> {
        let u = mic_type.to_ascii_uppercase();
        self.mics.iter().filter(|m| m.mic_type == u).collect()
    }

    /// Entries whose `market_category` matches `category`.
    pub fn by_category(&self, category: &str) -> Vec<&MIC> {
        self.mics
            .iter()
            .filter(|m| m.market_category.as_deref() == Some(category))
            .collect()
    }

    /// Case-insensitive substring search on `market_name` and `acronym`.
    pub fn search(&self, q: &str) -> Vec<&MIC> {
        let q = q.to_lowercase();
        self.mics
            .iter()
            .filter(|m| {
                m.market_name
                    .as_deref()
                    .unwrap_or("")
                    .to_lowercase()
                    .contains(&q)
                    || m.acronym
                        .as_deref()
                        .unwrap_or("")
                        .to_lowercase()
                        .contains(&q)
            })
            .collect()
    }

    /// Check that every MIC exists.
    ///
    /// Returns `(ok, missing)` where `missing` preserves the input
    /// order.
    pub fn validate<'a, I>(&self, mics: I) -> (bool, Vec<&'a str>)
    where
        I: IntoIterator<Item = &'a str>,
    {
        let mut missing = Vec::new();
        for m in mics {
            if !self.by_mic.contains_key(&m.to_ascii_uppercase()) {
                missing.push(m);
            }
        }
        (missing.is_empty(), missing)
    }
}
