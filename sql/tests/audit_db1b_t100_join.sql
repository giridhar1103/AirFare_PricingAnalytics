with joined as (
    select
        fare.sampled_passengers,
        traffic.passengers
    from int_db1b_direct_route_fares fare
    left join int_t100_route_quarter traffic
      on fare.service_year = traffic.service_year
     and fare.service_quarter = traffic.service_quarter
     and fare.origin_airport_id = traffic.origin_airport_id
     and fare.destination_airport_id = traffic.destination_airport_id
     and fare.carrier_code = traffic.carrier_code
)
select
    count(*) as fare_groups,
    count(passengers) / count(*)::double as row_join_rate,
    sum(case when passengers is not null then sampled_passengers else 0 end)
        / sum(sampled_passengers) as passenger_weighted_join_rate
from joined;
