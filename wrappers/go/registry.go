// Package iso10383 is the Go wrapper for the ISO 10383 MIC registry.
//
// Construct with LoadRegistry() for the bundled snapshot, or
// LoadRegistryFromFile(path) to read a snapshot from disk.
package iso10383

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
)

//go:embed data/iso10383.json
var bundled []byte

// MIC is one entry of the registry. Fields that the source file may
// leave empty are pointers so that JSON null maps to a nil pointer
// rather than the zero value.
type MIC struct {
	MIC                string  `json:"mic"`
	MICType            string  `json:"mic_type"`
	Status             string  `json:"status"`
	OperatingMIC       string  `json:"operating_mic"`
	MarketName         *string `json:"market_name"`
	LegalEntityName    *string `json:"legal_entity_name"`
	LEI                *string `json:"lei"`
	MarketCategory     *string `json:"market_category"`
	Acronym            *string `json:"acronym"`
	CountryCode        *string `json:"country_code"`
	City               *string `json:"city"`
	Website            *string `json:"website"`
	CreationDate       *string `json:"creation_date"`
	LastUpdateDate     *string `json:"last_update_date"`
	LastValidationDate *string `json:"last_validation_date"`
	ExpirationDate     *string `json:"expiration_date"`
	Note               *string `json:"note"`
}

// BrokenChain records a segment whose parent chain does not terminate
// at an operating MIC. The bundled snapshot has zero of these.
type BrokenChain struct {
	MIC          string   `json:"mic"`
	OperatingMIC string   `json:"operating_mic"`
	Reason       string   `json:"reason"`
	Chain        []string `json:"chain"`
}

// Counts mirrors meta.counts.
type Counts struct {
	Operating int `json:"operating"`
	Segment   int `json:"segment"`
	Active    int `json:"active"`
	Updated   int `json:"updated"`
	Expired   int `json:"expired"`
	Total     int `json:"total"`
}

// Meta mirrors the top-level meta object.
type Meta struct {
	Version        string        `json:"version"`
	Updated        string        `json:"updated"`
	SourceSnapshot string        `json:"source_snapshot"`
	SourceURL      string        `json:"source_url"`
	SourceHash     string        `json:"source_hash"`
	Counts         Counts        `json:"counts"`
	BrokenChains   []BrokenChain `json:"broken_chains"`
}

type raw struct {
	Meta Meta  `json:"meta"`
	MICs []MIC `json:"mics"`
}

// Registry is a read-only view over a MIC snapshot.
type Registry struct {
	meta  Meta
	mics  []MIC
	byMIC map[string]int
}

// LoadRegistry loads the bundled snapshot.
func LoadRegistry() (*Registry, error) {
	return LoadRegistryFromBytes(bundled)
}

// LoadRegistryFromFile loads a snapshot from disk.
func LoadRegistryFromFile(path string) (*Registry, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return LoadRegistryFromBytes(b)
}

// LoadRegistryFromBytes parses a snapshot from a byte slice.
func LoadRegistryFromBytes(b []byte) (*Registry, error) {
	var r raw
	if err := json.Unmarshal(b, &r); err != nil {
		return nil, fmt.Errorf("parse registry: %w", err)
	}
	if r.Meta.Version == "" {
		return nil, fmt.Errorf("snapshot missing meta.version")
	}
	by := make(map[string]int, len(r.MICs))
	for i, m := range r.MICs {
		by[m.MIC] = i
	}
	return &Registry{meta: r.Meta, mics: r.MICs, byMIC: by}, nil
}

// Meta returns the snapshot metadata.
func (r *Registry) Meta() Meta { return r.meta }

// Len is the number of entries.
func (r *Registry) Len() int { return len(r.mics) }

// IsEmpty reports whether the registry has no entries.
func (r *Registry) IsEmpty() bool { return len(r.mics) == 0 }

// All returns a defensive copy of every entry.
func (r *Registry) All() []MIC {
	out := make([]MIC, len(r.mics))
	copy(out, r.mics)
	return out
}

