-- Standardize scheduled domestic passenger segments from T-100.
create or replace table stg_t100_segment as
select
    cast(year as integer) as service_year,
    cast(month as integer) as service_month,
    cast(origin_airport_id as integer) as origin_airport_id,
    cast(dest_airport_id as integer) as destination_airport_id,
    upper(trim(origin)) as origin_code,
    upper(trim(dest)) as destination_code,
    cast(airline_id as integer) as airline_id,
    cast(unique_carrier as varchar) as carrier_code,
    cast(passengers as bigint) as passengers,
    cast(seats as bigint) as available_seats,
    cast(departures_performed as integer) as departures_performed,
    cast(distance as double) as distance_miles
from raw_t100_domestic_segment
where class = 'F'
  and passengers >= 0
  and seats > 0;
