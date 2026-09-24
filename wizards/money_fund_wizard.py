# -*- coding: utf-8 -*-
"""Receive money from a client, pay out for them, record an execution
collection, apply their money to fees or return it."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.money_whatsapp import money_text

MANAGER = "legal_department_management.group_legal_manager"


class LegalFundMoveWizard(models.TransientModel):
    _name = "legal.fund.move.wizard"
    _description = "Client money movement"

    kind = fields.Selection(lambda self: self.env["legal.client.fund.line"]._fields["kind"].selection,
                            string="Movement", required=True, default="deposit")
    legal_company_id = fields.Many2one("legal.company", string="Client", required=True)
    task_id = fields.Many2one("legal.task", string="Matter", domain="[('legal_company_id', '=', legal_company_id)]")
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string="Amount", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    receipt_number = fields.Char(string="Receipt number")
    receipt_file = fields.Binary(string="Receipt")
    receipt_filename = fields.Char(string="Receipt file name")
    note = fields.Char(string="Note")
    balance = fields.Monetary(string="Held now", currency_field="currency_id", compute="_compute_balance")
    balance_after = fields.Monetary(string="Held afterwards", currency_field="currency_id", compute="_compute_balance")
    goes_negative = fields.Boolean(compute="_compute_balance")
    is_manager = fields.Boolean(compute="_compute_balance")
    override_reason = fields.Text(string="Why it may go below zero")

    @api.depends("legal_company_id", "currency_id", "amount", "kind")
    def _compute_balance(self):
        Fund = self.env["legal.client.fund.line"]
        is_manager = self.env.user.has_group(MANAGER)
        for wizard in self:
            balances = Fund._ldm_balances(wizard.legal_company_id).get(wizard.legal_company_id.id, {})
            now = balances.get(wizard.currency_id, 0.0)
            sign = 1 if wizard.kind in ("deposit", "execution_collection") else -1
            wizard.balance = now
            wizard.balance_after = now + sign * (wizard.amount or 0.0)
            wizard.goes_negative = bool(wizard.currency_id) and wizard.currency_id.compare_amounts(
                wizard.balance_after, 0) < 0
            wizard.is_manager = is_manager

    @api.onchange("task_id")
    def _onchange_task(self):
        if self.task_id and not self.legal_company_id:
            self.legal_company_id = self.task_id.legal_company_id

    def action_confirm(self):
        self.ensure_one()
        if self.currency_id.compare_amounts(self.amount, 0) <= 0:
            raise UserError(_("Enter the amount."))
        if self.goes_negative and not self.is_manager:
            raise UserError(_("%(client)s holds only %(held)s. A legal manager must approve paying out more.",
                              client=self.legal_company_id.name,
                              held=money_text(self.env, [(self.currency_id, self.balance)]) or "0"))
        if self.goes_negative and not (self.override_reason or "").strip():
            raise UserError(_("Say why the client's money may go below zero."))
        attachment = self.env["ir.attachment"]
        if self.receipt_file:
            attachment = self.env["ir.attachment"].create({
                "name": self.receipt_filename or _("Receipt"), "datas": self.receipt_file,
                "res_model": "legal.client.fund.line", "res_id": 0,
            })
        line = self.env["legal.client.fund.line"].create({
            "kind": self.kind,
            "legal_company_id": self.legal_company_id.id,
            "task_id": self.task_id.id or False,
            "company_id": (self.task_id.company_id or self.legal_company_id.company_id or self.env.company).id,
            "date": self.date,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "receipt_number": self.receipt_number or False,
            "attachment_id": attachment.id or False,
            "note": self.note or False,
            "override_reason": (self.override_reason or "").strip() if self.goes_negative else False,
        })
        if attachment:
            attachment.sudo().res_id = line.id
        kinds = dict(self._fields["kind"]._description_selection(self.env))
        body = _("%(kind)s: %(amount)s. Client money held now: %(held)s.", kind=kinds[self.kind],
                 amount=money_text(self.env, [(self.currency_id, self.amount)]),
                 held=self.env["legal.client.fund.line"].ldm_balance_text(self.legal_company_id).get(
                     self.legal_company_id.id) or "0")
        self.legal_company_id.sudo().message_post(body=body)
        if self.task_id and self.kind != "execution_collection":
            self.task_id.sudo().message_post(body=body)
        return {"type": "ir.actions.act_window_close"}
