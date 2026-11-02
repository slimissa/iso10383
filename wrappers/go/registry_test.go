package iso10383

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
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
	if len(out) != len(c.Cases) {
		t.Fatalf("duplicate case id in %s: %d cases, %d unique",
			p, len(c.Cases), len(out))
	}
	return out
}

// assertAllFields checks every key of expect_all_field against m. MIC is
// read through its JSON tags, so a field name that is not a MIC field
// fails the test instead of being skipped.
func assertAllFields(t *testing.T, m MIC, want map[string]any) {
	t.Helper()
	b, err := json.Marshal(m)
	if err != nil {
		t.Fatalf("marshal MIC: %v", err)
	}
	var got map[string]any
	if err := json.Unmarshal(b, &got); err != nil {
		t.Fatalf("unmarshal MIC: %v", err)
	}
	for field, w := range want {
		g, ok := got[field]
		if !ok {
			t.Fatalf("unknown field %q in expect_all_field", field)
		}
		if g != w {
			t.Fatalf("%s: %v != %v", field, g, w)
		}
	}
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
	_, thisFile, _, _ := runtime.Caller(0)
	versionBytes, err := os.ReadFile(filepath.Join(
		filepath.Dir(thisFile), "..", "..", "VERSION"))
	if err != nil {
		t.Fatalf("read VERSION: %v", err)
	}
	wantVersion := strings.TrimSpace(string(versionBytes))
	if r.Meta().Version != wantVersion {
		t.Fatalf("version: %s != %s", r.Meta().Version, wantVersion)
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
	want := c["expect_all_field"].(map[string]any)

	rows := load(t).ByCountry(code)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	// Loop over every key so a future case with two fields is checked on
	// all of them, matching Python and JavaScript's drivers.
	for _, m := range rows {
		assertAllFields(t, m, want)
	}
}

func TestContractByStatusActive(t *testing.T) {
	c := loadContract(t)["list_by_status_active"]
	status := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)

	rows := load(t).ByStatus(status)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	// Loop over every key so a future case with two fields is checked on
	// all of them, matching Python and JavaScript's drivers.
	for _, m := range rows {
		assertAllFields(t, m, want)
	}
}

func TestContractByMICTypeSegment(t *testing.T) {
	c := loadContract(t)["list_by_mic_type_segment"]
	mt := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)

	rows := load(t).ByMICType(mt)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	// Loop over every key so a future case with two fields is checked on
	// all of them, matching Python and JavaScript's drivers.
	for _, m := range rows {
		assertAllFields(t, m, want)
	}
}

func TestContractExpiredTieOrderStable(t *testing.T) {
	c := loadContract(t)["expired_tie_order_stable"]
	since := c["args"].([]any)[0].(string)
	by := c["expect_order_by"].([]any)
	if len(by) != 2 || by[0] != "expiration_date" || by[1] != "mic" {
		t.Fatalf("unsupported expect_order_by: %v", c["expect_order_by"])
	}
	r := load(t)
	date := func(p *string) string {
		if p == nil {
			return ""
		}
		return *p
	}
	rows := r.Expired(since)
	for i := 1; i < len(rows); i++ {
		a, b := rows[i-1], rows[i]
		da, db := date(a.ExpirationDate), date(b.ExpirationDate)
		if da > db || (da == db && a.MIC >= b.MIC) {
			t.Fatalf("%s must precede %s (dates %s, %s)", b.MIC, a.MIC, db, da)
		}
	}
}

func TestContractExpiredTieBreakIsMIC(t *testing.T) {
	c := loadContract(t)["expired_tie_break_mic_synthetic"]
	since := c["args"].([]any)[0].(string)
	b, err := json.Marshal(c["registry"])
	if err != nil {
		t.Fatal(err)
	}
	r, err := LoadRegistryFromBytes(b)
	if err != nil {
		t.Fatalf("LoadRegistryFromBytes: %v", err)
	}
	var got []string
	for _, m := range r.Expired(since) {
		got = append(got, m.MIC)
	}
	var want []string
	for _, v := range c["expect_mic_order"].([]any) {
		want = append(want, v.(string))
	}
	if strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("expired order %v, want %v", got, want)
	}
}

func TestContractLookupLowercase(t *testing.T) {
	c := loadContract(t)["lookup_lowercase"]
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

func TestContractSegmentsLowercase(t *testing.T) {
	c := loadContract(t)["segments_lowercase"]
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

func TestContractByStatusLowercase(t *testing.T) {
	c := loadContract(t)["by_status_lowercase"]
	status := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)

	rows := load(t).ByStatus(status)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	// Loop over every key so a future case with two fields is checked on
	// all of them, matching Python and JavaScript's drivers.
	for _, m := range rows {
		assertAllFields(t, m, want)
	}
}

func TestContractByCategoryRMKT(t *testing.T) {
	c := loadContract(t)["by_category_rmkt"]
	category := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)

	rows := load(t).ByCategory(category)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	// Loop over every key so a future case with two fields is checked on
	// all of them, matching Python and JavaScript's drivers.
	for _, m := range rows {
		assertAllFields(t, m, want)
	}
}

