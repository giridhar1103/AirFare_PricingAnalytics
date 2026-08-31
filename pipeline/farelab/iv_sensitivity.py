"""Research-only IV sensitivity for fare endogeneity.

This module is not a production causal model. It tests whether a leave-one-route-out
carrier-network fare shifter changes the sign of the observational fare coefficient.
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from linearmodels.iv import IV2SLS

from .elasticity import load_panel


@dataclass(frozen=True)
class IVSensitivityCard:
    model_version: str
    built_at_utc: str
    model_type: str
    observations: int
    entities: int
    periods: int
    fare_estimate: float
    fare_std_error: float
    fare_confidence_low: float
    fare_confidence_high: float
    first_stage_partial_f: float
    first_stage_partial_r_squared: float
    instrument: str
    exclusion_assumption: str
    status: str


def add_network_fare_instrument(panel: pd.DataFrame) -> pd.DataFrame:
    frame = panel.copy()
    frame["fare_weighted_sample"] = frame["weighted_fare_usd"] * frame["sampled_passengers"]
    grouping = frame.groupby(["carrier_code", "time_id"], observed=True)
    frame["network_fare_dollars"] = grouping["fare_weighted_sample"].transform("sum")
    frame["network_sampled_passengers"] = grouping["sampled_passengers"].transform("sum")
    numerator = frame["network_fare_dollars"] - frame["fare_weighted_sample"]
    denominator = frame["network_sampled_passengers"] - frame["sampled_passengers"]
    frame["other_market_fare"] = numerator / denominator.replace(0, np.nan)
    frame = frame.loc[frame["other_market_fare"].between(50, 2000)].copy()
    frame["log_other_market_fare"] = np.log(frame["other_market_fare"])
    return frame


def fit_iv_sensitivity(panel: pd.DataFrame) -> tuple[object, pd.DataFrame]:
    frame = add_network_fare_instrument(panel)
    entity_codes = pd.Categorical(frame["entity_id"]).codes
    time_codes = pd.Categorical(frame["time_id"]).codes
    absorber = pyhdfe.create(
        np.column_stack([entity_codes, time_codes]),
        drop_singletons=False,
    )
    columns = [
        "log_passengers",
        "log_seats",
        "log_competitor_fare",
        "log_fare",
        "log_other_market_fare",
    ]
    residualized = absorber.residualize(frame[columns].to_numpy())
    residual = pd.DataFrame(residualized, columns=columns, index=frame.index)
    model = IV2SLS(
        dependent=residual["log_passengers"],
        exog=residual[["log_seats", "log_competitor_fare"]],
        endog=residual[["log_fare"]],
        instruments=residual[["log_other_market_fare"]],
    )
    clusters = pd.Series(entity_codes, index=frame.index)
    result = model.fit(cov_type="clustered", clusters=clusters, debiased=True)
    return result, frame


def build_card(result: object, frame: pd.DataFrame) -> IVSensitivityCard:
    confidence = result.conf_int().loc["log_fare"]
    diagnostic = result.first_stage.diagnostics.loc["log_fare"]
    estimate = float(result.params["log_fare"])
    first_stage_f = float(diagnostic["f.stat"])
    partial_r2 = float(diagnostic["partial.rsquared"])
    sign_status = "research_only_negative_sign" if estimate < 0 else "research_only_nonnegative_sign"
    return IVSensitivityCard(
        model_version="elasticity-iv-network-fare-sensitivity-v1",
        built_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        model_type="Two-way absorbed 2SLS sensitivity",
        observations=int(result.nobs),
        entities=int(frame["entity_id"].nunique()),
        periods=int(frame["time_id"].nunique()),
        fare_estimate=estimate,
        fare_std_error=float(result.std_errors["log_fare"]),
        fare_confidence_low=float(confidence.iloc[0]),
        fare_confidence_high=float(confidence.iloc[1]),
        first_stage_partial_f=first_stage_f,
        first_stage_partial_r_squared=partial_r2,
        instrument="Passenger-weighted carrier fare on all other supported routes in the same quarter",
        exclusion_assumption=(
            "After route-carrier effects, period effects, capacity, and competitor fare controls, "
            "the carrier's other-route fare affects focal-route passengers only through focal-route fare."
        ),
        status=sign_status,
    )


def run(database: Path, output: Path) -> IVSensitivityCard:
    panel = load_panel(database)
    result, frame = fit_iv_sensitivity(panel)
    card = build_card(result, frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(card), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return card


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FareLab's research-only IV sensitivity")
    parser.add_argument("--database", type=Path, default=Path("data/processed/farelab_panel.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("models/elasticity_iv_sensitivity_v1.json"))
    args = parser.parse_args()
    print(json.dumps(asdict(run(args.database, args.output)), indent=2))


if __name__ == "__main__":
    main()
