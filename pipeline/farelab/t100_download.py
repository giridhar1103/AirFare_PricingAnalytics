"""Download selected T-100 domestic segment fields from the official BTS form."""

import argparse
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


T100_FORM_URL = (
    "https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=&gnoyr_VQ=FIM"
)
T100_FIELDS = (
    "DEPARTURES_SCHEDULED",
    "DEPARTURES_PERFORMED",
    "SEATS",
    "PASSENGERS",
    "DISTANCE",
    "UNIQUE_CARRIER",
    "AIRLINE_ID",
    "CARRIER_NAME",
    "ORIGIN_AIRPORT_ID",
    "ORIGIN_CITY_MARKET_ID",
    "ORIGIN",
    "DEST_AIRPORT_ID",
    "DEST_CITY_MARKET_ID",
    "DEST",
    "YEAR",
    "QUARTER",
    "MONTH",
    "DISTANCE_GROUP",
    "CLASS",
)


class HiddenInputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        attributes = dict(attrs)
        if attributes.get("type", "").lower() == "hidden" and attributes.get("name"):
            self.values[attributes["name"]] = attributes.get("value") or ""


def download_t100(year: int, destination: Path, period: str = "All") -> Path:
    if not 1990 <= year <= 2026:
        raise ValueError("T-100 year must be between 1990 and 2026")
    if period != "All" and period not in {str(month) for month in range(1, 13)}:
        raise ValueError("Period must be All or a month number from 1 to 12")

    if destination.exists():
        return destination

    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    headers = {"User-Agent": "FareLab research pipeline (public DOT data)"}
    with opener.open(Request(T100_FORM_URL, headers=headers), timeout=120) as response:
        page = response.read().decode("utf-8")

    parser = HiddenInputParser()
    parser.feed(page)
    required_tokens = {"__VIEWSTATE", "__EVENTVALIDATION"}
    if not required_tokens.issubset(parser.values):
        raise RuntimeError("Official T-100 form did not provide required request tokens")

    payload = dict(parser.values)
    payload.update(
        {
            "cboGeography": "All",
            "cboYear": str(year),
            "cboPeriod": period,
            "btnDownload": "Download",
        }
    )
    payload.update({field: "on" for field in T100_FIELDS})
    request = Request(
        T100_FORM_URL,
        data=urlencode(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with opener.open(request, timeout=300) as response, partial.open("wb") as output:
        content_type = response.headers.get_content_type()
        if content_type in {"text/html", "text/plain"}:
            preview = response.read(500).decode("utf-8", errors="replace")
            raise RuntimeError(f"T-100 form returned {content_type} instead of an archive: {preview}")
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    partial.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Download selected official T-100 segment fields")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--period", default="All")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path("data/raw") / f"t100_domestic_segment_{args.year}_{args.period}.zip"
    print(download_t100(args.year, output, args.period))


if __name__ == "__main__":
    main()
