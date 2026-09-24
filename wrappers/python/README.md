# iso10383-registry (Python)

Python wrapper for the [ISO 10383 MIC registry](https://github.com/slimissa/iso10383).

```python
from iso10383 import MICRegistry

reg = MICRegistry()                        # bundled snapshot
xnys = reg.by_mic("XNYS")
print(xnys.mic_type, xnys.country_code)    # OPERATING US

for seg in reg.segments("XJPX"):
    print(seg.mic)

print(reg.operating_mic("XTKS"))           # XJPX
print(len(reg.expired(since="2024-01-01")))

No network. The bundled snapshot ships with the package.
