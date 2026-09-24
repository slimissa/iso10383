package iso10383

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// fixture-anchor rule: tests read every expected value from the shared
// contract file. Nothing in this file hardcodes a MIC, count, or
// country code; the fixture drives every assertion.

type contract struct {
	Cases []map[string]any `json:"cases"`
}

func loadContract(t *testing.T) map[string]map[string]any {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	p := filepath.Join(filepath.Dir(thisFile), "..", "..",
		"tests", "cross_language_consistency.json")
	b, err := os.ReadFile(p)
	if err != nil {
		t.Fatalf("read fixture %s: %v", p, err)
	}
	var c contract
	if err := json.Unmarshal(b, &c); err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	out := map[string]map[string]any{}
	for _, item := range c.Cases {
		id, _ := item["id"].(string)
		if id == "" {
			t.Fatal("fixture case missing id")
		}
		out[id] = item
	}
	return out
}

func load(t *testing.T) *Registry {
	t.Helper()
	r, err := LoadRegistry()
	if err != nil {
		t.Fatalf("LoadRegistry: %v", err)
	}
	return r
}

// --- shape of the bundled snapshot ---

func TestLoadBundled(t *testing.T) {
	r := load(t)
	if r.Len() == 0 {
		t.Fatal("bundled registry is empty")
	}
	if r.Meta().Version != "0.1.0" {
		t.Fatalf("version: %s", r.Meta().Version)
	}
	if !strings.HasPrefix(r.Meta().SourceHash, "sha256:") {
		t.Fatalf("source_hash: %s", r.Meta().SourceHash)
	}
	if len(r.Meta().BrokenChains) != 0 {
		t.Fatalf("broken chains: %d", len(r.Meta().BrokenChains))
	}
}

func TestLoadFromFile(t *testing.T) {
	_, thisFile, _, _ := runtime.Caller(0)
	root := filepath.Join(filepath.Dir(thisFile), "..", "..")
	r, err := LoadRegistryFromFile(filepath.Join(root, "iso10383.json"))
	if err != nil {
		t.Fatalf("LoadRegistryFromFile: %v", err)
	}
	if r.Len() == 0 {
		t.Fatal("empty registry from file")
	}
}

func TestLoadRejectsGarbage(t *testing.T) {
	if _, err := LoadRegistryFromBytes([]byte("not json")); err == nil {
		t.Fatal("expected error for non-JSON")
	}
	if _, err := LoadRegistryFromBytes([]byte(`{"mics":[]}`)); err == nil {
		t.Fatal("expected error for missing meta")
	}
}

func TestCountsAddUp(t *testing.T) {
	r := load(t)
	c := r.Meta().Counts
	if c.Operating+c.Segment != c.Total {
		t.Fatalf("mic_type counts: %d + %d != %d",
			c.Operating, c.Segment, c.Total)
	}
	if c.Active+c.Updated+c.Expired != c.Total {
		t.Fatalf("status counts: %d + %d + %d != %d",
			c.Active, c.Updated, c.Expired, c.Total)
	}
}

// --- contract fixture cases ---

func TestContractLookupXNYS(t *testing.T) {
	c := loadContract(t)["lookup_xnys"]
	mic := c["args"].([]any)[0].(string)
	m := load(t).ByMIC(mic)
	if m == nil {
		t.Fatalf("%s missing", mic)
	}
	expect := c["expect"].(map[string]any)
	if m.MIC != expect["mic"].(string) {
		t.Fatalf("mic: %s", m.MIC)
	}
	if m.MICType != expect["mic_type"].(string) {
		t.Fatalf("mic_type: %s", m.MICType)
	}
	if m.CountryCode == nil || *m.CountryCode != expect["country_code"].(string) {
		t.Fatalf("country: %v", m.CountryCode)
	}
	if m.OperatingMIC != expect["operating_mic"].(string) {
		t.Fatalf("operating_mic: %s", m.OperatingMIC)
	}
}

func TestContractLookupXTKS(t *testing.T) {
	c := loadContract(t)["lookup_xtks"]
	mic := c["args"].([]any)[0].(string)
	m := load(t).ByMIC(mic)
	if m == nil {
		t.Fatalf("%s missing", mic)
	}
	expect := c["expect"].(map[string]any)
	if m.MICType != expect["mic_type"].(string) {
		t.Fatalf("mic_type: %s", m.MICType)
	}
	if m.OperatingMIC != expect["operating_mic"].(string) {
		t.Fatalf("operating_mic: %s", m.OperatingMIC)
	}
}

func TestContractLookupMissing(t *testing.T) {
	c := loadContract(t)["lookup_missing"]
	mic := c["args"].([]any)[0].(string)
	if load(t).ByMIC(mic) != nil {
		t.Fatalf("%s should be nil", mic)
	}
}

func TestContractSegmentsXJPXContainsXTKS(t *testing.T) {
	c := loadContract(t)["segments_xjpx_contains_xtks"]
	parent := c["args"].([]any)[0].(string)
	want := c["expect_contains"].(map[string]any)
	wantMIC := want["mic"].(string)
	for _, s := range load(t).Segments(parent) {
		if s.MIC == wantMIC {
			return
		}
	}
	t.Fatalf("%s not in segments of %s", wantMIC, parent)
}

