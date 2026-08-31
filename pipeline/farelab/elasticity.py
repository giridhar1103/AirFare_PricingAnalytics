"""Fit FareLab's interpretable observational price-sensitivity benchmark."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


MODEL_VERSION = "elasticity-fe-v1"


@dataclass(frozen=True)
class CoefficientResult:
    name: str
    estimate: float
    std_error: float
    p_value: float
    confidence_low: float
    confidence_high: float


@dataclass(frozen=True)
class ModelCard:
    model_version: str
    built_at_utc: str
    model_type: str
    formula: str
    data_period: str
    excluded_years: list[int]
    observations: int
    entities: int
    periods: int
    r_squared_within: float
    covariance: str
    coefficients: list[CoefficientResult]
    filters: dict[str, object]
    interpretation: str
    limitation: str


PANEL_QUERY = """
with base as (
    select
        period_key,
        cast(substr(period_key, 1, 4) as integer) as service_year,
        cast(right(period_key, 1) as integer) as service_quarter,
        route_id,
        carrier_code,
        origin_code,
        destination_code,
        distance_miles,
        weighted_fare_usd,
        competitor_weighted_fare_usd,
        t100_passengers,
        available_seats,
        load_factor,
        market_share,
        hhi,
        sampled_passengers
    from mart_route_carrier_quarter
    where data_status = 'accepted'
      and weighted_fare_usd between 50 and 2000
      and competitor_weighted_fare_usd between 50 and 2000
      and t100_passengers >= 100
      and available_seats >= 100
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


def load_panel(database: Path) -> pd.DataFrame:
    with duckdb.connect(str(database), read_only=True) as connection:
        frame = connection.execute(PANEL_QUERY).fetch_df()
    if frame.empty:
        raise ValueError("No supported observations were found for elasticity modeling")
    frame["entity_id"] = frame["route_id"] + ":" + frame["carrier_code"]
    frame["time_id"] = frame["service_year"] * 4 + frame["service_quarter"]
    frame["log_passengers"] = np.log(frame["t100_passengers"])
    frame["log_fare"] = np.log(frame["weighted_fare_usd"])
    frame["log_seats"] = np.log(frame["available_seats"])
    frame["log_competitor_fare"] = np.log(frame["competitor_weighted_fare_usd"])
    return frame


def fit_fixed_effects(panel: pd.DataFrame) -> tuple[PanelOLS, object]:
    indexed = panel.set_index(["entity_id", "time_id"])
    model = PanelOLS.from_formula(
        "log_passengers ~ 1 + log_fare + log_seats + log_competitor_fare "
        "+ EntityEffects + TimeEffects",
        data=indexed,
        drop_absorbed=True,
        check_rank=True,
    )
    result = model.fit(cov_type="clustered", cluster_entity=True, debiased=True)
    return model, result


def _coefficient(result: object, name: str) -> CoefficientResult:
    confidence = result.conf_int().loc[name]
    return CoefficientResult(
        name=name,
        estimate=float(result.params[name]),
        std_error=float(result.std_errors[name]),
        p_value=float(result.pvalues[name]),
        confidence_low=float(confidence.iloc[0]),
        confidence_high=float(confidence.iloc[1]),
    )


def build_model_card(panel: pd.DataFrame, result: object) -> ModelCard:
    first_period = str(panel["period_key"].min())
    last_period = str(panel["period_key"].max())
    coefficients = [
        _coefficient(result, name)
        for name in ("log_fare", "log_seats", "log_competitor_fare")
    ]
    return ModelCard(
        model_version=MODEL_VERSION,
        built_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        model_type="Two-way fixed-effects log-log panel regression",
        formula=(
            "log(passengers) = beta_price*log(fare) + beta_capacity*log(seats) "
            "+ beta_competitor*log(competitor_fare) + entity effects + period effects + error"
        ),
        data_period=f"{first_period} to {last_period}",
        excluded_years=[2020, 2021],
        observations=int(result.nobs),
        entities=int(panel["entity_id"].nunique()),
        periods=int(panel["time_id"].nunique()),
        r_squared_within=float(result.rsquared_within),
        covariance="Entity-clustered standard errors with finite-sample debiasing",
        coefficients=coefficients,
        filters={
            "minimum_model_periods": 12,
            "minimum_distinct_rounded_fares": 8,
            "minimum_relative_fare_range": 0.10,
            "minimum_passengers": 100,
            "minimum_seats": 100,
            "fare_range_usd": [50, 2000],
            "requires_competitor_fare": True,
            "accepted_quality_rows_only": True,
        },
        interpretation=(
            "The fare coefficient is an observational own-price elasticity conditional on the "
            "included controls and fixed effects."
        ),
        limitation=(
            "Airlines set fares using demand information not observed in public DOT data. "
            "Fixed effects reduce confounding but do not establish a causal price effect."
        ),
    )


def fit_and_export(database: Path, output: Path) -> ModelCard:
    panel = load_panel(database)
    _, result = fit_fixed_effects(panel)
    card = build_model_card(panel, result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(asdict(card), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return card


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit FareLab's fixed-effects elasticity benchmark")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/processed/farelab_panel.duckdb"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/elasticity_fe_v1.json"),
    )
    args = parser.parse_args()
    card = fit_and_export(args.database, args.output)
    print(json.dumps(asdict(card), indent=2))


if __name__ == "__main__":
    main()
