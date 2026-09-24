# iso10383-registry (JavaScript)

JavaScript wrapper for the [ISO 10383 MIC registry](https://github.com/slimissa/iso10383).

```javascript
const { MICRegistry } = require("iso10383-registry");

const reg = new MICRegistry();               // bundled snapshot
const xnys = reg.byMic("XNYS");
console.log(xnys.mic_type, xnys.country_code);  // OPERATING US

for (const seg of reg.segments("XJPX")) {
  console.log(seg.mic);
}

console.log(reg.operatingMic("XTKS"));       // XJPX
console.log(reg.expired("2024-01-01").length);

No dependencies. No network. The bundled snapshot ships with the package.
