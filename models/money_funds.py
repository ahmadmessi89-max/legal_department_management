# -*- coding: utf-8 -*-
"""Client money the office holds (أمانات الموكلين), as an operational ledger.

The balance of a client in a currency can never go below zero: paying out more
than was received needs a legal manager and a reason (research 04, J3). An
execution collection is money received for the client and starts the fee
schedule's "when money is collected" instalments.
"""
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .ldm_engine import in_engine
from .money_whatsapp import money_text

MANAGER = "legal_department_management.group_legal_manager"
INCOMING = ("deposit", "execution_collection")


class LegalClientFundLine(models.Model):
    _inherit = "legal.client.fund.line"

    expense_ids = fields.One2many("legal.task.expense", "fund_line_id", string="Expense")
    balance_key = fields.Char(string="Client and currency", compute="_compute_balance_key", store=True)
    ldm_client_balance = fields.Monetary(string="Client's balance", currency_field="currency_id",
                                         compute="_compute_ldm_client_balance")

    @api.depends("legal_company_id.name", "currency_id.name")
    def _compute_balance_key(self):
        for line in self:
            line.balance_key = f"{line.legal_company_id.name or ''} · {line.currency_id.name or ''}"

    @api.depends("legal_company_id", "currency_id", "amount", "kind")
    def _compute_ldm_client_balance(self):
        balances = self._ldm_balances(self.legal_company_id)
        for line in self:
            line.ldm_client_balance = balances.get(line.legal_company_id.id, {}).get(line.currency_id, 0.0)

    @api.depends("date", "kind", "legal_company_id")
    def _compute_display_name(self):
        kinds = dict(self._fields["kind"]._description_selection(self.env))
        for line in self:
            line.display_name = " · ".join(p for p in (kinds.get(line.kind), line.legal_company_id.name,
                                                       fields.Date.to_string(line.date) if line.date else "") if p)

    # ------------------------------------------------------------------
    # Balances
    # ------------------------------------------------------------------
    @api.model
    def _ldm_balances(self, clients):
        """{client id: {currency record: balance}} over every line, whoever may read them."""
        result = {}
        if not clients:
            return result
        groups = self.sudo()._read_group([("legal_company_id", "in", clients.ids)],
                                         ["legal_company_id", "currency_id"], ["signed_amount:sum"])
        for client, currency, total in groups:
            result.setdefault(client.id, {})[currency.with_env(self.env)] = total
        return result

    @api.model
    def ldm_balance_text(self, clients):
        """{client id: "IQD 250,000 · USD 1,200"} for chips and stat buttons."""
        balances = self._ldm_balances(clients)
        return {cid: money_text(self.env, list(amounts.items())) for cid, amounts in balances.items()}

    def _ldm_is_manager(self):
        return self.env.uid == SUPERUSER_ID or self.env.user.has_group(MANAGER)

    def _ldm_check_balance(self, keys=None):
        keys = keys or {(line.legal_company_id, line.currency_id) for line in self}
        for client, currency in keys:
            balance = self._ldm_balances(client).get(client.id, {}).get(currency.with_env(self.env), 0.0)
            if currency.compare_amounts(balance, 0) >= 0:
                continue
            overridden = self.filtered(lambda l, c=client, cur=currency: l.legal_company_id == c
                                       and l.currency_id == cur and l.override_reason)
            if overridden and self._ldm_is_manager():
                continue
            raise ValidationError(_(
                "%(client)s would hold %(balance)s of client money, which is less than nothing. "
                "Record the money received first, or ask a legal manager to allow it with a reason.",
                client=client.name, balance=money_text(self.env, [(currency, balance)])))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("override_reason") for vals in vals_list) and not self._ldm_is_manager():
            raise AccessError(_("Only a legal manager can let a client's money go below zero."))
        for vals in vals_list:
            if vals.get("amount", 0) < 0:
                raise UserError(_("Enter the amount as a positive number; the movement says which way it goes."))
            if vals.get("task_id") and not vals.get("legal_company_id"):
                vals["legal_company_id"] = self.env["legal.task"].browse(vals["task_id"]).legal_company_id.id
        lines = super().create(vals_list)
        lines._ldm_check_balance()
        for line in lines.filtered(lambda l: l.kind == "execution_collection" and l.task_id):
            line.task_id._ldm_fire_fee_event("collection", amount=line.amount, currency=line.currency_id)
            line.task_id.message_post(body=_("Collected through execution: %s.",
                                             money_text(self.env, [(line.currency_id, line.amount)])))
        return lines

    def write(self, vals):
        if "override_reason" in vals and not self._ldm_is_manager():
            raise AccessError(_("Only a legal manager can let a client's money go below zero."))
        if not in_engine() and not self.env.su and self.sudo().expense_ids:
            raise UserError(_("This movement comes from an expense paid from the client's money. Change the expense."))
        if vals.get("amount", 0) < 0:
            raise UserError(_("Enter the amount as a positive number; the movement says which way it goes."))
        before = {(line.legal_company_id, line.currency_id) for line in self}
        result = super().write(vals)
        after = {(line.legal_company_id, line.currency_id) for line in self}
        self._ldm_check_balance(before | after)
        return result

    def unlink(self):
        if not in_engine() and not self.env.su and self.sudo().expense_ids:
            raise UserError(_("This movement comes from an expense paid from the client's money. Change the expense."))
        keys = {(line.legal_company_id, line.currency_id) for line in self}
        result = super().unlink()
        self.browse()._ldm_check_balance(keys)
        return result

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_ldm_receive(self):
        """List button: works on no selection, with the list's client if it has one."""
        context = self.env.context
        return self.ldm_action_move("deposit", context.get("default_legal_company_id"),
                                    context.get("default_task_id"))

    def action_ldm_pay_out(self):
        context = self.env.context
        return self.ldm_action_move("disbursement", context.get("default_legal_company_id"),
                                    context.get("default_task_id"))

    @api.model
    def ldm_action_move(self, kind, legal_company_id=False, task_id=False):
        """Open the dialog that records money received from or paid for a client."""
        titles = {
            "deposit": _("Receive client money"),
            "disbursement": _("Pay out for the client"),
            "execution_collection": _("Record a collection through execution"),
            "transfer_to_fees": _("Apply client money to our fees"),
            "refund": _("Return money to the client"),
        }
        return {
            "type": "ir.actions.act_window",
            "name": titles.get(kind, _("Client money")),
            "res_model": "legal.fund.move.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_kind": kind, "default_legal_company_id": legal_company_id,
                        "default_task_id": task_id},
        }
