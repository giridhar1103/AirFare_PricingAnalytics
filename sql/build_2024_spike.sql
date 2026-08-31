create or replace view raw_db1b_market as
select *
from read_csv_auto(
    'data/raw/Origin_and_Destination_Survey_DB1BMarket_2024_4.csv',
    header = true,
    sample_size = 100000,
    null_padding = true
);

create or replace view raw_t100_domestic_segment as
select *
from read_csv_auto(
    'data/raw/T_T100D_SEGMENT_US_CARRIER_ONLY.csv',
    header = true
);

.read sql/staging/stg_db1b_market.sql
.read sql/staging/stg_t100_segment.sql
.read sql/intermediate/int_db1b_direct_route_fares.sql
.read sql/intermediate/int_t100_route_quarter.sql
.read sql/marts/mart_route_carrier_quarter.sql
.read sql/tests/audit_db1b_t100_join.sql
