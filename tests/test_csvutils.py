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
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        writer = csvutils.open_csv_writer(temp.filename)
        writer.writerow(["hello", "name"])
        writer.writerow(["1", "Açaí"])

        reader = csvutils.open_csv_reader(temp.filename)
        assert reader.fieldnames == ["id", "name"]

        line = next(reader)
        assert line == {"id": "1", "name": "Açaí"}
