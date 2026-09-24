# -*- coding: utf-8 -*-
"""The close dialog in billing mode: before a matter is closed, show what is
still open on the money side and what the office still holds for the client,
and decide what happens to the fee instalments that have not fallen due.

Advocacy Law Art. 58: a settlement or another early ending still entitles the
lawyer to the fee, so the remaining instalments are proposed as due; Arts.
60-61: when the client ends the mandate or we withdraw, the fee is reviewed.
Art. 53: the client's money and original documents are returned."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.money_whatsapp import money_text

EARLY_END = ("settled", "withdrawn", "client_revoked")
ACCOUNT_READERS = "account.group_account_invoice,account.group_account_readonly"


class LegalTaskDecisionWizard(models.TransientModel):
    _inherit = "legal.task.decision.wizard"

    ldm_billing = fields.Boolean(compute="_compute_ldm_money")
    ldm_unbilled_text = fields.Char(string="Not invoiced yet", compute="_compute_ldm_money")
    ldm_remaining_line_ids = fields.Many2many("legal.engagement.line", string="Remaining instalments",
                                              compute="_compute_ldm_money")
    ldm_remaining_text = fields.Char(string="Instalments still to come", compute="_compute_ldm_money")
    ldm_balance_text = fields.Char(string="The client owes", compute="_compute_ldm_balance", groups=ACCOUNT_READERS)
    ldm_funds_text = fields.Char(string="Client money we hold", compute="_compute_ldm_money")
    ldm_originals_count = fields.Integer(string="Originals we hold", compute="_compute_ldm_money")
    ldm_poa_id = fields.Many2one("legal.poa", string="Power of attorney", compute="_compute_ldm_money")
    ldm_remaining_action = fields.Selection(
        [("due", "Make them due now"), ("keep", "Keep them as planned"), ("waive", "Waive them")],
        string="What happens to them", compute="_compute_ldm_remaining_action", store=True, readonly=False)
    ldm_waive_reason = fields.Text(string="Why are they waived?")

    def _ldm_remaining_lines(self):
        tasks = self.task_ids._origin or self.task_ids
        lines = self.env["legal.engagement.line"]
        for engagement in tasks.engagement_id.filtered(lambda e: e.state == "active"):
            others_open = engagement.task_ids.filtered(
                lambda t: t not in tasks and t.state in ("draft", "in_progress", "pending_docs"))
            lines |= engagement.line_ids.filtered(
                lambda l: l.state == "planned" and ((l.task_id and l.task_id in tasks)
                                                    or (not l.task_id and not others_open)))
        return lines

    @api.depends("task_ids", "mode")
    def _compute_ldm_money(self):
        billing = self.env["legal.task"]._ldm_feature("group_ldm_billing")
        for wizard in self:
            tasks = wizard.task_ids._origin or wizard.task_ids
            wizard.ldm_billing = bool(billing and wizard.mode == "close")
            unbilled = self.env["legal.billable"].sudo()._read_group(
                [("task_id", "in", tasks.ids)], ["currency_id"], ["amount:sum"])
            wizard.ldm_unbilled_text = money_text(self.env, unbilled) or False
            remaining = wizard._ldm_remaining_lines()
            wizard.ldm_remaining_line_ids = remaining
            wizard.ldm_remaining_text = money_text(
                self.env, [(c, sum(remaining.filtered(lambda l, c=c: l.currency_id == c).mapped("amount")))
                           for c in remaining.currency_id]) or False
            funds = self.env["legal.client.fund.line"].ldm_balance_text(tasks.legal_company_id)
            wizard.ldm_funds_text = " · ".join(v for v in funds.values() if v) or False
            originals = tasks.document_ids.filtered("original_held")
            vault = self.env["legal.company.document"].sudo().search_count(
                [("legal_company_id", "in", tasks.legal_company_id.ids), ("original_held", "=", True)])
            wizard.ldm_originals_count = len(originals) + vault
            wizard.ldm_poa_id = tasks.poa_id[:1]

    def _compute_ldm_balance(self):
        for wizard in self:
            clients = wizard.task_ids.legal_company_id
            wizard.ldm_balance_text = money_text(
                self.env, [(c.currency_id or self.env.company.currency_id, c.sudo().balance_due) for c in clients]) \
                or False

    @api.depends("outcome", "mode")
    def _compute_ldm_remaining_action(self):
        for wizard in self:
            wizard.ldm_remaining_action = "due" if wizard.outcome in EARLY_END else "keep"

    def action_confirm(self):
        self.ensure_one()
        lines = self.env["legal.engagement.line"]
        if self.mode == "close" and self.ldm_billing:
            lines = self._ldm_remaining_lines()
            if lines and self.ldm_remaining_action == "waive" and not (self.ldm_waive_reason or "").strip():
                raise UserError(_("Say why the remaining instalments are waived."))
        result = super().action_confirm()
        if lines:
            lines = lines.filtered(lambda l: l.state == "planned")
            if self.ldm_remaining_action == "due":
                lines.sudo()._ldm_make_due()
            elif self.ldm_remaining_action == "waive":
                lines.sudo()._ldm_waive(self.ldm_waive_reason)
        return result
