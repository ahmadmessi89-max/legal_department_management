# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


def _previous_month_start(model):
    return fields.Date.context_today(model).replace(day=1) - relativedelta(months=1)


def _previous_month_end(model):
    return fields.Date.context_today(model).replace(day=1) - relativedelta(days=1)


class LegalMonthlyReportWizard(models.TransientModel):
    """موقف الدعاوى والمعاملات for a period: by default the month just ended."""

    _name = "legal.monthly.report.wizard"
    _description = "Monthly status report"

    date_from = fields.Date(string="From", required=True, default=_previous_month_start)
    date_to = fields.Date(string="To", required=True, default=_previous_month_end)

    def action_print(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(_("The end date is before the start date."))
        data = {"date_from": fields.Date.to_string(self.date_from), "date_to": fields.Date.to_string(self.date_to)}
        return self.env.ref("legal_department_management.action_report_ldm_monthly_status").report_action(
            [], data=data, config=False)
