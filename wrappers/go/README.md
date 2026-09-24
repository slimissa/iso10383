# iso10383-registry (Go)

Go wrapper for the [ISO 10383 MIC registry](https://github.com/slimissa/iso10383).

```go
package main

import (
    "fmt"
    iso10383 "github.com/slimissa/iso10383/wrappers/go"
)

func main() {
    reg, err := iso10383.LoadRegistry()   // bundled snapshot
    if err != nil { panic(err) }

    xnys := reg.ByMIC("XNYS")
    fmt.Println(xnys.MICType, *xnys.CountryCode)  // OPERATING US

    for _, seg := range reg.Segments("XJPX") {
        fmt.Println(seg.MIC)
    }

    fmt.Println(reg.OperatingMIC("XTKS"))          // XJPX
    fmt.Println(len(reg.Expired("2024-01-01")))
}

No dependencies outside the standard library. No network. The
bundled snapshot is embedded via //go:embed.
