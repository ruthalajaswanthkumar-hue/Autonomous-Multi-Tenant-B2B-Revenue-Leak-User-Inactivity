begin;

do $$
begin
  if (select count(*) from customers) <> 3 then
    raise exception 'synthetic customer fixtures were not loaded';
  end if;
  if (select count(*) from actual_charges) <> 3 then
    raise exception 'synthetic charge fixtures were not loaded';
  end if;
end $$;

select persist_leakage_evaluation($json$
{
  "rule_id":"outdated_pricing",
  "customer_id":"11111111-1111-1111-1111-111111111111",
  "outcome":"finding",
  "expected_value":"149.00",
  "actual_value":"99.00",
  "difference":"50.00",
  "impact_estimate":"50.00",
  "currency":"USD",
  "severity":"low",
  "evidence":{"term_id":"catalog-pro-2025"},
  "rule_version":"pricing.v1",
  "finding_key":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
$json$::jsonb);

select persist_leakage_evaluation($json$
{
  "rule_id":"outdated_pricing",
  "customer_id":"11111111-1111-1111-1111-111111111111",
  "outcome":"finding",
  "expected_value":"149.00",
  "actual_value":"99.00",
  "difference":"50.00",
  "impact_estimate":"50.00",
  "currency":"USD",
  "severity":"low",
  "evidence":{"term_id":"catalog-pro-2025"},
  "rule_version":"pricing.v1",
  "finding_key":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
$json$::jsonb);

do $$
begin
  if (select count(*) from leakage_detections) <> 1 then
    raise exception 'finding persistence is not idempotent';
  end if;
end $$;

rollback;
