"""Verify and package FareLab's static production release."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import validate_artifact


REQUIRED_ACTIONS = {
    "Evaluate yield",
    "Protect share",
    "Review capacity",
    "Review fare position",
    "Hold and monitor",
}
ASSET_REFERENCE = re.compile(r'(?:src|href)="(?P<path>/farelab/[^"?#]+)')


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as source:
        return tomllib.load(source)


def _verify_index(index_path: Path, dist: Path, base_path: str) -> list[str]:
    text = index_path.read_text(encoding="utf-8")
    references = [match.group("path") for match in ASSET_REFERENCE.finditer(text)]
    if not references:
        raise ValueError("Production index contains no FareLab asset references")
    invalid = [reference for reference in references if not reference.startswith(base_path)]
    if invalid:
        raise ValueError(f"Asset references escape {base_path}: {invalid}")
    missing = []
    for reference in references:
        relative = reference.removeprefix(base_path)
        if not (dist / relative).is_file():
            missing.append(reference)
    if missing:
        raise ValueError(f"Production index references missing files: {missing}")
    if "/src/" in text:
        raise ValueError("Production index still references source files")
    return references


def _verify_artifact(
    artifact_path: Path,
    source_artifact_path: Path,
    expected_schema: str,
    maximum_bytes: int,
) -> dict[str, Any]:
    if artifact_path.stat().st_size > maximum_bytes:
        raise ValueError(
            f"Overview artifact is {artifact_path.stat().st_size} bytes, above {maximum_bytes}"
        )
    if source_artifact_path.is_file() and sha256_file(artifact_path) != sha256_file(source_artifact_path):
        raise ValueError("Built overview artifact is stale relative to web/public")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    validate_artifact(artifact, production=True)
    if artifact["schema_version"] != expected_schema:
        raise ValueError(
            f"Artifact schema {artifact['schema_version']} does not match {expected_schema}"
        )
    routes = artifact.get("routes", [])
    if not routes:
        raise ValueError("Production artifact contains no routes")
    actions = {route.get("action") for route in routes}
    if actions != REQUIRED_ACTIONS:
        raise ValueError(f"Production action coverage is incomplete: {sorted(actions)}")
    if "no dot-derived elasticity" not in artifact.get("identificationAudit", {}).get("status", "").lower():
        raise ValueError("Identification audit does not reject DOT-derived elasticity")
    for route in routes:
        if any(field in route for field in ("elasticity", "elasticityLow", "elasticityHigh")):
            raise ValueError(f"Route {route.get('id')} exposes a rejected elasticity estimate")
        policy = route.get("scenarioPolicy", {})
        if "assumption" not in str(policy.get("source", "")).lower():
            raise ValueError(f"Route {route.get('id')} does not identify its scenario assumption")
        forecast = route.get("forecast", {})
        if not (forecast.get("low", 0) <= forecast.get("passengers", -1) <= forecast.get("high", -1)):
            raise ValueError(f"Route {route.get('id')} has an invalid forecast interval")
    return artifact


def verify_release(repository_root: Path, dist: Path) -> dict[str, Any]:
    config = _project_config(repository_root / "config/project.toml")
    base_path = str(config["project"]["public_base_path"])
    expected_schema = str(config["artifacts"]["schema_version"])
    maximum_bytes = int(config["artifacts"]["maximum_overview_bytes"])
    index_path = dist / "index.html"
    artifact_path = dist / "data/farelab-overview.json"
    if not index_path.is_file() or not artifact_path.is_file():
        raise FileNotFoundError("FareLab release requires dist/index.html and the overview artifact")
    source_maps = sorted(path.relative_to(dist).as_posix() for path in dist.rglob("*.map"))
    if source_maps:
        raise ValueError(f"Production release contains source maps: {source_maps}")
    references = _verify_index(index_path, dist, base_path)
    artifact = _verify_artifact(
        artifact_path,
        repository_root / "web/public/data/farelab-overview.json",
        expected_schema,
        maximum_bytes,
    )
    files = sorted(path for path in dist.rglob("*") if path.is_file())
    return {
        "release_schema": "1.0.0",
        "verified_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "public_base_path": base_path,
        "source_vintage": artifact["source_vintage"],
        "artifact_schema": artifact["schema_version"],
        "route_count": len(artifact["routes"]),
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "entrypoint_references": references,
        "files": [
            {
                "path": path.relative_to(dist).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }


def build_bundle(repository_root: Path, dist: Path, output: Path) -> dict[str, Any]:
    manifest = verify_release(repository_root, dist)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="farelab_release_") as directory:
        staging_root = Path(directory) / "farelab"
        shutil.copytree(dist, staging_root)
        (staging_root / "release-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        with tarfile.open(output, "w:gz") as archive:
            archive.add(staging_root, arcname="farelab")
    manifest["bundle"] = {
        "path": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
    }
    return manifest


def preflight_host(host_root: Path) -> dict[str, Any]:
    """Inspect the portfolio host without changing it."""
    package_path = host_root / "package.json"
    public_dir = host_root / "client/public"
    redirects_path = public_dir / "_redirects"
    required = [package_path, public_dir, redirects_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Portfolio host contract is incomplete: {missing}")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    build_command = package.get("scripts", {}).get("build:pages")
    if not build_command:
        raise ValueError("Portfolio host has no build:pages script")
    redirect_lines = [
        line.strip()
        for line in redirects_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    global_fallback = next((line for line in redirect_lines if line.split()[0] == "/*"), None)
    if global_fallback is None:
        raise ValueError("Portfolio host has no global SPA fallback")
    farelab_rule = next(
        (line for line in redirect_lines if line.split()[0].rstrip("/") == "/farelab/*".rstrip("/")),
        None,
    )
    target = public_dir / "farelab"
    existing_files = sorted(
        path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
    ) if target.is_dir() else []
    return {
        "host_root": str(host_root.resolve()),
        "deployment_type": "Cloudflare Pages static build",
        "build_command": build_command,
        "public_directory": str(public_dir.resolve()),
        "farelab_target": str(target.resolve()),
        "farelab_target_exists": target.exists(),
        "farelab_existing_file_count": len(existing_files),
        "global_fallback": global_fallback,
        "farelab_fallback": farelab_rule,
        "required_changes": [
            *([] if target.exists() else ["Install verified static bundle at client/public/farelab"]),
            *([] if farelab_rule else ["Insert /farelab/* fallback before the global fallback"]),
        ],
        "service_changes_required": False,
        "port_changes_required": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or package a FareLab static release")
    parser.add_argument("command", choices=("verify", "bundle", "host-preflight"))
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--dist", type=Path, default=Path("web/dist"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/farelab-static.tar.gz"))
    parser.add_argument("--host-root", type=Path, default=Path("/root/MyWebsiteHost"))
    args = parser.parse_args()
    repository_root = args.repository_root.resolve()
    dist = (repository_root / args.dist).resolve() if not args.dist.is_absolute() else args.dist
    if args.command == "verify":
        result = verify_release(repository_root, dist)
    elif args.command == "bundle":
        output = (repository_root / args.output).resolve() if not args.output.is_absolute() else args.output
        result = build_bundle(repository_root, dist, output)
    else:
        result = preflight_host(args.host_root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
