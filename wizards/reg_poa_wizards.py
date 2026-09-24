# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LegalPoaRevokeWizard(models.TransientModel):
    """Revoke a power of attorney (عزل الوكيل): the date, the reason, and the
    matters that will be told."""

    _name = "legal.poa.revoke.wizard"
    _description = "Revoke a power of attorney"

    poa_id = fields.Many2one("legal.poa", string="Power of attorney", required=True, ondelete="cascade")
    date = fields.Date(string="Revoked on", required=True, default=fields.Date.context_today)
    reason = fields.Text(string="Reason", required=True,
                         help="For example: the client ended the mandate by notarial notice number and date.")
    open_task_ids = fields.Many2many("legal.task", string="Open matters relying on it",
                                     compute="_compute_open_task_ids")

    @api.depends("poa_id")
    def _compute_open_task_ids(self):
        for wizard in self:
            wizard.open_task_ids = wizard.poa_id.task_ids.filtered(
                lambda t: t.state in ("draft", "in_progress", "pending_docs"))

    def action_confirm(self):
        self.ensure_one()
        self.poa_id._ldm_revoke(self.date, self.reason)
        return {"type": "ir.actions.act_window_close"}
