# -*- coding: utf-8 -*-
from odoo import fields, models


class LegalFeeWaiveWizard(models.TransientModel):
    _name = "legal.fee.waive.wizard"
    _description = "Waive instalments"

    line_ids = fields.Many2many("legal.engagement.line", "ldm_waive_wizard_line_rel", "wizard_id", "line_id",
                                string="Instalments")
    reason = fields.Text(string="Why are they waived?")

    def action_confirm(self):
        self.ensure_one()
        self.line_ids._ldm_waive(self.reason)
        return {"type": "ir.actions.act_window_close"}
