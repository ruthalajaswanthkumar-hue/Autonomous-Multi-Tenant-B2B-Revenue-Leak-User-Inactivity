# n8n Workflow Contracts

All exports are valid JSON and inactive by default.

| Export | Responsibility |
|---|---|
| `01-stripe-data-sync.json` | Stripe adapter design; live test-mode execution remains unverified |
| `02-usage-collection.json` | idempotent normalized usage ingestion |
| `03-detect-outdated-pricing.json` | invoke the tested pricing rule and persist a finding |
| `04-detect-missing-overages.json` | invoke the tested overage rule and persist a finding |
| `05-daily-summary.json` | summarize stored findings and hand off to notification transport |

Financial rule behavior belongs to `src/revenue_leakage`; it is not duplicated in the detection workflows. Import validation does not establish credential validity, provider semantics or notification delivery.
