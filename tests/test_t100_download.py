import unittest

from pipeline.farelab.t100_download import HiddenInputParser, T100_FIELDS


class T100DownloadTests(unittest.TestCase):
    def test_hidden_form_tokens_are_parsed(self):
        parser = HiddenInputParser()
        parser.feed(
            '<input type="hidden" name="__VIEWSTATE" value="abc" />'
            '<input type="hidden" name="__EVENTVALIDATION" value="xyz" />'
        )
        self.assertEqual(parser.values["__VIEWSTATE"], "abc")
        self.assertEqual(parser.values["__EVENTVALIDATION"], "xyz")

    def test_t100_contract_includes_stable_keys_and_capacity(self):
        required = {"AIRLINE_ID", "ORIGIN_AIRPORT_ID", "DEST_AIRPORT_ID", "SEATS", "PASSENGERS"}
        self.assertTrue(required.issubset(T100_FIELDS))


if __name__ == "__main__":
    unittest.main()
