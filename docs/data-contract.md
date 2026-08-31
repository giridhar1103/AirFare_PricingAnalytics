# Data contract

## Source systems

### DB1B historical fare model

Purpose: passenger-weighted fare, route, carrier, routing, and sampled passenger observations before July 2025.

Important contract:

- Quarterly collection
- 10% sample rate
- Collection ended in July 2025
- Fare is ticket value under BTS definitions
- Zero and frequent-flyer fares require filtering under the published methodology

### DB1C current monitoring product

Purpose: monthly monitoring after the collection transition.

Important contract:

- Monthly collection from July 2025
- 40% sample rate
- Separate model and quality history from DB1B
- No naive row union with DB1B

### T-100 domestic segment

Purpose: monthly passengers, available seats, departures, service class, and distance for nonstop domestic segments.

Important contract:

- Reported operating traffic and capacity
- Contains no carrier financial information
- Airport ID and airline ID are preferred for longitudinal keys
- Service class and scheduled passenger filters must be explicit

## Raw zone

Raw files are immutable and stored outside Git. Every ingestion run writes:

```text
source_name
source_url
source_period
downloaded_at_utc
sha256
byte_count
row_count
schema_fingerprint
```

## Canonical analytical mart

`mart_route_carrier_quarter`

| Field | Type | Definition |
| --- | --- | --- |
| `period_key` | string | Calendar quarter such as `2024Q1` |
| `route_id` | string | Stable normalized airport-market pair |
| `origin_airport_id` | integer | DOT airport identifier |
| `destination_airport_id` | integer | DOT airport identifier |
| `origin_code` | string | Display airport code at the data vintage |
| `destination_code` | string | Display airport code at the data vintage |
| `airline_id` | integer | DOT airline identifier |
| `carrier_code` | string | Display carrier code at the data vintage |
| `weighted_fare_usd` | number | Passenger-weighted market fare |
| `sampled_passengers` | number | DB1B sampled passengers used in fare calculation |
| `t100_passengers` | integer | T-100 transported passengers |
| `available_seats` | integer | T-100 available seats |
| `load_factor` | number | T-100 passengers divided by seats |
| `market_share` | number | Carrier passenger share in normalized route-period |
| `hhi` | number | Sum of squared market shares |
| `competitor_fare_index` | number | Carrier fare divided by competing-carrier weighted fare |
| `direct_share` | number | Share of sampled passengers on direct itineraries |
| `revenue_proxy_usd` | number | Weighted fare times T-100 passengers |
| `data_status` | string | `accepted`, `review`, or `quarantined` |

## Quality gates

- No duplicate route-carrier-period key
- Fare is finite and positive after published filters
- Passenger and seat counts are nonnegative
- Accepted load factor lies between 0 and 1
- Market shares sum to 1 within tolerance for each market-period
- HHI lies between reciprocal carrier count and 1 within tolerance
- Join coverage and unmatched keys are reported for every build
- Every exported artifact includes source vintage and build timestamp

## Environment separation

- `data/fixtures` contains deterministic developer fixtures only.
- `data/raw`, `data/interim`, and `data/processed` are ignored by Git except for instructions.
- Production export fails if an artifact has `data_mode=development_fixture`.
- The web interface shows a visible development-data banner when a fixture is loaded.
