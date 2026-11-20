select billing_period, attribution_source, sum(allocated_cost) as total_cost from read_parquet('data/mart_allocation_audit.parquet') group by all
