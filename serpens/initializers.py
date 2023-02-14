#
# Copyright (C) 2020 Noverde Tecnologia e Pagamentos S/A
# Copyright (C) 2020 Everaldo Canuto <everaldo.canuto@gmail.com>
#
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
#
import os

import elastic

from serpens import log


def setup():
    elastic.setup()
    log.setup()
    if "SENTRY_DSN" in os.environ:
        from serpens import sentry

        sentry.setup()
