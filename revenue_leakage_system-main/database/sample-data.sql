-- Synthetic demonstration records with frozen dates. These are not client data.

insert into customers (
  id, stripe_customer_id, email, name, current_plan, currency,
  enabled_features, plan_effective_date, source_updated_at
) values
  ('11111111-1111-1111-1111-111111111111', 'cus_synth_outdated', 'outdated@example.test', 'Synthetic Outdated Price', 'pro', 'USD', '["api"]', '2025-01-01', '2025-02-10T11:00:00Z'),
  ('22222222-2222-2222-2222-222222222222', 'cus_synth_overage', 'overage@example.test', 'Synthetic Missing Overage', 'basic', 'USD', '["api"]', '2025-01-01', '2025-02-10T11:00:00Z'),
  ('33333333-3333-3333-3333-333333333333', 'cus_synth_discount', 'discount@example.test', 'Synthetic Valid Discount', 'pro', 'USD', '["api", "analytics"]', '2025-01-01', '2025-02-10T11:00:00Z');

insert into pricing_rules (
  rule_external_id, rule_version, plan_name, current_base_price, currency,
  included_usage, overage_rates, features, effective_date, source_updated_at
) values
  ('catalog-pro-2025', 'pricing.v1', 'pro', 149.00, 'USD', '{"api_calls":10000}', '{"api_calls_per_1000":5}', '["api","analytics"]', '2025-01-01', '2025-02-10T11:00:00Z'),
  ('catalog-basic-2025', 'pricing.v1', 'basic', 49.00, 'USD', '{"api_calls":10000}', '{"api_calls_per_1000":5}', '["api"]', '2025-01-01', '2025-02-10T11:00:00Z');

insert into contract_pricing (
  contract_external_id, customer_id, plan_name, base_price, currency,
  discount_percent, discount_reason, discount_end_date, entitled_features,
  effective_date, rule_version, source_updated_at
) values (
  'contract-synth-discount',
  '33333333-3333-3333-3333-333333333333',
  'pro', 149.00, 'USD', 15.00, 'synthetic annual commitment', '2025-12-31',
  '["api","analytics"]', '2025-01-01', 'discount.v1', '2025-02-10T11:00:00Z'
);

insert into product_usage (
  external_event_id, customer_id, usage_period_start, usage_period_end,
  usage_data, source_updated_at
) values (
  'usage-synth-jan', '22222222-2222-2222-2222-222222222222',
  '2025-01-01', '2025-01-31', '{"api_calls":25000}', '2025-02-10T11:00:00Z'
);

insert into actual_charges (
  customer_id, stripe_invoice_id, billing_period_start, billing_period_end,
  base_charge, overage_charges, discounts, total_charged, currency, source_updated_at
) values
  ('11111111-1111-1111-1111-111111111111', 'in_synth_outdated', '2025-01-01', '2025-01-31', 99.00, 0, 0, 99.00, 'USD', '2025-02-10T11:00:00Z'),
  ('22222222-2222-2222-2222-222222222222', 'in_synth_overage', '2025-01-01', '2025-01-31', 49.00, 0, 0, 49.00, 'USD', '2025-02-10T11:00:00Z'),
  ('33333333-3333-3333-3333-333333333333', 'in_synth_discount', '2025-01-01', '2025-01-31', 126.65, 0, 22.35, 126.65, 'USD', '2025-02-10T11:00:00Z');
