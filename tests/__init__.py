# -*- coding: utf-8 -*-
# Foundation
from . import test_foundation_security
from . import test_foundation_workflow
from . import test_foundation_clocks
from . import test_foundation_modes
# Streams (each imports its own extra modules from its file)
from . import test_gov
from . import test_lit
from . import test_ws
from . import test_money
from . import test_reg
# Design pass
from . import test_design
