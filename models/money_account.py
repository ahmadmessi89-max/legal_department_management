# -*- coding: utf-8 -*-
"""The invoice side: which matters an invoice was made for, and freeing the
instalments, time and expenses of a cancelled or deleted invoice so they go
back to To invoice."""
from odoo import fields, models

from .ldm_engine import engine_guard


class AccountMove(models.Model):
    _inherit = "account.move"

    ldm_task_ids = fields.Many2many("legal.task", "ldm_account_move_task_rel", "move_id", "task_id",
                                    string="Legal matters", copy=False, readonly=True)

    def button_cancel(self):
        result = super().button_cancel()
        self.line_ids._ldm_release_sources()
        return result

    def unlink(self):
        self.line_ids._ldm_release_sources()
        return super().unlink()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def unlink(self):
        self._ldm_release_sources()
        return super().unlink()

    def _ldm_release_sources(self):
        if not self:
            return
        env = self.env(su=True)
        with engine_guard():
            env["legal.engagement.line"].search([("invoice_line_id", "in", self.ids)]).write(
                {"invoice_line_id": False, "state": "due"})
            env["legal.time.entry"].search([("invoice_line_id", "in", self.ids)]).write(
                {"invoice_line_id": False, "state": "approved"})
            env["legal.task.expense"].search([("invoice_line_id", "in", self.ids)]).write(
                {"invoice_line_id": False})
