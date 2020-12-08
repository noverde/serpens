import tempfile
from serpens import csvutils


def test_utf8_with_bom():
    reader = csvutils.open_csv_reader("tests/samples/fruits_utf8bom.csv")

    assert reader.fieldnames == ["id", "name"]

    line = next(reader)
    assert line == {"id": "1", "name": "Açaí"}


def test_utf8_without_bom():
    reader = csvutils.open_csv_reader("tests/samples/fruits_utf8.csv")
    assert reader.fieldnames == ["id", "name"]

    line = next(reader)
    assert line == {"id": "1", "name": "Açaí"}


def test_iso8859():
    reader = csvutils.open_csv_reader("tests/samples/fruits_iso8859.csv")
    assert reader.fieldnames == ["id", "name"]

    line = next(reader)
    assert line == {"id": "1", "name": "Açaí"}


def test_writer():
    _, temp = tempfile.mkstemp()
    writer = csvutils.open_csv_writer(temp)
    writer.writerow(["id", "name"])
    writer.writerow(["1", "Açaí"])
    del writer

    reader = csvutils.open_csv_reader(temp)
    assert reader.fieldnames == ["id", "name"]

    line = next(reader)
    assert line == {"id": "1", "name": "Açaí"}
