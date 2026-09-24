# -*- coding: utf-8 -*-
# Owned by the ws stream (docs/ldm/SPEC.md section 11): the workspace. Every
# payload an OWL screen of the workspace renders is composed here, as the
# reading user, so record rules and the auditor's read-only access apply
# without a second check in the browser.
from . import ws_common  # noqa: F401
from . import ws_step  # noqa: F401
from . import ws_task  # noqa: F401
from . import ws_my_day  # noqa: F401
from . import ws_palette  # noqa: F401
from . import ws_company  # noqa: F401
