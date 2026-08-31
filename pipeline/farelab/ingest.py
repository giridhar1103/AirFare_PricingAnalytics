"""Reproducible source download and archive inspection utilities."""

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


DB1B_BASE_URL = "https://www.transtats.bts.gov/PREZIP"


@dataclass(frozen=True)
class SourceManifest:
    source_name: str
    source_period: str
    source_url: str
    downloaded_at_utc: str
    sha256: str
    byte_count: int
    archive_members: list[str]
    uncompressed_csv_bytes: int
    schema_status: str


def db1b_filename(year: int, quarter: int) -> str:
    if not 1993 <= year <= 2025:
        raise ValueError("DB1B year must be between 1993 and 2025")
    if quarter not in {1, 2, 3, 4}:
        raise ValueError("Quarter must be 1, 2, 3, or 4")
    if year == 2025 and quarter > 2:
        raise ValueError("DB1B collection ended after 2025 Q2")
    return f"Origin_and_Destination_Survey_DB1BMarket_{year}_{quarter}.zip"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_db1b_archive(path: Path, year: int, quarter: int, source_url: str) -> SourceManifest:
    with ZipFile(path) as archive:
        members = archive.namelist()
        csv_members = [name for name in members if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise ValueError(f"Expected exactly one CSV member, found {len(csv_members)}")
        csv_info = archive.getinfo(csv_members[0])
        with archive.open(csv_info) as csv_file:
            header = csv_file.readline().decode("utf-8-sig").strip()
        required_columns = {
            "Year",
            "Quarter",
            "OriginAirportID",
            "DestAirportID",
            "RPCarrier",
            "OpCarrier",
            "Passengers",
            "MktFare",
        }
        columns = {value.strip('"') for value in header.rstrip(",").split(",")}
        missing = required_columns.difference(columns)
        if missing:
            raise ValueError(f"DB1B schema missing required columns: {sorted(missing)}")
        return SourceManifest(
            source_name="DB1B Market",
            source_period=f"{year}Q{quarter}",
            source_url=source_url,
            downloaded_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            sha256=sha256_file(path),
            byte_count=path.stat().st_size,
            archive_members=members,
            uncompressed_csv_bytes=csv_info.file_size,
            schema_status="header_verified",
        )


def download_db1b(year: int, quarter: int, raw_dir: Path, manifest_dir: Path) -> SourceManifest:
    filename = db1b_filename(year, quarter)
    url = f"{DB1B_BASE_URL}/{filename}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / filename
    partial = raw_dir / f"{filename}.part"
    if not destination.exists():
        with urlopen(url, timeout=120) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        partial.replace(destination)
    manifest = inspect_db1b_archive(destination, year, quarter, url)
    manifest_path = manifest_dir / f"db1b_{year}q{quarter}.json"
    manifest_path.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify official FareLab source files")
    subparsers = parser.add_subparsers(dest="source", required=True)
    db1b = subparsers.add_parser("db1b", help="Download a quarterly DB1B market archive")
    db1b.add_argument("--year", type=int, required=True)
    db1b.add_argument("--quarter", type=int, required=True)
    db1b.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    db1b.add_argument("--manifest-dir", type=Path, default=Path("data/manifests"))
    args = parser.parse_args()
    manifest = download_db1b(args.year, args.quarter, args.raw_dir, args.manifest_dir)
    print(json.dumps(asdict(manifest), indent=2))


if __name__ == "__main__":
    main()
