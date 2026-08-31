-- Standardize the historical quarterly DB1B market extract.
create or replace table stg_db1b_market as
select
    cast(Year as integer) as service_year,
    cast(Quarter as integer) as service_quarter,
    cast(OriginAirportID as integer) as origin_airport_id,
    cast(DestAirportID as integer) as destination_airport_id,
    upper(trim(Origin)) as origin_code,
    upper(trim(Dest)) as destination_code,
    cast(RPCarrier as varchar) as reporting_carrier,
    cast(TkCarrier as varchar) as ticketing_carrier,
    cast(OpCarrier as varchar) as operating_carrier,
    cast(MktFare as double) as market_fare_usd,
    cast(Passengers as double) as sampled_passengers,
    cast(MktMilesFlown as double) as market_miles,
    cast(MktCoupons as integer) as market_coupons,
    cast(BulkFare as integer) as bulk_fare_flag
from raw_db1b_market
where MktFare > 0
  and Passengers > 0
  and OriginCountry = 'US'
  and DestCountry = 'US'
  and Year between 2017 and 2025;
