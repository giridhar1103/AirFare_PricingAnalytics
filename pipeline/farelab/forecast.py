"""Time-validated conditional passenger-demand forecasting for FareLab."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


MODEL_VERSION = "conditional-demand-forecast-v1"


FORECAST_QUERY = """
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
        hhi
    from mart_route_carrier_quarter
    where data_status = 'accepted'
      and weighted_fare_usd between 50 and 2000
      and t100_passengers >= 100
      and available_seats >= 100
),
support as (
    select route_id, carrier_code, count(*) as periods
    from base
    group by route_id, carrier_code
    having count(*) >= 12
)
select base.*
from base
join support using (route_id, carrier_code)
order by route_id, carrier_code, service_year, service_quarter
"""


NUMERIC_FEATURES = [
    "log_lag1_passengers",
    "log_lag4_passengers",
    "log_fare",
    "log_seats",
    "log_competitor_fare",
    "lag1_load_factor",
    "lag1_market_share",
    "hhi",
    "log_distance",
    "quarter_sin",
    "quarter_cos",
    "trend",
    "competitor_fare_missing",
]
CATEGORICAL_FEATURES = ["carrier_code"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass(frozen=True)
class MetricSet:
    mae: float
    wape: float
    bias: float
    observations: int


@dataclass(frozen=True)
class FoldResult:
    fold: str
    train_through: str
    test_periods: list[str]
    seasonal_naive: MetricSet
    ridge: MetricSet
    gradient_boosting: MetricSet


@dataclass(frozen=True)
class IntervalCalibration:
    level: float
    method: str
    log_absolute_error_quantile: float
    empirical_coverage: float
    observations: int


@dataclass(frozen=True)
class ForecastModelCard:
    model_version: str
    built_at_utc: str
    task: str
    data_period: str
    forecast_horizon: str
    target: str
    features: list[str]
    validation: str
    excluded_training_years: list[int]
    folds: list[FoldResult]
    aggregate_seasonal_naive: MetricSet
    aggregate_ridge: MetricSet
    aggregate_gradient_boosting: MetricSet
    interval_calibration: IntervalCalibration
    champion: str
    promotion_rule: str
    interpretation: str
    limitation: str


def load_history(database: Path) -> pd.DataFrame:
    with duckdb.connect(str(database), read_only=True) as connection:
        frame = connection.execute(FORECAST_QUERY).fetch_df()
    if frame.empty:
        raise ValueError("No supported route history was found for forecasting")
    frame["entity_id"] = frame["route_id"] + ":" + frame["carrier_code"]
    frame["period_index"] = frame["service_year"] * 4 + frame["service_quarter"]
    return frame


def build_supervised_frame(history: pd.DataFrame) -> pd.DataFrame:
    current = history.copy()
    lag_columns = [
        "entity_id",
        "period_index",
        "t100_passengers",
        "load_factor",
        "market_share",
    ]
    lag1 = history[lag_columns].copy()
    lag1["period_index"] += 1
    lag1 = lag1.rename(
        columns={
            "t100_passengers": "lag1_passengers",
            "load_factor": "lag1_load_factor",
            "market_share": "lag1_market_share",
        }
    )
    lag4 = history[["entity_id", "period_index", "t100_passengers"]].copy()
    lag4["period_index"] += 4
    lag4 = lag4.rename(columns={"t100_passengers": "lag4_passengers"})
    frame = current.merge(lag1, on=["entity_id", "period_index"], how="left")
    frame = frame.merge(lag4, on=["entity_id", "period_index"], how="left")
    frame = frame.dropna(subset=["lag1_passengers", "lag4_passengers"]).copy()
    frame["competitor_fare_missing"] = frame["competitor_weighted_fare_usd"].isna().astype(float)
    frame["competitor_fare_filled"] = frame["competitor_weighted_fare_usd"].fillna(
        frame["weighted_fare_usd"]
    )
    frame["log_lag1_passengers"] = np.log1p(frame["lag1_passengers"])
    frame["log_lag4_passengers"] = np.log1p(frame["lag4_passengers"])
    frame["log_fare"] = np.log(frame["weighted_fare_usd"])
    frame["log_seats"] = np.log(frame["available_seats"])
    frame["log_competitor_fare"] = np.log(frame["competitor_fare_filled"])
    frame["log_distance"] = np.log1p(frame["distance_miles"])
    frame["quarter_sin"] = np.sin(2 * np.pi * frame["service_quarter"] / 4)
    frame["quarter_cos"] = np.cos(2 * np.pi * frame["service_quarter"] / 4)
    frame["trend"] = frame["period_index"] - frame["period_index"].min()
    frame["target_log_passengers"] = np.log1p(frame["t100_passengers"])
    return frame


def _ridge_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "carrier",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("model", Ridge(alpha=3.0))])


def _boosting_matrix(frame: pd.DataFrame, carrier_map: dict[str, int]) -> np.ndarray:
    numeric = frame[NUMERIC_FEATURES].to_numpy(dtype=float)
    carrier = frame["carrier_code"].map(carrier_map).fillna(-1).to_numpy(dtype=float).reshape(-1, 1)
    return np.column_stack([numeric, carrier])


def _boosting_model() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.05,
        max_iter=240,
        max_leaf_nodes=31,
        min_samples_leaf=30,
        l2_regularization=0.2,
        categorical_features=[len(NUMERIC_FEATURES)],
        early_stopping=True,
        validation_fraction=0.12,
        n_iter_no_change=20,
        random_state=42,
    )


def _to_passengers(log_prediction: np.ndarray) -> np.ndarray:
    return np.maximum(np.expm1(log_prediction), 0)


def metrics(actual: np.ndarray, predicted: np.ndarray) -> MetricSet:
    errors = predicted - actual
    denominator = float(np.abs(actual).sum())
    return MetricSet(
        mae=float(np.abs(errors).mean()),
        wape=float(np.abs(errors).sum() / denominator) if denominator else 0.0,
        bias=float(errors.sum() / denominator) if denominator else 0.0,
        observations=int(len(actual)),
    )


def _aggregate(actual: list[np.ndarray], predicted: list[np.ndarray]) -> MetricSet:
    return metrics(np.concatenate(actual), np.concatenate(predicted))


def backtest(
    frame: pd.DataFrame,
) -> tuple[ForecastModelCard, object, dict[str, int], IntervalCalibration]:
    fold_definitions = [
        ("2023", 2023, ["2023Q1", "2023Q2", "2023Q3", "2023Q4"]),
        ("2024", 2024, ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]),
        ("2025H1", 2025, ["2025Q1", "2025Q2"]),
    ]
    folds: list[FoldResult] = []
    actuals: list[np.ndarray] = []
    naive_predictions: list[np.ndarray] = []
    ridge_predictions: list[np.ndarray] = []
    boosting_predictions: list[np.ndarray] = []

    for label, test_year, test_periods in fold_definitions:
        train = frame.loc[
            (frame["service_year"] < test_year)
            & (~frame["service_year"].isin([2020, 2021]))
        ].copy()
        test = frame.loc[frame["period_key"].isin(test_periods)].copy()
        if train.empty or test.empty:
            raise ValueError(f"Forecast fold {label} has no train or test observations")

        ridge = _ridge_pipeline()
        ridge.fit(train[ALL_FEATURES], train["target_log_passengers"])
        ridge_pred = _to_passengers(ridge.predict(test[ALL_FEATURES]))

        carrier_values = sorted(train["carrier_code"].unique())
        carrier_map = {carrier: index for index, carrier in enumerate(carrier_values)}
        boosting = _boosting_model()
        boosting.fit(
            _boosting_matrix(train, carrier_map),
            train["target_log_passengers"].to_numpy(),
        )
        boosting_pred = _to_passengers(boosting.predict(_boosting_matrix(test, carrier_map)))

        actual = test["t100_passengers"].to_numpy(dtype=float)
        naive = test["lag4_passengers"].to_numpy(dtype=float)
        actuals.append(actual)
        naive_predictions.append(naive)
        ridge_predictions.append(ridge_pred)
        boosting_predictions.append(boosting_pred)
        folds.append(
            FoldResult(
                fold=label,
                train_through=str(train["period_key"].max()),
                test_periods=test_periods,
                seasonal_naive=metrics(actual, naive),
                ridge=metrics(actual, ridge_pred),
                gradient_boosting=metrics(actual, boosting_pred),
            )
        )

    aggregate_naive = _aggregate(actuals, naive_predictions)
    aggregate_ridge = _aggregate(actuals, ridge_predictions)
    aggregate_boosting = _aggregate(actuals, boosting_predictions)
    combined_actual = np.concatenate(actuals)
    combined_boosting = np.concatenate(boosting_predictions)
    absolute_log_error = np.abs(
        np.log1p(combined_actual) - np.log1p(combined_boosting)
    )
    interval_level = 0.80
    interval_quantile = float(
        np.quantile(absolute_log_error, interval_level, method="higher")
    )
    predicted_log = np.log1p(combined_boosting)
    interval_low = np.maximum(np.expm1(predicted_log - interval_quantile), 0)
    interval_high = np.maximum(np.expm1(predicted_log + interval_quantile), 0)
    interval_calibration = IntervalCalibration(
        level=interval_level,
        method="Out-of-fold symmetric absolute-log-error conformal interval",
        log_absolute_error_quantile=interval_quantile,
        empirical_coverage=float(
            np.mean(
                (combined_actual >= interval_low)
                & (combined_actual <= interval_high)
            )
        ),
        observations=int(len(combined_actual)),
    )
    candidates = {
        "seasonal_naive": aggregate_naive,
        "ridge": aggregate_ridge,
        "gradient_boosting": aggregate_boosting,
    }
    champion = min(candidates, key=lambda name: candidates[name].wape)

    final_train = frame.loc[~frame["service_year"].isin([2020, 2021])].copy()
    final_carriers = sorted(final_train["carrier_code"].unique())
    final_carrier_map = {carrier: index for index, carrier in enumerate(final_carriers)}
    final_model = _boosting_model()
    final_model.fit(
        _boosting_matrix(final_train, final_carrier_map),
        final_train["target_log_passengers"].to_numpy(),
    )

    card = ForecastModelCard(
        model_version=MODEL_VERSION,
        built_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        task="Conditional next-quarter route-carrier passenger forecast",
        data_period=f"{frame['period_key'].min()} to {frame['period_key'].max()}",
        forecast_horizon="One quarter",
        target="T-100 scheduled passenger volume",
        features=ALL_FEATURES,
        validation="Three expanding-window folds with later calendar periods held out",
        excluded_training_years=[2020, 2021],
        folds=folds,
        aggregate_seasonal_naive=aggregate_naive,
        aggregate_ridge=aggregate_ridge,
        aggregate_gradient_boosting=aggregate_boosting,
        interval_calibration=interval_calibration,
        champion=champion,
        promotion_rule=(
            "Promote ML only when aggregate WAPE improves on seasonal naive and absolute bias "
            "does not exceed 5%."
        ),
        interpretation=(
            "This is a conditional forecast using observed or analyst-supplied fare and capacity "
            "inputs. Changing an input does not make the resulting difference causal."
        ),
        limitation=(
            "The model does not observe booking curves, fare-class inventory, search demand, "
            "schedule quality, ancillary revenue, or route accounting cost."
        ),
    )
    return card, final_model, final_carrier_map, interval_calibration


def run(database: Path, output: Path, model_output: Path) -> ForecastModelCard:
    history = load_history(database)
    frame = build_supervised_frame(history)
    card, model, carrier_map, interval_calibration = backtest(frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(card), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "carrier_map": carrier_map,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "model_version": MODEL_VERSION,
            "interval_calibration": asdict(interval_calibration),
            "trend_origin": int(frame["period_index"].min()),
        },
        model_output,
    )
    return card


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest and train FareLab's demand forecast")
    parser.add_argument("--database", type=Path, default=Path("data/processed/farelab_panel.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("models/demand_forecast_v1.json"))
    parser.add_argument("--model-output", type=Path, default=Path("models/demand_forecast_v1.joblib"))
    args = parser.parse_args()
    card = run(args.database, args.output, args.model_output)
    print(json.dumps(asdict(card), indent=2))


if __name__ == "__main__":
    main()
