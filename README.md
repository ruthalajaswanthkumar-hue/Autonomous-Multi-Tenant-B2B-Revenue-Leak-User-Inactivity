# Revenue Leakage Detection System

> Tested reference implementation for comparing contractual billing expectations with actual charges and returning auditable, versioned evidence.

**Status:** Tested reference implementation / portfolio system
**Domain:** Revenue Operations · Billing Controls · Financial Systems

This repository is not presented as a client deployment. It makes no claim about recovered dollars, return on investment, payback period, production coverage, or live operating performance.

## Implemented system

- Python 3.11 rules for outdated pricing, negotiated customer pricing, missing overages, discount validity and feature-entitlement mismatches.
- Exact Decimal calculations, explicit currency rejection, effective/end dates, grace periods, source freshness and missing-data blocking.
- Structured output from every evaluation: rule ID/version, customer, expected and actual values, difference, impact estimate, severity, evidence, outcome and deterministic finding key.
- Duplicate usage-event validation and duplicate-finding suppression.
- A small FastAPI service used by the n8n pricing and overage orchestration contracts.
- PostgreSQL schema with source provenance, exact financial precision and idempotent finding persistence.
- Frozen synthetic SQL examples and a labeled synthetic benchmark.

## Architecture

```text
Stripe / contracts / product usage
                 |
                 v
        n8n source adapters
                 |
                 v
      canonical PostgreSQL data
                 |
                 v
 deterministic Python rule service
 (Decimal + dates + freshness + evidence)
                 |
                 v
 idempotent findings -> review / Slack summary
```

n8n owns connectors, schedules and notifications. `src/revenue_leakage` owns financial comparisons so they can be run and tested without n8n. See [architecture](./docs/architecture.md), [evidence](./docs/evidence.md), and [reliability controls](./docs/reliability.md).

## Reproduce

Python 3.11:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest
PYTHONPATH=src .venv/bin/python scripts/run_synthetic_benchmark.py
```

The committed `uv.lock` records the full resolved dependency graph; CI installs it with
`uv sync --locked --extra dev`.

Service:

```bash
LEAKAGE_ENGINE_TOKEN=local-secret .venv/bin/python -m revenue_leakage
```

PostgreSQL:

```bash
psql -v ON_ERROR_STOP=1 -f database/schema.sql
psql -v ON_ERROR_STOP=1 -f database/sample-data.sql
```

All n8n exports are inactive by default. Configure platform-managed credentials and the engine URL/token before importing and validating them against a target n8n version.

## Synthetic benchmark

The committed [benchmark set](./benchmarks/synthetic_cases.json) contains 11 deterministic cases. The reproduced artifact reports:

| Metric | Synthetic result |
|---|---:|
| True positives | 4 |
| True negatives | 7 |
| False positives | 0 |
| False negatives | 0 |
| Precision | 1.0000 |
| Recall | 1.0000 |

These figures measure the encoded rules on designed fixtures only. They do not establish performance on unseen contracts, production invoices or real customers. See [the machine-readable result](./results/synthetic_benchmark.json).

## Evidence status

| Item | Label |
|---|---|
| Python rules and service | **Implemented and tested** |
| PostgreSQL schema, sample data and idempotency | **Implemented and tested** |
| n8n JSON imports/contracts | **Implemented artifacts; not live-provider verified** |
| Workflow screenshots | **Design evidence** |
| Benchmark metrics | **Synthetic benchmark** |
| Production detection or recovery | **Not established** |
| Client or business outcome | **Not claimed** |

## Workflow visuals

- [Stripe ingestion design](./docs/01-stripe-data-sync-workflow.jpeg)
- [Usage ingestion design](./docs/02-usage-collection-workflow.jpeg)
- [Pricing-rule design](./docs/03-detect-outdated-pricing-workflow.jpeg)
- [Overage-rule design](./docs/04-detect-missing-overages-workflow.jpeg)
- [Daily summary design](./docs/05-daily-leakage-summary-workflow.jpeg)

The screenshots document the earlier orchestration design and may not match the refactored service boundary node-for-node.

## Remaining deployment work

- Validate Stripe/product adapters and credential scopes against real test-mode accounts.
- Add tenant authorization/RLS for the chosen deployment identity model.
- Add production observability, notification delivery tests and review/approval UX.
- Construct a representative, independently labeled historical evaluation set before making accuracy or value claims.

MIT licensed. Built by **Ugo Chukwu / Etherlabs**.
