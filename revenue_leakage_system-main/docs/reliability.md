# Reliability and Failure Modes

Revenue-control systems can create expensive false alarms or, worse, silently miss billing errors. Rules should therefore be deterministic, versioned, auditable and safe under repeated ingestion.

## 1. Stale contract or pricing data

A correct rule running against an old price table can produce false leakage findings.

**Controls:** effective dates, source freshness metadata, versioned pricing rules and visible stale-data warnings.

## 2. Usage-window mismatch

Usage may be calculated on a different billing window/timezone than invoicing.

**Control:** make the billing period explicit and test boundary cases.

## 3. Duplicate source events

Replayed Stripe/product events can inflate usage or create duplicate findings.

**Controls:** stable external IDs, idempotent ingestion and deduplicated findings.

## 4. Decimal/currency errors

Financial comparison should use exact decimal semantics rather than binary floating-point assumptions.

**Control:** database numeric/decimal types and explicit currency handling.

## 5. Contract precedence

A global price list may not override negotiated customer terms.

**Control:** define source-of-truth precedence: signed contract/amendment → customer-specific configuration → standard catalog, according to the target business.

## 6. Discount validity

Discounts need effective dates, eligibility state, limits and explicit stacking policy.

## 7. Feature-entitlement drift

Product access and billing plan may update at different times.

**Control:** define a tolerance/grace window where appropriate rather than immediately treating every temporary mismatch as leakage.

## 8. Finding duplication

The same unresolved issue should not create a new independent alert every scheduled run.

**Control:** deterministic finding keys, status lifecycle, first/last seen timestamps and alert deduplication.

## 9. Rule changes

Changing a detection rule can change historical findings.

**Control:** version rules and store the rule version with each detection.

## 10. False automatic correction

Detection and recovery/correction are different risk levels.

**Control:** high-impact financial corrections should require explicit policy/approval rather than automatically modifying contracts or charges from a detection alone.

## 11. Missing source data

Missing usage or contract information should not silently be interpreted as zero.

**Control:** distinguish missing/unknown from actual zero and route incomplete records for review.

## 12. Observability

Track:
- records ingested by source;
- source freshness;
- rules evaluated;
- findings by rule/severity;
- estimated value by rule/currency;
- duplicate-suppressed findings;
- unresolved finding age;
- rule errors;
- workflow failures;
- resolution/recovery outcomes when available.

## Test acceptance set

Automated fixtures should cover:
- correct standard pricing;
- customer-specific negotiated price;
- outdated price;
- correctly billed overage;
- missing overage;
- valid discount;
- expired discount;
- feature mismatch;
- grace-period behavior;
- duplicate events;
- duplicate findings;
- effective-date boundary;
- decimal precision;
- currency mismatch;
- missing usage/contract data;
- stale source data.

The core rules are tested outside n8n, with n8n responsible for orchestration, connectors and notifications. Live provider semantics, tenant authorization and production operations remain deployment-specific work.
