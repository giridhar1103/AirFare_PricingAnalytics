"""Export governed, browser-sized FareLab artifacts from the production warehouse."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import pandas as pd

from .forecast import _boosting_matrix, _to_passengers, load_history


def _future_frame(history: pd.DataFrame, bundle: dict[str, Any]) -> pd.DataFrame:
    latest = history.loc[history["period_key"] == "2025Q2"].copy()
    lag4 = history.loc[history["period_key"] == "2024Q3", ["entity_id", "t100_passengers"]].copy()
    lag4 = lag4.rename(columns={"t100_passengers": "lag4_passengers"})
    future = latest.merge(lag4, on="entity_id", how="inner")
    future["lag1_passengers"] = future["t100_passengers"]
    future["lag1_load_factor"] = future["load_factor"]
    future["lag1_market_share"] = future["market_share"]
    future["competitor_fare_missing"] = future["competitor_weighted_fare_usd"].isna().astype(float)
    future["competitor_fare_filled"] = future["competitor_weighted_fare_usd"].fillna(
        future["weighted_fare_usd"]
    )
    future["log_lag1_passengers"] = np.log1p(future["lag1_passengers"])
    future["log_lag4_passengers"] = np.log1p(future["lag4_passengers"])
    future["log_fare"] = np.log(future["weighted_fare_usd"])
    future["log_seats"] = np.log(future["available_seats"])
    future["log_competitor_fare"] = np.log(future["competitor_fare_filled"])
    future["log_distance"] = np.log1p(future["distance_miles"])
    future["quarter_sin"] = np.sin(2 * np.pi * 3 / 4)
    future["quarter_cos"] = np.cos(2 * np.pi * 3 / 4)
    future_period_index = 2025 * 4 + 3
    future["trend"] = future_period_index - int(bundle["trend_origin"])

    prediction = _to_passengers(
        bundle["model"].predict(_boosting_matrix(future, bundle["carrier_map"]))
    )
    calibration = bundle["interval_calibration"]
    quantile = float(calibration["log_absolute_error_quantile"])
    predicted_log = np.log1p(prediction)
    future["forecast_passengers"] = prediction
    future["forecast_low"] = np.maximum(np.expm1(predicted_log - quantile), 0)
    future["forecast_high"] = np.maximum(np.expm1(predicted_log + quantile), 0)
    future["forecast_yoy_change"] = prediction / future["lag4_passengers"] - 1
    return future


def _action(row: pd.Series) -> tuple[str, str]:
    load_factor = float(row["load_factor"])
    forecast_growth = float(row["forecast_yoy_change"])
    share_change = float(row["share_change_pp"])
    fare_index = float(row["fare_index"])
    if load_factor >= 0.90 and forecast_growth >= 0.02:
        return (
            "Review capacity",
            "High current utilization and a positive conditional demand forecast warrant a capacity review.",
        )
    if share_change <= -0.03 and fare_index >= 1.03:
        return (
            "Protect share",
            "Passenger share declined while the carrier fare remained above the competing-fare benchmark.",
        )
    if fare_index >= 1.15 and share_change < 0:
        return (
            "Review fare position",
            "The carrier fare is materially above the competing-fare benchmark while share is softening.",
        )
    if fare_index <= 0.90 and load_factor >= 0.85:
        return (
            "Evaluate yield",
            "The carrier has a relative fare discount and strong utilization, supporting a yield review.",
        )
    return (
        "Hold and monitor",
        "Current fare position, utilization, and share movement do not pass a stronger review rule.",
    )


def _priority_score(row: pd.Series, action: str) -> int:
    load_factor = float(row["load_factor"])
    share_change = float(row["share_change_pp"])
    fare_index = float(row["fare_index"])
    forecast_growth = float(row["forecast_yoy_change"])
    volume_support = float(np.clip(float(row["t100_passengers"]) / 100_000, 0, 1))

    if action == "Review capacity":
        score = (
            58
            + 15 * np.clip((load_factor - 0.90) / 0.06, 0, 1)
            + 15 * np.clip((forecast_growth - 0.02) / 0.18, 0, 1)
            + 7 * volume_support
        )
    elif action == "Protect share":
        score = (
            58
            + 18 * np.clip((-share_change - 0.03) / 0.10, 0, 1)
            + 12 * np.clip((fare_index - 1.03) / 0.50, 0, 1)
            + 5 * np.clip(-forecast_growth / 0.20, 0, 1)
            + 2 * volume_support
        )
    elif action == "Review fare position":
        score = (
            55
            + 18 * np.clip((fare_index - 1.15) / 0.75, 0, 1)
            + 15 * np.clip(-share_change / 0.08, 0, 1)
            + 5 * volume_support
        )
    elif action == "Evaluate yield":
        score = (
            58
            + 17 * np.clip((0.90 - fare_index) / 0.35, 0, 1)
            + 15 * np.clip((load_factor - 0.85) / 0.10, 0, 1)
            + 5 * np.clip(forecast_growth / 0.15, 0, 1)
        )
    else:
        score = 20 + 10 * np.clip((load_factor - 0.75) / 0.20, 0, 1) + 8 * volume_support
    return int(np.clip(round(score), 0, 95))


def _balanced_route_sample(frame: pd.DataFrame, maximum_routes: int) -> pd.DataFrame:
    """Retain strong examples for every review action plus lower-priority controls."""
    action_order = [
        "Review capacity",
        "Protect share",
        "Review fare position",
        "Evaluate yield",
        "Hold and monitor",
    ]
    ranked = frame.sort_values(["score", "t100_passengers"], ascending=[False, False])
    quota = max(maximum_routes // len(action_order), 1)
    selected_parts = [ranked.loc[ranked["action"] == action].head(quota) for action in action_order]
    selected = pd.concat(selected_parts, ignore_index=False).drop_duplicates("entity_id")
    if len(selected) < maximum_routes:
        remaining = ranked.loc[~ranked["entity_id"].isin(selected["entity_id"])]
        selected = pd.concat(
            [selected, remaining.head(maximum_routes - len(selected))], ignore_index=False
        )
    return selected.sort_values(["score", "t100_passengers"], ascending=[False, False]).head(
        maximum_routes
    )


def _history_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in frame.sort_values("period_index").itertuples():
        records.append(
            {
                "period": row.period_key,
                "fare": round(float(row.weighted_fare_usd), 2),
                "passengers": int(row.t100_passengers),
                "seats": int(row.available_seats),
                "loadFactor": round(float(row.load_factor), 6),
                "competitorFare": (
                    round(float(row.competitor_weighted_fare_usd), 2)
                    if pd.notna(row.competitor_weighted_fare_usd)
                    else None
                ),
                "marketShare": round(float(row.market_share), 6),
                "hhi": round(float(row.hhi), 6),
                "revenueProxy": round(float(row.weighted_fare_usd * row.t100_passengers), 2),
            }
        )
    return records


def _carrier_names(database: Path) -> dict[str, str]:
    query = """
    select carrier_code, max(carrier_name) as carrier_name
    from stg_t100_segment
    where carrier_name is not null
    group by carrier_code
    """
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(query).fetchall()
    return {str(code): str(name) for code, name in rows}


def _quality_summary(database: Path) -> dict[str, Any]:
    query = """
    select
        count(*) as mart_rows,
        count(distinct route_id) as directional_routes,
        count(distinct carrier_code) as carriers,
        min(period_key) as first_period,
        max(period_key) as last_period,
        sum(case when data_status = 'accepted' then 1 else 0 end) as accepted_rows,
        sum(case when data_status = 'review' then 1 else 0 end) as review_rows
    from mart_route_carrier_quarter
    """
    join_query = """
    with joined as (
        select
            fare.service_year,
            fare.service_quarter,
            fare.sampled_passengers,
            traffic.passengers
        from int_db1b_direct_route_fares fare
        left join int_t100_route_quarter traffic
          on fare.service_year = traffic.service_year
         and fare.service_quarter = traffic.service_quarter
         and fare.origin_airport_id = traffic.origin_airport_id
         and fare.destination_airport_id = traffic.destination_airport_id
         and fare.carrier_code = traffic.carrier_code
    ), quarterly as (
        select
            sum(case when passengers is not null then sampled_passengers else 0 end)
                / sum(sampled_passengers) as passenger_weighted_join_rate
        from joined
        group by service_year, service_quarter
    )
    select min(passenger_weighted_join_rate) from quarterly
    """
    with duckdb.connect(str(database), read_only=True) as connection:
        row = connection.execute(query).fetchone()
        source_files = connection.execute(
            "select count(*) from warehouse_source_manifest"
        ).fetchone()[0]
        join_rate = connection.execute(join_query).fetchone()[0]
    return {
        "martRows": int(row[0]),
        "directionalRoutes": int(row[1]),
        "carriers": int(row[2]),
        "firstPeriod": str(row[3]),
        "lastPeriod": str(row[4]),
        "acceptedRows": int(row[5]),
        "reviewRows": int(row[6]),
        "sourceFiles": int(source_files),
        "minimumPassengerWeightedJoinRate": float(join_rate),
    }


def build_artifact(
    database: Path,
    model_bundle_path: Path,
    forecast_card_path: Path,
    elasticity_card_path: Path,
    share_card_path: Path,
    iv_card_path: Path,
    maximum_routes: int = 60,
) -> dict[str, Any]:
    history = load_history(database)
    bundle = joblib.load(model_bundle_path)
    future = _future_frame(history, bundle)
    year_ago = history.loc[
        history["period_key"] == "2024Q2",
        [
            "entity_id",
            "weighted_fare_usd",
            "t100_passengers",
            "available_seats",
            "market_share",
            "load_factor",
        ],
    ].copy()
    year_ago = year_ago.rename(
        columns={
            "weighted_fare_usd": "year_ago_fare",
            "t100_passengers": "year_ago_passengers",
            "available_seats": "year_ago_seats",
            "market_share": "year_ago_share",
            "load_factor": "year_ago_load_factor",
        }
    )
    future = future.merge(year_ago, on="entity_id", how="inner")
    future = future.loc[
        future["competitor_weighted_fare_usd"].notna()
        & (future["t100_passengers"] >= 10_000)
        & (future["market_share"] >= 0.03)
    ].copy()
    future["fare_index"] = future["weighted_fare_usd"] / future["competitor_weighted_fare_usd"]
    future["fare_change_yoy"] = future["weighted_fare_usd"] / future["year_ago_fare"] - 1
    future["passenger_change_yoy"] = future["t100_passengers"] / future["year_ago_passengers"] - 1
    future["seat_change_yoy"] = future["available_seats"] / future["year_ago_seats"] - 1
    future["share_change_pp"] = future["market_share"] - future["year_ago_share"]

    actions = future.apply(lambda row: _action(row), axis=1)
    future["action"] = [value[0] for value in actions]
    future["rationale"] = [value[1] for value in actions]
    future["score"] = future.apply(lambda row: _priority_score(row, row["action"]), axis=1)
    future = _balanced_route_sample(future, maximum_routes)

    names = _carrier_names(database)
    route_records: list[dict[str, Any]] = []
    for row in future.itertuples():
        entity_history = history.loc[history["entity_id"] == row.entity_id].copy()
        observed_fare_min = float(entity_history["weighted_fare_usd"].min())
        observed_fare_max = float(entity_history["weighted_fare_usd"].max())
        interval_width = (float(row.forecast_high) - float(row.forecast_low)) / float(
            row.forecast_passengers
        )
        confidence = "High" if len(entity_history) >= 24 and interval_width <= 0.25 else "Medium"
        evidence = [
            f"{len(entity_history)} observed route-carrier quarters",
            f"Fare index {float(row.fare_index):.2f}x versus competing carriers",
            f"Passenger share change {float(row.share_change_pp) * 100:+.1f} percentage points year over year",
            f"Conditional 2025 Q3 forecast {float(row.forecast_yoy_change) * 100:+.1f}% versus 2024 Q3",
        ]
        route_records.append(
            {
                "id": row.entity_id,
                "origin": row.origin_code,
                "destination": row.destination_code,
                "carrier": row.carrier_code,
                "carrierName": names.get(row.carrier_code, row.carrier_code),
                "distanceMiles": int(round(float(row.distance_miles))),
                "baselineFare": round(float(row.weighted_fare_usd), 2),
                "passengers": int(row.t100_passengers),
                "seats": int(row.available_seats),
                "loadFactor": round(float(row.load_factor), 6),
                "marketShare": round(float(row.market_share), 6),
                "hhi": round(float(row.hhi), 6),
                "fareIndex": round(float(row.fare_index), 6),
                "observedFareMin": round(observed_fare_min, 2),
                "observedFareMax": round(observed_fare_max, 2),
                "observations": int(len(entity_history)),
                "action": row.action,
                "confidence": confidence,
                "score": int(row.score),
                "rationale": row.rationale,
                "evidence": evidence,
                "changes": {
                    "fareYoY": round(float(row.fare_change_yoy), 6),
                    "passengersYoY": round(float(row.passenger_change_yoy), 6),
                    "seatsYoY": round(float(row.seat_change_yoy), 6),
                    "shareYoYPoints": round(float(row.share_change_pp), 6),
                },
                "forecast": {
                    "period": "2025Q3",
                    "passengers": int(round(float(row.forecast_passengers))),
                    "low": int(round(float(row.forecast_low))),
                    "high": int(round(float(row.forecast_high))),
                    "yearOverYearChange": round(float(row.forecast_yoy_change), 6),
                    "assumption": "Fare, seats, competitor fare, and market structure held at 2025 Q2 inputs",
                },
                "scenarioPolicy": {
                    "defaultElasticity": -1.0,
                    "sensitivityLow": -1.5,
                    "sensitivityHigh": -0.5,
                    "source": "Analyst assumption, not estimated from the DOT panel",
                },
                "history": _history_records(entity_history),
            }
        )

    forecast_card = json.loads(forecast_card_path.read_text(encoding="utf-8"))
    elasticity_card = json.loads(elasticity_card_path.read_text(encoding="utf-8"))
    share_card = json.loads(share_card_path.read_text(encoding="utf-8"))
    iv_card = json.loads(iv_card_path.read_text(encoding="utf-8"))
    return {
        "schema_version": "2.1.0",
        "data_mode": "dot_observed",
        "source_vintage": "DB1B 2017Q1 to 2025Q2 | T-100 2017 to 2025",
        "built_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "title": "U.S. route pricing decision lab",
        "notice": "Observed DOT market data with model-backed conditional forecasts.",
        "quality": _quality_summary(database),
        "forecastModel": {
            "version": forecast_card["model_version"],
            "champion": forecast_card["champion"],
            "wape": forecast_card["aggregate_gradient_boosting"]["wape"],
            "bias": forecast_card["aggregate_gradient_boosting"]["bias"],
            "seasonalNaiveWape": forecast_card["aggregate_seasonal_naive"]["wape"],
            "intervalLevel": forecast_card["interval_calibration"]["level"],
            "intervalCoverage": forecast_card["interval_calibration"]["empirical_coverage"],
            "intervalEvaluationPeriods": forecast_card["interval_calibration"][
                "evaluation_periods"
            ],
            "intervalEvaluationObservations": forecast_card["interval_calibration"]["observations"],
            "intervalCalibrationObservations": forecast_card["interval_calibration"][
                "calibration_observations"
            ],
            "validationObservations": forecast_card["aggregate_gradient_boosting"]["observations"],
        },
        "identificationAudit": {
            "status": "No DOT-derived elasticity is approved for scenario use",
            "passengerFixedEffectsCoefficient": elasticity_card["coefficients"][0]["estimate"],
            "marketShareFixedEffectsCoefficient": share_card["fare_coefficient"],
            "ivSensitivityCoefficient": iv_card["fare_estimate"],
            "reason": "All three fare coefficients are nonnegative, which is inconsistent with an identified downward-sloping demand response and indicates endogeneity.",
        },
        "routes": route_records,
    }


def export_artifact(output: Path, **kwargs: Any) -> dict[str, Any]:
    artifact = build_artifact(**kwargs)
    if artifact["data_mode"] != "dot_observed":
        raise ValueError("Production web export requires DOT observed data")
    if not artifact["routes"]:
        raise ValueError("Production web export has no supported routes")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(artifact, allow_nan=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="Export FareLab's production web artifact")
    parser.add_argument(
        "--database", type=Path, default=Path("data/processed/farelab_panel.duckdb")
    )
    parser.add_argument(
        "--model-bundle", type=Path, default=Path("models/demand_forecast_v1.joblib")
    )
    parser.add_argument(
        "--forecast-card", type=Path, default=Path("models/demand_forecast_v1.json")
    )
    parser.add_argument(
        "--elasticity-card", type=Path, default=Path("models/elasticity_fe_v1.json")
    )
    parser.add_argument("--share-card", type=Path, default=Path("models/market_share_fe_v1.json"))
    parser.add_argument(
        "--iv-card", type=Path, default=Path("models/elasticity_iv_sensitivity_v1.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("web/public/data/farelab-overview.json")
    )
    parser.add_argument("--maximum-routes", type=int, default=60)
    args = parser.parse_args()
    artifact = export_artifact(
        output=args.output,
        database=args.database,
        model_bundle_path=args.model_bundle,
        forecast_card_path=args.forecast_card,
        elasticity_card_path=args.elasticity_card,
        share_card_path=args.share_card,
        iv_card_path=args.iv_card,
        maximum_routes=args.maximum_routes,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "routes": len(artifact["routes"]),
                "schema_version": artifact["schema_version"],
                "data_mode": artifact["data_mode"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
