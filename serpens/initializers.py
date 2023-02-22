#
# Copyright (C) 2020 Noverde Tecnologia e Pagamentos S/A
# Copyright (C) 2020 Everaldo Canuto <everaldo.canuto@gmail.com>
#
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
#
import os

from serpens import log, elastic


def setup():
    log.setup()
    elastic.setup()

    if "SENTRY_DSN" in os.environ:
        from serpens import sentry

        sentry.setup()
