# -*- coding: utf-8 -*-
"""Cash advances to runners (سلفة): handed over by the office's cashier,
spent on government fees at the counters, settled against the receipts."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .money_whatsapp import money_text

MANAGER = "legal_department_management.group_legal_manager"
BILLING = "legal_department_management.group_ldm_billing_user"


class LegalAdvance(models.Model):
    _inherit = "legal.advance"

    expense_count = fields.Integer(string="Receipts", compute="_compute_expense_count")
    ldm_can_handle = fields.Boolean(compute="_compute_ldm_can_handle")

    def _compute_expense_count(self):
        for advance in self:
            advance.expense_count = len(advance.expense_ids)

    @api.depends_context("uid")
    def _compute_ldm_can_handle(self):
        allowed = self._ldm_is_cashier()
        for advance in self:
            advance.ldm_can_handle = allowed

    @api.model
    def _ldm_is_cashier(self):
        user = self.env.user
        return self.env.su or user.has_group(MANAGER) or user.has_group(BILLING)

    def _ldm_check_cashier(self):
        if not self._ldm_is_cashier():
            raise AccessError(_("Only a legal manager or the billing team can hand over or settle a cash advance."))

    # ------------------------------------------------------------------
    # CRUD guards
    # ------------------------------------------------------------------
    def write(self, vals):
        if not self.env.su and not self._ldm_is_cashier():
            if "state" in vals:
                raise AccessError(_("Only a legal manager or the billing team can hand over or settle a cash advance."))
            if {"amount", "currency_id", "user_id", "returned_amount"} & set(vals) and \
                    any(a.state != "draft" for a in self):
                raise UserError(_("An advance that has been handed over can no longer change."))
        return super().write(vals)

    def unlink(self):
        if any(a.state != "draft" for a in self) and not self.env.su:
            raise UserError(_("Only an advance that was never handed over can be deleted."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_ldm_hand_over(self):
        self._ldm_check_cashier()
        for advance in self:
            if advance.state != "draft":
                raise UserError(_("%s has already been handed over.", advance.name))
            if advance.currency_id.compare_amounts(advance.amount, 0) <= 0:
                raise UserError(_("Enter the amount handed over."))
        self.write({"state": "paid"})
        for advance in self:
            advance.message_post(body=_("%(amount)s handed over to %(user)s.",
                                        amount=money_text(self.env, [(advance.currency_id, advance.amount)]),
                                        user=advance.user_id.name))
        return True

    def action_ldm_settle(self):
        self.ensure_one()
        self._ldm_check_cashier()
        if self.state != "paid":
            raise UserError(_("Only an advance that has been handed over can be settled."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Settle %s", self.name),
            "res_model": "legal.advance.settle.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_advance_id": self.id},
        }

    def _ldm_settle(self, expenses, returned_amount):
        """Link ``expenses`` to the advance, record the cash returned and close it.
        The money must balance: whatever is left must come back as cash; if the
        runner spent more than they were given, the office owes the difference."""
        self.ensure_one()
        self._ldm_check_cashier()
        if self.state != "paid":
            raise UserError(_("Only an advance that has been handed over can be settled."))
        currency = self.currency_id
        if currency.compare_amounts(returned_amount, 0) < 0:
            raise UserError(_("The cash returned cannot be negative."))
        wrong = expenses.filtered(lambda e: e.paid_by != "employee" or e.employee_user_id != self.user_id
                                  or e.currency_id != currency or (e.advance_id and e.advance_id != self))
        if wrong:
            raise UserError(_("Only expenses %(user)s paid in %(currency)s can settle this advance.",
                              user=self.user_id.name, currency=currency.name))
        expenses.sudo().write({"advance_id": self.id})
        spent = sum(self.expense_ids.mapped("amount"))
        balance = self.amount - spent - returned_amount
        if currency.compare_amounts(balance, 0) > 0:
            raise UserError(_("%(amount)s is still not accounted for. Add the missing receipts or the cash returned.",
                              amount=money_text(self.env, [(currency, balance)])))
        super(LegalAdvance, self.sudo()).write({"returned_amount": returned_amount, "state": "settled"})
        body = _("Settled: %(spent)s spent on %(count)s receipts, %(returned)s returned.",
                 spent=money_text(self.env, [(currency, spent)]) or "0", count=len(self.expense_ids),
                 returned=money_text(self.env, [(currency, returned_amount)]) or "0")
        if currency.compare_amounts(balance, 0) < 0:
            body += " " + _("The office owes %(amount)s to %(user)s.",
                            amount=money_text(self.env, [(currency, -balance)]), user=self.user_id.name)
        self.message_post(body=body)
        return True

    def action_view_expenses(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_expense")
        action.update({"domain": [("advance_id", "=", self.id)], "context": {"create": False}})
        return action

    # ------------------------------------------------------------------
    # My Day
    # ------------------------------------------------------------------
    @api.model
    def ldm_my_balance(self):
        """Cash the current user still has to account for, per currency.

        Returns ``{"count": n, "lines": [{"currency_id", "currency", "balance",
        "amount", "spent", "text"}], "text": "IQD 150,000", "action": {...}}``.
        ``count`` is 0 when nothing is outstanding (My Day then draws nothing)."""
        advances = self.search([("user_id", "=", self.env.uid), ("state", "=", "paid")])
        per_currency = {}
        for advance in advances:
            row = per_currency.setdefault(advance.currency_id, {"balance": 0.0, "amount": 0.0, "spent": 0.0})
            row["balance"] += advance.balance
            row["amount"] += advance.amount
            row["spent"] += advance.spent_amount
        lines = [{
            "currency_id": currency.id,
            "currency": currency.name,
            "balance": row["balance"],
            "amount": row["amount"],
            "spent": row["spent"],
            "text": money_text(self.env, [(currency, row["balance"])]) or "0",
        } for currency, row in per_currency.items()]
        return {
            "count": len(advances),
            "lines": lines,
            "text": money_text(self.env, [(c, r["balance"]) for c, r in per_currency.items()]),
            "action": {
                "type": "ir.actions.act_window",
                "name": _("My cash advances"),
                "res_model": "legal.advance",
                "views": [[False, "list"], [False, "form"]],
                "domain": [("user_id", "=", self.env.uid), ("state", "=", "paid")],
            },
        }
