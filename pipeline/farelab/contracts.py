"""Artifact contract checks shared by export tasks."""

from datetime import datetime
from typing import Any


REQUIRED_METADATA = {
    "schema_version",
    "data_mode",
    "source_vintage",
    "built_at_utc",
}


def validate_artifact(artifact: dict[str, Any], production: bool = False) -> None:
    missing = REQUIRED_METADATA.difference(artifact)
    if missing:
        raise ValueError(f"Artifact metadata missing: {sorted(missing)}")
    try:
        datetime.fromisoformat(str(artifact["built_at_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("built_at_utc must be ISO 8601") from exc
    if production and artifact["data_mode"] != "dot_observed":
        raise ValueError("Production export requires data_mode=dot_observed")
    if not artifact["source_vintage"]:
        raise ValueError("source_vintage cannot be empty")
