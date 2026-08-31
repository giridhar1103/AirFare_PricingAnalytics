-- V1 pricing scope uses direct domestic itineraries where the reporting,
-- ticketing, and operating carrier agree. This yields an auditable join to
-- T-100 capacity without assigning regional capacity to a marketing carrier.
create or replace table int_db1b_direct_route_fares as
select
    service_year,
    service_quarter,
    origin_airport_id,
    destination_airport_id,
    origin_code,
    destination_code,
    ticketing_carrier as carrier_code,
    sum(market_fare_usd * sampled_passengers) / sum(sampled_passengers) as weighted_fare_usd,
    sum(sampled_passengers) as sampled_passengers,
    min(market_fare_usd) as observed_fare_min,
    max(market_fare_usd) as observed_fare_max,
    count(*) as sampled_itinerary_rows
from stg_db1b_market
where market_coupons = 1
  and bulk_fare_flag = 0
  and market_fare_usd between 50 and 2000
  and reporting_carrier = ticketing_carrier
  and ticketing_carrier = operating_carrier
group by all;
