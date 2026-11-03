# Setup Guide

## Local verification

Use Python 3.11 and PostgreSQL 16:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
psql -v ON_ERROR_STOP=1 -f database/schema.sql
psql -v ON_ERROR_STOP=1 -f database/sample-data.sql
```

Copy `.env.example` to an uncommitted `.env` and replace placeholders. `LEAKAGE_ENGINE_TOKEN` is optional only for local development; configure it for any reachable service.

```bash
.venv/bin/python -m revenue_leakage
```

Import the five JSON files in `n8n-workflows/`. They are inactive by default. Configure database, Stripe/product, Slack and service credentials through n8n's credential store or environment variables, then validate manually in the target n8n release before enabling schedules.

The SQL sample records and benchmark are synthetic. Do not mix them with production data.
