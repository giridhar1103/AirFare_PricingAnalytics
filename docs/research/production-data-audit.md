# Production data audit

## Build scope

| Source | Files | Staged rows | Coverage | Compressed bytes |
| --- | ---: | ---: | --- | ---: |
| DB1B Market | 34 | 220,847,178 | 2017 Q1 through 2025 Q2 | 3,000,826,879 |
| T-100 Domestic Segment U.S. Carriers | 9 | 2,662,620 | 2017 through 2025 | 46,149,364 |
| Total | 43 | 223,509,798 |  | 3,046,976,243 |

Every loaded source has a URL, period, archive name, SHA-256 checksum, byte count, row count, and UTC load timestamp in `warehouse_source_manifest`.

The public repository includes `data/manifests/warehouse_build.json`, which summarizes all 43 manifest rows. Its ordered manifest digest is `6de908da013955f4a764da16e05c9106fff298eb8b1a4bcb0d2b880ab4448728`.

## Mart result

| Measure | Result |
| --- | ---: |
| Route-carrier-quarter rows | 238,526 |
| Directional routes | 8,639 |
| Carriers | 21 |
| Accepted rows | 238,522 |
| Review rows | 4 |
| Duplicate canonical keys | 0 |

The four review rows have a calculated load factor slightly above 1. They remain visible to data-quality reporting and are excluded from model training and public route selection.

## Join coverage

DB1B and T-100 are joined on year, quarter, directional DOT airport identifiers, and aligned carrier code. Passenger-weighted direct-fare join coverage is used as the principal audit because unmatched thin groups have little commercial volume.

| Measure across 34 quarters | Result |
| --- | ---: |
| Minimum passenger-weighted join rate | 99.06% |
| Average passenger-weighted join rate | 99.57% |
| Minimum unweighted group join rate | 65.48% |
| Average unweighted group join rate | 74.42% |

The unweighted result is lower because small fare groups often do not have aligned nonstop T-100 service under the release-1 carrier rule. FareLab publishes both views and does not describe group-level coverage as 99%.

## Public product scope

The browser artifact includes 60 route-carrier examples selected from 2025 Q2 candidates with at least 10,000 passengers, at least 3% carrier share, a competing-fare comparison, and complete forecast inputs. It retains 12 supported examples for each action so the product demonstrates the full review workflow, including hold controls.

This public set is a decision-workflow sample, not a statistically representative airline network portfolio.
