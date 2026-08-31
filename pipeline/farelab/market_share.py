"""Estimate the observational relationship between relative fare and market share."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


MODEL_VERSION = "market-share-fe-v1"


@dataclass(frozen=True)
class ShareModelCard:
    model_version: str
    built_at_utc: str
    model_type: str
    formula: str
    data_period: str
    excluded_years: list[int]
    observations: int
    entities: int
    market_periods: int
    r_squared_within: float
    fare_coefficient: float
    fare_std_error: float
    fare_p_value: float
    fare_confidence_low: float
    fare_confidence_high: float
    capacity_coefficient: float
    capacity_std_error: float
    interpretation: str
    limitation: str


SHARE_QUERY = """
with base as (
    select
        period_key,
        cast(substr(period_key, 1, 4) as integer) as service_year,
        cast(right(period_key, 1) as integer) as service_quarter,
        route_id,
        carrier_code,
        weighted_fare_usd,
        t100_passengers,
        available_seats,
        market_share,
        sampled_passengers
    from mart_route_carrier_quarter
    where data_status = 'accepted'
      and competitor_weighted_fare_usd between 50 and 2000
      and weighted_fare_usd between 50 and 2000
      and t100_passengers >= 100
      and available_seats >= 100
      and market_share > 0
),
support as (
    select
        route_id,
        carrier_code,
        count(*) filter (where service_year not in (2020, 2021)) as model_periods,
        count(distinct round(weighted_fare_usd, 0))
            filter (where service_year not in (2020, 2021)) as distinct_rounded_fares,
        (
            max(weighted_fare_usd) filter (where service_year not in (2020, 2021))
            - min(weighted_fare_usd) filter (where service_year not in (2020, 2021))
        ) / nullif(
            avg(weighted_fare_usd) filter (where service_year not in (2020, 2021)),
            0
        ) as relative_fare_range
    from base
    group by route_id, carrier_code
)
select base.*
from base
join support using (route_id, carrier_code)
where base.service_year not in (2020, 2021)
  and support.model_periods >= 12
  and support.distinct_rounded_fares >= 8
  and support.relative_fare_range >= 0.10
order by route_id, carrier_code, period_key
"""


def load_share_panel(database: Path) -> pd.DataFrame:
    with duckdb.connect(str(database), read_only=True) as connection:
        frame = connection.execute(SHARE_QUERY).fetch_df()
    if frame.empty:
        raise ValueError("No supported observations were found for market-share modeling")
    frame["entity_id"] = frame["route_id"] + ":" + frame["carrier_code"]
    frame["time_id"] = frame["service_year"] * 4 + frame["service_quarter"]
    frame["market_period_id"] = frame["route_id"] + ":" + frame["period_key"]
    frame["log_market_share"] = np.log(frame["market_share"])
    frame["log_fare"] = np.log(frame["weighted_fare_usd"])
    frame["log_seats"] = np.log(frame["available_seats"])
    return frame


def fit_share_model(panel: pd.DataFrame) -> object:
    indexed = panel.set_index(["entity_id", "time_id"])
    exogenous = indexed[["log_fare", "log_seats"]]
    route_period_effect = pd.DataFrame(
        {
            "route_period": pd.Categorical(indexed["market_period_id"]).codes,
        },
        index=indexed.index,
    )
    model = PanelOLS(
        indexed["log_market_share"],
        exogenous,
        entity_effects=True,
        other_effects=route_period_effect,
        drop_absorbed=True,
        check_rank=True,
    )
    return model.fit(cov_type="clustered", cluster_entity=True, debiased=True)


def build_card(panel: pd.DataFrame, result: object) -> ShareModelCard:
    confidence = result.conf_int().loc["log_fare"]
    return ShareModelCard(
        model_version=MODEL_VERSION,
        built_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        model_type="Entity and route-period fixed-effects log-share regression",
        formula=(
            "log(market_share) = beta_fare*log(fare) + beta_capacity*log(seats) "
            "+ route-carrier effects + route-period effects + error"
        ),
        data_period=f"{panel['period_key'].min()} to {panel['period_key'].max()}",
        excluded_years=[2020, 2021],
        observations=int(result.nobs),
        entities=int(panel["entity_id"].nunique()),
        market_periods=int(panel["market_period_id"].nunique()),
        r_squared_within=float(result.rsquared_within),
        fare_coefficient=float(result.params["log_fare"]),
        fare_std_error=float(result.std_errors["log_fare"]),
        fare_p_value=float(result.pvalues["log_fare"]),
        fare_confidence_low=float(confidence.iloc[0]),
        fare_confidence_high=float(confidence.iloc[1]),
        capacity_coefficient=float(result.params["log_seats"]),
        capacity_std_error=float(result.std_errors["log_seats"]),
        interpretation=(
            "The fare coefficient measures the within-market association between a carrier's "
            "fare and passenger share after controlling for its seats, persistent route-carrier "
            "differences, and shocks shared by all carriers in the same route-period."
        ),
        limitation=(
            "The estimate remains observational. Time-varying schedule quality, product changes, "
            "and fare-setting responses to private demand information can still confound it."
        ),
    )


def fit_and_export(database: Path, output: Path) -> ShareModelCard:
    panel = load_share_panel(database)
    result = fit_share_model(panel)
    card = build_card(panel, result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(card), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return card


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit FareLab's relative-fare market-share model")
    parser.add_argument("--database", type=Path, default=Path("data/processed/farelab_panel.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("models/market_share_fe_v1.json"))
    args = parser.parse_args()
    card = fit_and_export(args.database, args.output)
    print(json.dumps(asdict(card), indent=2))


if __name__ == "__main__":
    main()
