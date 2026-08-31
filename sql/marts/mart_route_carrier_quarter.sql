create or replace table mart_route_carrier_quarter as
with traffic_shares as (
    select
        *,
        sum(passengers) over market_window as market_passengers,
        passengers / nullif(sum(passengers) over market_window, 0) as market_share
    from int_t100_route_quarter
    window market_window as (
        partition by
            service_year,
            service_quarter,
            origin_airport_id,
            destination_airport_id
    )
),
traffic_concentration as (
    select
        *,
        sum(market_share * market_share) over market_window as hhi
    from traffic_shares
    window market_window as (
        partition by
            service_year,
            service_quarter,
            origin_airport_id,
            destination_airport_id
    )
),
joined as (
    select
        fare.service_year,
        fare.service_quarter,
        fare.origin_airport_id,
        fare.destination_airport_id,
        fare.origin_code,
        fare.destination_code,
        fare.carrier_code,
        traffic.airline_id,
        traffic.distance_miles,
        fare.weighted_fare_usd,
        fare.sampled_passengers,
        fare.observed_fare_min,
        fare.observed_fare_max,
        traffic.passengers,
        traffic.available_seats,
        traffic.departures_performed,
        traffic.market_passengers,
        traffic.market_share,
        traffic.hhi,
        sum(fare.weighted_fare_usd * fare.sampled_passengers) over market_window
            as market_sample_fare_dollars,
        sum(fare.sampled_passengers) over market_window as market_sampled_passengers
    from int_db1b_direct_route_fares fare
    join traffic_concentration traffic
      on fare.service_year = traffic.service_year
     and fare.service_quarter = traffic.service_quarter
     and fare.origin_airport_id = traffic.origin_airport_id
     and fare.destination_airport_id = traffic.destination_airport_id
     and fare.carrier_code = traffic.carrier_code
    window market_window as (
        partition by
            fare.service_year,
            fare.service_quarter,
            fare.origin_airport_id,
            fare.destination_airport_id
    )
),
shares as (
    select
        *,
        (
            market_sample_fare_dollars - weighted_fare_usd * sampled_passengers
        ) / nullif(market_sampled_passengers - sampled_passengers, 0)
            as competitor_weighted_fare_usd
    from joined
)
select
    concat(service_year, 'Q', service_quarter) as period_key,
    concat(origin_airport_id, ':', destination_airport_id) as route_id,
    origin_airport_id,
    destination_airport_id,
    origin_code,
    destination_code,
    airline_id,
    carrier_code,
    distance_miles,
    weighted_fare_usd,
    sampled_passengers,
    passengers as t100_passengers,
    available_seats,
    passengers / nullif(available_seats, 0) as load_factor,
    market_share,
    hhi,
    competitor_weighted_fare_usd,
    weighted_fare_usd / nullif(competitor_weighted_fare_usd, 0) as competitor_fare_index,
    observed_fare_min,
    observed_fare_max,
    weighted_fare_usd * passengers as revenue_proxy_usd,
    case
        when available_seats <= 0 or passengers < 0 then 'quarantined'
        when passengers / available_seats > 1 then 'review'
        else 'accepted'
    end as data_status
from shares;
