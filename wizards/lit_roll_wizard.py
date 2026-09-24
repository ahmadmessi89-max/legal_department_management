# -*- coding: utf-8 -*-
"""Print the hearing roll (رول الجلسات) for a range of days."""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LegalHearingRollWizard(models.TransientModel):
    _name = "legal.hearing.roll.wizard"
    _description = "Print the hearing roll"

    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True,
                          default=lambda self: fields.Date.context_today(self) + timedelta(days=6))
    user_ids = fields.Many2many("res.users", string="Lawyers",
                                help="Leave empty for everyone's sessions.")
    department_ids = fields.Many2many("legal.department", string="Courts", domain="[('body_kind', '=', 'court')]",
                                      help="Leave empty for every court.")
    include_held = fields.Boolean(string="Include sessions already held")

    @api.onchange("date_from")
    def _onchange_date_from(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            self.date_to = self.date_from

    def action_print(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(_("The roll must end on or after the day it starts."))
        data = {
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "user_ids": self.user_ids.ids,
            "department_ids": self.department_ids.ids,
            "include_held": self.include_held,
        }
        return self.env.ref("legal_department_management.action_report_ldm_hearing_roll").report_action(
            self.env["legal.hearing"], data=data)
