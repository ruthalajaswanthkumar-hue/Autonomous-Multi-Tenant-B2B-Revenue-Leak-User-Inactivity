create extension if not exists pgcrypto;

create table if not exists customers (
  id uuid primary key default gen_random_uuid(),
  stripe_customer_id text unique not null,
  email text,
  name text not null,
  current_plan text not null,
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  enabled_features jsonb not null default '[]'::jsonb,
  plan_effective_date date,
  source_updated_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pricing_rules (
  id uuid primary key default gen_random_uuid(),
  rule_external_id text unique not null,
  rule_version text not null,
  plan_name text not null,
  current_base_price numeric(18,6) not null check (current_base_price >= 0),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  included_usage jsonb not null default '{}'::jsonb,
  overage_rates jsonb not null default '{}'::jsonb,
  features jsonb not null default '[]'::jsonb,
  effective_date date not null,
  end_date date,
  source_updated_at timestamptz not null,
  created_at timestamptz not null default now(),
  check (end_date is null or end_date >= effective_date),
  unique (plan_name, currency, effective_date, rule_version)
);

create table if not exists contract_pricing (
  id uuid primary key default gen_random_uuid(),
  contract_external_id text unique not null,
  customer_id uuid not null references customers(id) on delete cascade,
  plan_name text not null,
  base_price numeric(18,6) not null check (base_price >= 0),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  included_usage jsonb not null default '{}'::jsonb,
  overage_rates jsonb not null default '{}'::jsonb,
  discount_percent numeric(7,4) not null default 0 check (discount_percent between 0 and 100),
  discount_reason text,
  discount_end_date date,
  entitled_features jsonb not null default '[]'::jsonb,
  effective_date date not null,
  end_date date,
  rule_version text not null,
  source_updated_at timestamptz not null,
  created_at timestamptz not null default now(),
  check (end_date is null or end_date >= effective_date)
);

create table if not exists actual_charges (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete cascade,
  stripe_invoice_id text unique not null,
  billing_period_start date not null,
  billing_period_end date not null,
  base_charge numeric(18,6) not null check (base_charge >= 0),
  overage_charges numeric(18,6) not null default 0 check (overage_charges >= 0),
  discounts numeric(18,6) not null default 0 check (discounts >= 0),
  total_charged numeric(18,6) not null check (total_charged >= 0),
  currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
  source_updated_at timestamptz not null,
  created_at timestamptz not null default now(),
  check (billing_period_end >= billing_period_start)
);

create table if not exists product_usage (
  id uuid primary key default gen_random_uuid(),
  external_event_id text unique not null,
  customer_id uuid not null references customers(id) on delete cascade,
  usage_period_start date not null,
  usage_period_end date not null,
  usage_data jsonb not null,
  source_updated_at timestamptz not null,
  created_at timestamptz not null default now(),
  check (usage_period_end >= usage_period_start)
);

create table if not exists leakage_detections (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete cascade,
  rule_id text not null,
  rule_version text not null,
  finding_key char(64) not null check (finding_key ~ '^[0-9a-f]{64}$'),
  outcome text not null check (outcome in ('finding', 'clear', 'blocked', 'grace')),
  expected_value numeric(18,6),
  actual_value numeric(18,6),
  difference numeric(18,6),
  impact_estimate numeric(18,6),
  currency char(3),
  severity text not null check (severity in ('none', 'low', 'medium', 'high')),
  evidence jsonb not null,
  status text not null default 'new' check (status in ('new', 'investigating', 'resolved', 'false_positive')),
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  check ((status in ('resolved', 'false_positive')) = (resolved_at is not null))
);

create unique index if not exists uq_active_finding_key
  on leakage_detections (finding_key)
  where status in ('new', 'investigating');
create index if not exists idx_detections_customer on leakage_detections (customer_id, created_at desc);
create index if not exists idx_charges_customer_period on actual_charges (customer_id, billing_period_end desc);
create index if not exists idx_usage_customer_period on product_usage (customer_id, usage_period_end desc);
create index if not exists idx_contract_customer_effective on contract_pricing (customer_id, effective_date desc);

create or replace function persist_leakage_evaluation(payload jsonb)
returns uuid
language plpgsql
as $$
declare
  detection_id uuid;
begin
  if payload->>'outcome' <> 'finding' then
    return null;
  end if;

  insert into leakage_detections (
    customer_id, rule_id, rule_version, finding_key, outcome,
    expected_value, actual_value, difference, impact_estimate,
    currency, severity, evidence
  ) values (
    (payload->>'customer_id')::uuid,
    payload->>'rule_id',
    payload->>'rule_version',
    payload->>'finding_key',
    payload->>'outcome',
    nullif(payload->>'expected_value', '')::numeric,
    nullif(payload->>'actual_value', '')::numeric,
    nullif(payload->>'difference', '')::numeric,
    nullif(payload->>'impact_estimate', '')::numeric,
    nullif(payload->>'currency', ''),
    payload->>'severity',
    payload->'evidence'
  )
  on conflict (finding_key) where status in ('new', 'investigating')
  do update set
    last_seen_at = now(),
    expected_value = excluded.expected_value,
    actual_value = excluded.actual_value,
    difference = excluded.difference,
    impact_estimate = excluded.impact_estimate,
    severity = excluded.severity,
    evidence = excluded.evidence
  returning id into detection_id;

  return detection_id;
end
$$;