func TestContractSegmentsXJPXNotEmpty(t *testing.T) {
	if len(load(t).Segments("XJPX")) == 0 {
		t.Fatal("XJPX has no children")
	}
}

func TestContractParentXTKS(t *testing.T) {
	c := loadContract(t)["parent_xtks"]
	mic := c["args"].([]any)[0].(string)
	want := c["expect"].(string)
	if got := load(t).OperatingMIC(mic); got != want {
		t.Fatalf("%s parent: %s != %s", mic, got, want)
	}
}

func TestContractParentOfOperatingIsSelf(t *testing.T) {
	c := loadContract(t)["parent_of_operating_is_self"]
	mic := c["args"].([]any)[0].(string)
	want := c["expect"].(string)
	if got := load(t).OperatingMIC(mic); got != want {
		t.Fatalf("got %s want %s", got, want)
	}
}

func TestContractExpiredSince2024(t *testing.T) {
	c := loadContract(t)["expired_since_2024"]
	since := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	wantStatus := c["expect_all_status"].(string)
	floor := c["expect_all_expiration_ge"].(string)

	rows := load(t).Expired(since)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	for _, m := range rows {
		if m.Status != wantStatus {
			t.Fatalf("status: %s", m.Status)
		}
		d := ""
		if m.ExpirationDate != nil {
			d = *m.ExpirationDate
		}
		if d < floor {
			t.Fatalf("expiration_date %s < %s", d, floor)
		}
	}
}

func TestContractSearchNasdaq(t *testing.T) {
	c := loadContract(t)["search_nasdaq_count"]
	q := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	if len(load(t).Search(q)) < min {
		t.Fatalf("count < %d", min)
	}
}

func TestContractByCountryUS(t *testing.T) {
	c := loadContract(t)["list_by_country_us"]
	code := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)["country_code"].(string)

	rows := load(t).ByCountry(code)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	for _, m := range rows {
		if m.CountryCode == nil || *m.CountryCode != want {
			t.Fatalf("country: %v", m.CountryCode)
		}
	}
}

func TestContractByStatusActive(t *testing.T) {
	c := loadContract(t)["list_by_status_active"]
	status := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)["status"].(string)

	rows := load(t).ByStatus(status)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	for _, m := range rows {
		if m.Status != want {
			t.Fatalf("status: %s", m.Status)
		}
	}
}

func TestContractByMICTypeSegment(t *testing.T) {
	c := loadContract(t)["list_by_mic_type_segment"]
	mt := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)["mic_type"].(string)

	rows := load(t).ByMICType(mt)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	for _, m := range rows {
		if m.MICType != want {
			t.Fatalf("mic_type: %s", m.MICType)
		}
	}
}

func TestContractValidateAllPresent(t *testing.T) {
	c := loadContract(t)["validate_all_present"]
	args := c["args"].([]any)[0].([]any)
	mics := make([]string, len(args))
	for i, a := range args {
		mics[i] = a.(string)
	}
	want := c["expect_ok"].(bool)
	ok, missing := load(t).Validate(mics)
	if ok != want {
		t.Fatalf("ok = %v, want %v", ok, want)
	}
	if len(missing) != 0 {
		t.Fatalf("missing: %v", missing)
	}
}

func TestContractValidateMissing(t *testing.T) {
	c := loadContract(t)["validate_missing_returns_false"]
	args := c["args"].([]any)[0].([]any)
	mics := make([]string, len(args))
	for i, a := range args {
		mics[i] = a.(string)
	}
	wantOK := c["expect_ok"].(bool)
	wantMissing := c["expect_missing"].([]any)

	ok, missing := load(t).Validate(mics)
	if ok != wantOK {
		t.Fatalf("ok = %v, want %v", ok, wantOK)
	}
	if len(missing) != len(wantMissing) {
		t.Fatalf("missing count %d != %d", len(missing), len(wantMissing))
	}
	for i, m := range wantMissing {
		if missing[i] != m.(string) {
			t.Fatalf("missing[%d] = %s, want %s", i, missing[i], m.(string))
		}
	}
}

// --- copy semantics ---

func TestByMICReturnsCopy(t *testing.T) {
	r := load(t)
	a := r.ByMIC("XNYS")
	b := r.ByMIC("XNYS")
	if a == nil || b == nil {
		t.Fatal("XNYS missing")
	}
	if a == b {
		t.Fatal("expected distinct pointers")
	}
	// Mutating a must not affect the registry.
	a.MIC = "ZZZZ"
	c := r.ByMIC("XNYS")
	if c == nil || c.MIC != "XNYS" {
		t.Fatal("registry mutated by caller")
	}
}

func TestAllReturnsDefensiveCopy(t *testing.T) {
	r := load(t)
	rows := r.All()
	n := len(rows)
	rows = append(rows, rows[0])
	if len(r.All()) != n {
		t.Fatal("All() result aliased the registry")
	}
}
