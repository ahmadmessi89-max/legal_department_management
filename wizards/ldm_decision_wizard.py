# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LegalTaskDecisionWizard(models.TransientModel):
    """One small dialog for the three decisions that need words: closing a
    matter (with its outcome), cancelling it, and rejecting an approval."""

    _name = "legal.task.decision.wizard"
    _description = "Close, cancel or reject a matter"

    task_ids = fields.Many2many("legal.task", string="Matters", required=True)
    mode = fields.Selection([("close", "Close"), ("cancel", "Cancel"), ("reject", "Reject")],
                            required=True, default="close")
    outcome = fields.Selection(lambda self: self.env["legal.task"]._fields["outcome"].selection,
                               string="Outcome", default="completed")
    note = fields.Text(string="Note")
    open_item_count = fields.Integer(compute="_compute_open_items")
    close_open_items = fields.Boolean(string="Also close its open steps and deadlines", default=True)

    @api.depends("task_ids")
    def _compute_open_items(self):
        for wizard in self:
            tasks = wizard.task_ids
            wizard.open_item_count = (len(tasks.step_ids.filtered(lambda s: s.state == "todo"))
                                      + len(tasks.deadline_ids.filtered(lambda d: d.state == "open"))
                                      + len(tasks.hearing_ids.filtered(lambda h: h.state == "planned")))

    def action_confirm(self):
        self.ensure_one()
        tasks = self.task_ids
        if self.mode == "reject":
            if not (self.note or "").strip():
                raise UserError(_("Say why the matter is rejected."))
            tasks._ldm_reject(self.note)
        elif self.mode == "cancel":
            if not (self.note or "").strip():
                raise UserError(_("Say why the matter is cancelled."))
            tasks._ldm_cancel(self.note)
        else:
            tasks._ldm_close(self.outcome or "completed", self.note)
        if self.mode in ("close", "cancel") and self.close_open_items:
            tasks.step_ids.filtered(lambda s: s.state == "todo").write({"state": "skipped"})
            tasks.deadline_ids.filtered(lambda d: d.state == "open").write({"state": "cancelled"})
            tasks.hearing_ids.filtered(lambda h: h.state == "planned").write({"state": "cancelled"})
        return {"type": "ir.actions.act_window_close"}
