# -*- coding: utf-8 -*-
# Foundation: every model and field of docs/ldm/SPEC.md section 4.
from . import ldm_text
from . import ldm_engine
from . import ldm_cron
from . import ldm_reminders
from . import res_company
from . import res_config_settings
from . import res_users
from . import legal_ministry
from . import legal_department
from . import legal_task_template
from . import base_work
from . import base_litigation
from . import base_registers
from . import base_money
from . import legal_company
from . import legal_task
# Kept from 19.0.6.3.0 (rewritten by their streams)
from . import legal_task_wizard
from . import legal_company_report_wizard
from . import legal_general_report_wizard
# Streams (behaviour on top of the foundation's declarations)
from . import gov_government
from . import lit_litigation
from . import ws_workspace
from . import money_money
from . import reg_registers
# Design pass: the company file's service overview and the managers' analytics board
from . import ds_services
from . import ds_analytics
