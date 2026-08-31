"""Build the multi-period FareLab DuckDB warehouse from verified DOT archives."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from .ingest import DB1B_BASE_URL, db1b_filename, download_db1b
from .t100_download import T100_FORM_URL, download_t100


DB1B_PATTERN = re.compile(r"DB1BMarket_(?P<year>\d{4})_(?P<quarter>[1-4])\.zip$", re.IGNORECASE)
T100_PATTERN = re.compile(r"t100_domestic_segment_(?P<year>\d{4})_All\.zip$", re.IGNORECASE)


def source_periods(start_year: int, end_year: int) -> list[tuple[int, int]]:
    if start_year < 1993 or end_year > 2025 or start_year > end_year:
        raise ValueError("DB1B period range must be within 1993 through 2025")
    periods: list[tuple[int, int]] = []
    for year in range(start_year, end_year + 1):
        final_quarter = 2 if year == 2025 else 4
        periods.extend((year, quarter) for quarter in range(1, final_quarter + 1))
    return periods


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _run_duckdb(database: Path, sql: str) -> str:
    executable = shutil.which("duckdb")
    if executable is None:
        raise RuntimeError("DuckDB CLI is required but was not found")
    database.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [executable, str(database), "-c", sql],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_member(archive_path: Path) -> str:
    with ZipFile(archive_path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    if len(members) != 1:
        raise ValueError(f"Expected exactly one CSV in {archive_path.name}, found {len(members)}")
    return members[0]


def _record_source(
    database: Path,
    source_name: str,
    source_period: str,
    source_url: str,
    archive_path: Path,
    row_count: int,
) -> None:
    loaded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    values = {
        "source_name": source_name,
        "source_period": source_period,
        "source_url": source_url,
        "archive_name": archive_path.name,
        "sha256": _sha256(archive_path),
        "byte_count": archive_path.stat().st_size,
        "row_count": row_count,
        "loaded_at_utc": loaded_at,
    }
    escaped = {key: str(value).replace("'", "''") for key, value in values.items()}
    sql = f"""
    create table if not exists warehouse_source_manifest (
        source_name varchar,
        source_period varchar,
        source_url varchar,
        archive_name varchar,
        sha256 varchar,
        byte_count bigint,
        row_count bigint,
        loaded_at_utc timestamp,
        primary key (source_name, source_period)
    );
    delete from warehouse_source_manifest
    where source_name = '{escaped['source_name']}'
      and source_period = '{escaped['source_period']}';
    insert into warehouse_source_manifest values (
        '{escaped['source_name']}',
        '{escaped['source_period']}',
        '{escaped['source_url']}',
        '{escaped['archive_name']}',
        '{escaped['sha256']}',
        {values['byte_count']},
        {values['row_count']},
        '{escaped['loaded_at_utc']}'
    );
    """
    _run_duckdb(database, sql)


def load_db1b_archive(database: Path, archive_path: Path) -> int:
    match = DB1B_PATTERN.search(archive_path.name)
    if match is None:
        raise ValueError(f"Cannot identify DB1B period from {archive_path.name}")
    year = int(match.group("year"))
    quarter = int(match.group("quarter"))
    member = _csv_member(archive_path)
    with tempfile.TemporaryDirectory(prefix="farelab_db1b_") as directory:
        with ZipFile(archive_path) as archive:
            archive.extract(member, directory)
        csv_path = Path(directory) / member
        sql = f"""
        begin transaction;
        create table if not exists stg_db1b_market (
            service_year integer,
            service_quarter integer,
            origin_airport_id integer,
            destination_airport_id integer,
            origin_code varchar,
            destination_code varchar,
            reporting_carrier varchar,
            ticketing_carrier varchar,
            operating_carrier varchar,
            market_fare_usd double,
            sampled_passengers double,
            market_miles double,
            market_coupons integer,
            bulk_fare_flag integer
        );
        delete from stg_db1b_market
        where service_year = {year} and service_quarter = {quarter};
        insert into stg_db1b_market
        select
            cast(Year as integer),
            cast(Quarter as integer),
            cast(OriginAirportID as integer),
            cast(DestAirportID as integer),
            upper(trim(Origin)),
            upper(trim(Dest)),
            cast(RPCarrier as varchar),
            cast(TkCarrier as varchar),
            cast(OpCarrier as varchar),
            cast(MktFare as double),
            cast(Passengers as double),
            cast(MktMilesFlown as double),
            cast(MktCoupons as integer),
            cast(BulkFare as integer)
        from read_csv_auto(
            '{_sql_path(csv_path)}',
            header = true,
            sample_size = 100000,
            null_padding = true
        )
        where MktFare > 0
          and Passengers > 0
          and OriginCountry = 'US'
          and DestCountry = 'US'
          and Year = {year}
          and Quarter = {quarter};
        commit;
        select count(*) from stg_db1b_market
        where service_year = {year} and service_quarter = {quarter};
        """
        output = _run_duckdb(database, sql)
    row_count = _last_integer(output)
    source_url = f"{DB1B_BASE_URL}/{archive_path.name}"
    _record_source(database, "DB1B Market", f"{year}Q{quarter}", source_url, archive_path, row_count)
    return row_count


def load_t100_archive(database: Path, archive_path: Path) -> int:
    match = T100_PATTERN.search(archive_path.name)
    if match is None:
        raise ValueError(f"Cannot identify T-100 year from {archive_path.name}")
    year = int(match.group("year"))
    member = _csv_member(archive_path)
    with tempfile.TemporaryDirectory(prefix="farelab_t100_") as directory:
        with ZipFile(archive_path) as archive:
            archive.extract(member, directory)
        csv_path = Path(directory) / member
        sql = f"""
        begin transaction;
        create table if not exists stg_t100_segment (
            service_year integer,
            service_month integer,
            origin_airport_id integer,
            destination_airport_id integer,
            origin_code varchar,
            destination_code varchar,
            airline_id integer,
            carrier_code varchar,
            carrier_name varchar,
            passengers bigint,
            available_seats bigint,
            departures_performed integer,
            distance_miles double
        );
        delete from stg_t100_segment where service_year = {year};
        insert into stg_t100_segment
        select
            cast(YEAR as integer),
            cast(MONTH as integer),
            cast(ORIGIN_AIRPORT_ID as integer),
            cast(DEST_AIRPORT_ID as integer),
            upper(trim(ORIGIN)),
            upper(trim(DEST)),
            cast(AIRLINE_ID as integer),
            cast(UNIQUE_CARRIER as varchar),
            cast(CARRIER_NAME as varchar),
            cast(PASSENGERS as bigint),
            cast(SEATS as bigint),
            cast(DEPARTURES_PERFORMED as integer),
            cast(DISTANCE as double)
        from read_csv_auto('{_sql_path(csv_path)}', header = true)
        where CLASS = 'F'
          and PASSENGERS >= 0
          and SEATS > 0
          and YEAR = {year};
        commit;
        select count(*) from stg_t100_segment where service_year = {year};
        """
        output = _run_duckdb(database, sql)
    row_count = _last_integer(output)
    _record_source(
        database,
        "T-100 Domestic Segment U.S. Carriers",
        str(year),
        T100_FORM_URL,
        archive_path,
        row_count,
    )
    return row_count


def _last_integer(output: str) -> int:
    numbers = re.findall(r"│\s*(\d+)\s*│", output)
    if not numbers:
        raise RuntimeError(f"Could not parse DuckDB row count from output: {output}")
    return int(numbers[-1])


def rebuild_marts(database: Path, repository_root: Path) -> dict[str, object]:
    transformations = (
        repository_root / "sql/intermediate/int_db1b_direct_route_fares.sql",
        repository_root / "sql/intermediate/int_t100_route_quarter.sql",
        repository_root / "sql/marts/mart_route_carrier_quarter.sql",
    )
    for path in transformations:
        _run_duckdb(database, path.read_text(encoding="utf-8"))
    query = """
    select
        count(*) as mart_rows,
        count(distinct route_id) as routes,
        count(distinct carrier_code) as carriers,
        min(period_key) as first_period,
        max(period_key) as last_period,
        sum(case when data_status = 'accepted' then 1 else 0 end) as accepted_rows,
        sum(case when competitor_fare_index is not null then 1 else 0 end) as competitive_rows
    from mart_route_carrier_quarter;
    """
    executable = shutil.which("duckdb")
    if executable is None:
        raise RuntimeError("DuckDB CLI is required but was not found")
    result = subprocess.run(
        [executable, "-json", str(database), "-c", query],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(result.stdout)
    return rows[0] if rows else {}


def build(
    start_year: int,
    end_year: int,
    raw_dir: Path,
    manifest_dir: Path,
    database: Path,
    download: bool,
) -> dict[str, object]:
    repository_root = Path(__file__).resolve().parents[2]
    periods = source_periods(start_year, end_year)
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    for year, quarter in periods:
        filename = db1b_filename(year, quarter)
        archive = raw_dir / filename
        print(f"DB1B {year} Q{quarter}: preparing", flush=True)
        if download:
            download_db1b(year, quarter, raw_dir, manifest_dir)
        if not archive.exists():
            raise FileNotFoundError(f"Missing DB1B archive: {archive}")
        rows = load_db1b_archive(database, archive)
        print(f"DB1B {year} Q{quarter}: loaded {rows:,} staged rows", flush=True)

    for year in range(start_year, end_year + 1):
        archive = raw_dir / f"t100_domestic_segment_{year}_All.zip"
        print(f"T-100 {year}: preparing", flush=True)
        if download:
            download_t100(year, archive, "All")
        if not archive.exists():
            raise FileNotFoundError(f"Missing T-100 archive: {archive}")
        rows = load_t100_archive(database, archive)
        print(f"T-100 {year}: loaded {rows:,} staged rows", flush=True)

    print("Rebuilding analytical marts", flush=True)
    summary = rebuild_marts(database, repository_root)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the FareLab multi-period DuckDB warehouse")
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/manifests"))
    parser.add_argument("--database", type=Path, default=Path("data/processed/farelab_panel.duckdb"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    build(
        start_year=args.start_year,
        end_year=args.end_year,
        raw_dir=args.raw_dir,
        manifest_dir=args.manifest_dir,
        database=args.database,
        download=args.download,
    )


if __name__ == "__main__":
    main()