// ByMIC returns a copy of the entry for mic, or nil.
// The lookup is case-insensitive.
func (r *Registry) ByMIC(mic string) *MIC {
	i, ok := r.byMIC[strings.ToUpper(mic)]
	if !ok {
		return nil
	}
	m := r.mics[i]
	return &m
}

// Segments returns the direct children of an operating MIC.
//
// A grandchild whose parent is another segment is not listed here.
// Walk with OperatingMIC for multi-level chains.
func (r *Registry) Segments(mic string) []MIC {
	u := strings.ToUpper(mic)
	var out []MIC
	for _, m := range r.mics {
		if m.MICType == "SEGMENT" && m.OperatingMIC == u {
			out = append(out, m)
		}
	}
	return out
}

// OperatingMIC returns the operating_mic field of mic, or "" if the
// MIC is unknown. Operating MICs self-reference (D3).
func (r *Registry) OperatingMIC(mic string) string {
	if m := r.ByMIC(mic); m != nil {
		return m.OperatingMIC
	}
	return ""
}

// Expired returns expired entries, sorted by expiration_date ascending.
// Pass "" for since to return every expired entry.
func (r *Registry) Expired(since string) []MIC {
	var out []MIC
	for _, m := range r.mics {
		if m.Status != "EXPIRED" {
			continue
		}
		if since != "" {
			d := ""
			if m.ExpirationDate != nil {
				d = *m.ExpirationDate
			}
			if d < since {
				continue
			}
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool {
		di, dj := "", ""
		if out[i].ExpirationDate != nil {
			di = *out[i].ExpirationDate
		}
		if out[j].ExpirationDate != nil {
			dj = *out[j].ExpirationDate
		}
		return di < dj
	})
	return out
}

// ByCountry returns entries whose ISO 3166 alpha-2 country matches code.
func (r *Registry) ByCountry(code string) []MIC {
	u := strings.ToUpper(code)
	var out []MIC
	for _, m := range r.mics {
		if m.CountryCode != nil && *m.CountryCode == u {
			out = append(out, m)
		}
	}
	return out
}

// ByStatus returns entries whose status matches.
func (r *Registry) ByStatus(status string) []MIC {
	u := strings.ToUpper(status)
	var out []MIC
	for _, m := range r.mics {
		if m.Status == u {
			out = append(out, m)
		}
	}
	return out
}

// ByMICType returns entries whose mic_type matches.
func (r *Registry) ByMICType(micType string) []MIC {
	u := strings.ToUpper(micType)
	var out []MIC
	for _, m := range r.mics {
		if m.MICType == u {
			out = append(out, m)
		}
	}
	return out
}

// ByCategory returns entries whose market_category matches.
func (r *Registry) ByCategory(category string) []MIC {
	var out []MIC
	for _, m := range r.mics {
		if m.MarketCategory != nil && *m.MarketCategory == category {
			out = append(out, m)
		}
	}
	return out
}

// Search does a case-insensitive substring match on market_name and
// acronym.
func (r *Registry) Search(q string) []MIC {
	q = strings.ToLower(q)
	var out []MIC
	for _, m := range r.mics {
		name := ""
		if m.MarketName != nil {
			name = strings.ToLower(*m.MarketName)
		}
		acr := ""
		if m.Acronym != nil {
			acr = strings.ToLower(*m.Acronym)
		}
		if strings.Contains(name, q) || strings.Contains(acr, q) {
			out = append(out, m)
		}
	}
	return out
}

// Validate returns ok=true and an empty slice when every MIC exists.
// The second return value lists the MICs that were not found, in the
// order they were given.
func (r *Registry) Validate(mics []string) (bool, []string) {
	var missing []string
	for _, m := range mics {
		if _, ok := r.byMIC[strings.ToUpper(m)]; !ok {
			missing = append(missing, m)
		}
	}
	return len(missing) == 0, missing
}
