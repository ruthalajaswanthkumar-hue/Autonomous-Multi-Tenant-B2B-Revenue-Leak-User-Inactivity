# Evidence and Claim Policy

| Label | Meaning in this repository |
|---|---|
| **Implemented** | Present in code/schema/workflow artifacts |
| **Tested** | Executed by automated tests |
| **Synthetic benchmark** | Evaluated on generated, explicitly labeled fixtures |
| **Production** | Requires observed live-system evidence; none is claimed here |
| **Client outcome** | Requires attributable evidence and permission; none is claimed here |

## Current evidence

- The Python core, HTTP contract, workflow JSON contracts and PostgreSQL persistence are implemented and tested.
- The benchmark is reproducible but entirely synthetic. Perfect fixture metrics mean the fixtures match the encoded requirements; they do not demonstrate generalization.
- Workflow screenshots show design structure only.
- Provider integrations have not been authenticated and executed during this pass.
- No recovered-revenue, ROI, payback, customer-result, production SLA or coverage claim is supported by this repository.

A future production claim needs a frozen rule version, authoritative contract labels, invoice/usage windows, source freshness, currencies, adjudicated false positives, an evaluation period and a clear distinction between detected impact, confirmed leakage and cash actually recovered.
