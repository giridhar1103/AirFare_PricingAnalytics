import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from pipeline.farelab.ingest import db1b_filename, inspect_db1b_archive


class IngestTests(unittest.TestCase):
    def test_db1b_filename_and_collection_boundary(self):
        self.assertEqual(
            db1b_filename(2024, 4),
            "Origin_and_Destination_Survey_DB1BMarket_2024_4.zip",
        )
        with self.assertRaises(ValueError):
            db1b_filename(2025, 3)

    def test_archive_contract_checks_required_header(self):
        header = (
            "Year,Quarter,OriginAirportID,DestAirportID,RPCarrier,OpCarrier,"
            "Passengers,MktFare\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "sample.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("sample.csv", header + "2024,4,1,2,AA,AA,10,200\n")
            manifest = inspect_db1b_archive(archive_path, 2024, 4, "https://example.test/sample.zip")
            self.assertEqual(manifest.schema_status, "header_verified")
            self.assertEqual(manifest.source_period, "2024Q4")


if __name__ == "__main__":
    unittest.main()
