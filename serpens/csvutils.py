#
# Copyright (C) 2020 Noverde Tecnologia e Pagamentos S/A
# Copyright (C) 2020 Everaldo Canuto <everaldo.canuto@gmail.com>
#
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
#

import csv

try:
    from smart_open import open
except ImportError:
    pass


def open_csv_reader(filename):
    try:
        # From Python Unicode documentation:
        # In some areas, it is also convention to use a "BOM" at the start of
        # UTF-8 encoded files; the name is misleading since UTF-8 is not
        # byte-order dependent. The mark simply announces that the file is
        # encoded in UTF-8. Use the 'utf-8-sig' codec to automatically skip the
        # mark if present for reading such files.
        stream = open(filename, "r", encoding="UTF-8-SIG")
        buffer = stream.read(2048)
    except UnicodeDecodeError:
        stream = open(filename, "r", encoding="ISO-8859-1")
        buffer = stream.read(2048)

    dialect = csv.Sniffer().sniff(buffer)
    stream.seek(0)

    return csv.DictReader(stream, dialect=dialect)


def open_csv_writer(filename, dialect="excel"):
    stream = open(filename, "w", encoding="UTF-8")

    return csv.writer(stream, dialect=dialect)