func TestContractByCategoryLowercase(t *testing.T) {
	c := loadContract(t)["by_category_lowercase"]
	category := c["args"].([]any)[0].(string)
	min := int(c["expect_count_min"].(float64))
	want := c["expect_all_field"].(map[string]any)

	rows := load(t).ByCategory(category)
	if len(rows) < min {
		t.Fatalf("count %d < %d", len(rows), min)
	}
	// Loop over every key so a future case with two fields is checked on
	// all of them, matching Python and JavaScript's drivers.
	for _, m := range rows {
		assertAllFields(t, m, want)
	}
}

func TestContractValidateLowercaseInput(t *testing.T) {
	c := loadContract(t)["validate_lowercase_input"]
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
	// Mutating a value field of a must not affect the registry.
	a.MIC = "ZZZZ"
	c := r.ByMIC("XNYS")
	if c == nil || c.MIC != "XNYS" {
		t.Fatal("registry mutated by caller")
	}
}

// ByMIC returns a deep copy: value fields and pointer fields are both
// independent of the registry, so writing through a returned pointer
// cannot change a later lookup.
func TestByMICReturnsDeepCopy(t *testing.T) {
	r := load(t)
	mic := loadContract(t)["lookup_xnys"]["args"].([]any)[0].(string)
	a := r.ByMIC(mic)
	b := r.ByMIC(mic)
	if a == nil || b == nil {
		t.Fatalf("%s missing", mic)
	}
	if a == b {
		t.Fatal("expected distinct pointers")
	}
	a.MIC = "ZZZZ"
	if b.MIC != mic {
		t.Fatal("value field was shared between returned structs")
	}
	if a.MarketName == nil || b.MarketName == nil {
		t.Fatal("fixture entry has no market_name to test with")
	}
	if a.MarketName == b.MarketName {
		t.Fatal("pointer field was shared between returned structs")
	}
	want := *b.MarketName
	*a.MarketName = "x"
	if got := *r.ByMIC(mic).MarketName; got != want {
		t.Fatalf("write through ByMIC result reached the registry: %q != %q",
			got, want)
	}
	if *b.MarketName != want {
		t.Fatal("write through one result reached another result")
	}
}

// ptrFields returns the address of every *string field of m, found by
// reflection so a *string field added to MIC later is covered without
// editing this helper.
func ptrFields(m *MIC) []**string {
	var out []**string
	v := reflect.ValueOf(m).Elem()
	want := reflect.TypeOf((*string)(nil))
	for i := 0; i < v.NumField(); i++ {
		if v.Field(i).Type() == want {
			out = append(out, v.Field(i).Addr().Interface().(**string))
		}
	}
	return out
}

// A *string field added to MIC but not to cloneMIC would alias the
// registry again. This fails until cloneMIC copies it.
func TestCloneMICCopiesEveryPointerField(t *testing.T) {
	var m MIC
	fields := ptrFields(&m)
	if len(fields) == 0 {
		t.Fatal("MIC has no *string fields; the test lost its target")
	}
	for i, f := range fields {
		s := "v" + string(rune('a'+i))
		*f = &s
	}
	c := cloneMIC(m)
	for i, f := range ptrFields(&c) {
		orig := ptrFields(&m)[i]
		if *f == nil || *f == *orig {
			t.Fatalf("pointer field %d not deep-copied", i)
		}
		if **f != **orig {
			t.Fatalf("pointer field %d changed value: %q != %q", i, **f, **orig)
		}
	}
}

// Every slice-returning query hands back deep copies: scribbling over
// each *string in a result must leave the registry unchanged.
func TestQueryResultsAreDeepCopies(t *testing.T) {
	r := load(t)
	before := r.All()

	var seg, withCountry, withCategory, withName MIC
	var haveSeg, haveCountry, haveCategory, haveName bool
	for _, m := range before {
		if !haveSeg && m.MICType == "SEGMENT" {
			seg, haveSeg = m, true
		}
		if !haveCountry && m.CountryCode != nil {
			withCountry, haveCountry = m, true
		}
		if !haveCategory && m.MarketCategory != nil {
			withCategory, haveCategory = m, true
		}
		if !haveName && m.MarketName != nil && *m.MarketName != "" {
			withName, haveName = m, true
		}
	}
	if !(haveSeg && haveCountry && haveCategory && haveName) {
		t.Fatal("registry lacks an entry needed to drive every query")
	}

	queries := []struct {
		name string
		run  func() []MIC
	}{
		{"All", r.All},
		{"Segments", func() []MIC { return r.Segments(seg.OperatingMIC) }},
		{"Expired", func() []MIC { return r.Expired("") }},
		{"ByCountry", func() []MIC { return r.ByCountry(*withCountry.CountryCode) }},
		{"ByStatus", func() []MIC { return r.ByStatus(before[0].Status) }},
		{"ByMICType", func() []MIC { return r.ByMICType(before[0].MICType) }},
		{"ByCategory", func() []MIC { return r.ByCategory(*withCategory.MarketCategory) }},
		{"Search", func() []MIC { return r.Search(*withName.MarketName) }},
	}
	for _, q := range queries {
		rows := q.run()
		if len(rows) == 0 {
			t.Fatalf("%s: no rows returned to test with", q.name)
		}
		scribbled := 0
		for i := range rows {
			for _, f := range ptrFields(&rows[i]) {
				if *f != nil {
					**f = "scribbled"
					scribbled++
				}
			}
		}
		if scribbled == 0 {
			t.Fatalf("%s: no pointer fields to write through", q.name)
		}
		if !reflect.DeepEqual(before, r.All()) {
			t.Fatalf("%s: a write through the result changed the registry", q.name)
		}
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
