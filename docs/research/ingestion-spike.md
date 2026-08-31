# Real-data ingestion spike

Run date: 2026-08-30

## Files verified

### DB1B Market 2024 Q4

- Official archive size: 109,087,449 bytes
- Uncompressed CSV size: 2,150,709,018 bytes
- Raw rows: 8,525,077
- Positive-fare domestic rows: 8,518,002
- Directional markets after basic staging: 68,089
- Reporting carriers after basic staging: 25
- Sampled passengers in the raw file: 15,922,048

The schema contains the stable airport identifiers and separate reporting, ticketing, and operating carrier fields required by the proposed design.

### T-100 Domestic Segment 2024

- Official form-generated archive size: 5,651,291 bytes
- Uncompressed selected-field CSV size: 48,521,670 bytes
- Scheduled passenger service rows, class F: 341,585
- Scheduled passenger volume: 856,457,490
- Scheduled available seats: 1,054,337,932

The downloader replays the official ASP.NET form with its required validation tokens and requests only the governed FareLab field contract.

## Join audit

The first row-level audit matched direct DB1B itinerary rows to T-100 route-quarter capacity on year, quarter, directional airport identifiers, and operating carrier.

- Eligible direct fare rows: 4,677,261
- Row join rate: 99.56%
- Passenger-weighted join rate: 99.78%

After the first-release aligned-carrier filter and aggregation to route-carrier-quarter grain, the executable mart build produced:

- Eligible fare groups: 10,148
- Joined mart rows: 8,118
- Fare-group join rate: 80.00%
- Passenger-weighted group join rate: 99.82%
- Directional airport routes represented: 5,410
- Carriers represented: 14

The lower group-level rate is concentrated in very thin fare groups. The passenger-weighted rate shows that nearly all in-scope volume joins. Both rates remain production quality metrics so thin-market exclusions are visible.

Carrier identity requires a stricter product decision. In the eligible direct-fare sample:

- Reporting, ticketing, and operating carrier all agree for 87.48% of sampled passengers.
- Ticketing and operating carrier agree for 88.33% of sampled passengers.

## V1 decision

The first production mart will use direct itineraries where reporting, ticketing, and operating carrier agree. This reduces coverage but avoids silently assigning an operating affiliate's T-100 capacity to a marketing carrier. The excluded codeshare share will be published as a coverage metric.

A later release may add a dated operating-to-marketing carrier bridge. It must be validated independently before those rows enter the recommendation queue.

## Conclusion

The data architecture is feasible. The direct route and operating-carrier join is technically strong for the tested period. Carrier ownership, not row-level joinability, is the material semantic risk and now has an explicit first-release control.
