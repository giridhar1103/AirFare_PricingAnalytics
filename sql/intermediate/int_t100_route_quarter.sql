create or replace table int_t100_route_quarter as
select
    service_year,
    cast(ceil(service_month / 3.0) as integer) as service_quarter,
    origin_airport_id,
    destination_airport_id,
    origin_code,
    destination_code,
    airline_id,
    carrier_code,
    sum(passengers) as passengers,
    sum(available_seats) as available_seats,
    sum(departures_performed) as departures_performed,
    max(distance_miles) as distance_miles
from stg_t100_segment
group by all;
