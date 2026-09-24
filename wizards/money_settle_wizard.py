# -*- coding: utf-8 -*-
"""Settle a runner's cash advance against the receipts of what was paid."""
from odoo import Command, _, api, fields, models


class LegalAdvanceSettleWizard(models.TransientModel):
    _name = "legal.advance.settle.wizard"
    _description = "Settle a cash advance"

    advance_id = fields.Many2one("legal.advance", string="Advance", required=True)
    user_id = fields.Many2one(related="advance_id.user_id", string="Given to")
    currency_id = fields.Many2one(related="advance_id.currency_id")
    amount = fields.Monetary(related="advance_id.amount", string="Handed over", currency_field="currency_id")
    expense_ids = fields.Many2many("legal.task.expense", "ldm_settle_wizard_expense_rel", "wizard_id", "expense_id",
                                   string="Receipts")
    candidate_ids = fields.Many2many("legal.task.expense", compute="_compute_candidates")
    spent = fields.Monetary(string="Spent", currency_field="currency_id", compute="_compute_totals")
    returned_amount = fields.Monetary(string="Cash returned", currency_field="currency_id")
    balance = fields.Monetary(string="Left to account for", currency_field="currency_id", compute="_compute_totals")

    @api.model
    def _ldm_candidates(self, advance):
        return self.env["legal.task.expense"].search([
            ("paid_by", "=", "employee"), ("employee_user_id", "=", advance.user_id.id),
            ("currency_id", "=", advance.currency_id.id), ("state", "=", "confirmed"),
            "|", ("advance_id", "=", False), ("advance_id", "=", advance.id)])

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        advance = self.env["legal.advance"].browse(values.get("advance_id") or
                                                   self.env.context.get("default_advance_id")).exists()
        if advance:
            expenses = self._ldm_candidates(advance)
            if "expense_ids" in fields_list:
                values["expense_ids"] = [Command.set(expenses.ids)]
            if "returned_amount" in fields_list:
                values["returned_amount"] = max(advance.amount - sum(expenses.mapped("amount")), 0.0)
        return values

    @api.depends("advance_id")
    def _compute_candidates(self):
        for wizard in self:
            wizard.candidate_ids = self._ldm_candidates(wizard.advance_id) if wizard.advance_id else False

    @api.depends("expense_ids", "returned_amount", "amount")
    def _compute_totals(self):
        for wizard in self:
            wizard.spent = sum(wizard.expense_ids.mapped("amount"))
            wizard.balance = (wizard.amount or 0.0) - wizard.spent - (wizard.returned_amount or 0.0)

    @api.onchange("expense_ids")
    def _onchange_expenses(self):
        self.returned_amount = max((self.amount or 0.0) - sum(self.expense_ids.mapped("amount")), 0.0)

    def action_confirm(self):
        self.ensure_one()
        self.advance_id._ldm_settle(self.expense_ids, self.returned_amount or 0.0)
        return {"type": "ir.actions.act_window_close"}
