import unittest
import tempfile
import warnings

from serpens import csvutils


class TestCsvUtils(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter(action="ignore", category=ResourceWarning)

    def test_utf8_with_bom(self):
        reader = csvutils.open_csv_reader("tests/samples/fruits_utf8bom.csv")

        self.assertEqual(reader.fieldnames, ["id", "name"])

        line = next(reader)
        self.assertEqual(line, {"id": "1", "name": "Açaí"})

    def test_utf8_without_bom(self):
        reader = csvutils.open_csv_reader("tests/samples/fruits_utf8.csv")
        self.assertEqual(reader.fieldnames, ["id", "name"])

        line = next(reader)
        self.assertEqual(line, {"id": "1", "name": "Açaí"})

    def test_iso8859(self):
        reader = csvutils.open_csv_reader("tests/samples/fruits_iso8859.csv")
        self.assertEqual(reader.fieldnames, ["id", "name"])

        line = next(reader)
        self.assertEqual(line, {"id": "1", "name": "Açaí"})
        del reader

    def test_writer(self):
        _, temp = tempfile.mkstemp()
        writer = csvutils.open_csv_writer(temp)
        writer.writerow(["id", "name"])
        writer.writerow(["1", "Açaí"])
        del writer

        reader = csvutils.open_csv_reader(temp)
        self.assertEqual(reader.fieldnames, ["id", "name"])

        line = next(reader)
        self.assertEqual(line, {"id": "1", "name": "Açaí"})
