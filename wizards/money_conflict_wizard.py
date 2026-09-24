# -*- coding: utf-8 -*-
"""A legal manager's decision on a possible conflict of interest."""
from odoo import _, fields, models


class LegalConflictDecisionWizard(models.TransientModel):
    _name = "legal.conflict.decision.wizard"
    _description = "Decide on a conflict check"

    check_id = fields.Many2one("legal.conflict.check", string="Conflict check", required=True)
    task_id = fields.Many2one(related="check_id.task_id", string="Matter")
    query = fields.Char(related="check_id.query")
    hit_html = fields.Html(related="check_id.hit_html")
    policy = fields.Selection(related="check_id.policy")
    decision = fields.Selection(
        [("clear", "Not a conflict: someone else, or no opposing interest"),
         ("override", "Accept the matter despite the match"),
         ("declined", "Decline the matter")],
        string="Decision")
    reason = fields.Text(string="Reason")

    def action_confirm(self):
        self.ensure_one()
        self.check_id.ldm_decide(self.decision, self.reason)
        return {"type": "ir.actions.act_window_close"}
