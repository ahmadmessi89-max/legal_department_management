# -*- coding: utf-8 -*-
"""Money on the client dossier: client money held, what is waiting to be
invoiced, what the client owes, and the statement of account (كشف حساب)."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .money_whatsapp import money_text

ACCOUNT_READERS = "account.group_account_invoice,account.group_account_readonly"


class LegalCompany(models.Model):
    _inherit = "legal.company"

    ldm_fund_balance_text = fields.Char(string="Client money held", compute="_compute_ldm_money")
    unbilled_amount = fields.Monetary(string="To invoice", currency_field="currency_id", compute="_compute_ldm_money",
                                      help="Due instalments, approved time and recharged expenses not yet invoiced, "
                                      "in the company's currency.")
    balance_due = fields.Monetary(string="Balance due", currency_field="currency_id", compute="_compute_ldm_balance",
                                  groups=ACCOUNT_READERS,
                                  help="What the client still owes on posted invoices, in the company's currency.")
    engagement_count = fields.Integer(string="Number of fee agreements", compute="_compute_ldm_money")
    ldm_can_message = fields.Boolean(compute="_compute_ldm_can_message")

    @api.depends_context("uid")
    def _compute_ldm_can_message(self):
        allowed = self.env["legal.task"]._ldm_user_can_message()
        for client in self:
            client.ldm_can_message = allowed

    def _compute_ldm_money(self):
        funds = self.env["legal.client.fund.line"].ldm_balance_text(self)
        unbilled = {}
        for client, currency, total in self.env["legal.billable"].sudo()._read_group(
                [("legal_company_id", "in", self.ids)], ["legal_company_id", "currency_id"], ["amount:sum"]):
            unbilled.setdefault(client.id, []).append((currency, total))
        engagements = {client.id: count for client, count in self.env["legal.engagement"]._read_group(
            [("legal_company_id", "in", self.ids)], ["legal_company_id"], ["__count"])}
        today = fields.Date.context_today(self)
        for client in self:
            company = client.company_id or self.env.company
            target = client.currency_id or company.currency_id
            client.ldm_fund_balance_text = funds.get(client.id) or False
            client.unbilled_amount = sum(currency._convert(amount, target, company, today)
                                         for currency, amount in unbilled.get(client.id, []))
            client.engagement_count = engagements.get(client.id, 0)

    def _compute_ldm_balance(self):
        for client in self:
            partner = client.partner_id.commercial_partner_id
            if not partner:
                client.balance_due = 0.0
                continue
            moves = self.env["account.move"].sudo().search([
                ("commercial_partner_id", "=", partner.id), ("state", "=", "posted"),
                ("move_type", "in", ("out_invoice", "out_refund"))])
            client.balance_due = sum(moves.mapped("amount_residual_signed"))

    # ------------------------------------------------------------------
    # Statement of account
    # ------------------------------------------------------------------
    def _ldm_statement(self, date_from, date_to):
        """One section per currency: opening balance, invoices and payments in
        the period (from the receivable lines' amount in that currency),
        closing balance, then what is not invoiced yet, the schedule still to
        come and the client money held."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        company = self.company_id or self.env.company
        Line = self.env["account.move.line"].sudo()
        base = [("partner_id", "child_of", partner.id), ("parent_state", "=", "posted"),
                ("account_id.account_type", "=", "asset_receivable"), ("company_id", "=", company.id)] \
            if partner else [("id", "=", 0)]
        opening = {currency: total for currency, total in Line._read_group(
            base + [("date", "<", date_from)], ["currency_id"], ["amount_currency:sum"])}
        period = Line.search(base + [("date", ">=", date_from), ("date", "<=", date_to)], order="date, move_name, id")
        unbilled = self.env["legal.billable"].sudo().search([("legal_company_id", "=", self.id)], order="date, id")
        schedule = self.env["legal.engagement.line"].sudo().search([
            ("legal_company_id", "=", self.id), ("state", "=", "planned"),
            ("engagement_id.state", "=", "active")], order="date, sequence, id")
        funds = self.env["legal.client.fund.line"]._ldm_balances(self).get(self.id, {})
        currencies = set(opening) | set(period.currency_id) | set(unbilled.currency_id) \
            | set(schedule.currency_id) | {c for c, amount in funds.items() if not c.is_zero(amount)}
        sections = []
        for currency in sorted(currencies, key=lambda c: (c != company.currency_id, c.name)):
            balance = opening.get(currency, 0.0)
            rows = []
            invoiced = paid = 0.0
            for line in period.filtered(lambda l, c=currency: l.currency_id == c):
                amount = line.amount_currency
                balance += amount
                if amount >= 0:
                    invoiced += amount
                else:
                    paid -= amount
                move = line.move_id
                rows.append({
                    "date": line.date,
                    "number": move.name,
                    "label": self._ldm_statement_label(move, line),
                    "debit": amount if amount > 0 else 0.0,
                    "credit": -amount if amount < 0 else 0.0,
                    "balance": balance,
                })
            waiting = unbilled.filtered(lambda r, c=currency: r.currency_id == c)
            coming = schedule.filtered(lambda r, c=currency: r.currency_id == c)
            sections.append({
                "currency": currency,
                "opening": opening.get(currency, 0.0),
                "rows": rows,
                "invoiced": invoiced,
                "paid": paid,
                "closing": balance,
                "unbilled": waiting,
                "unbilled_total": sum(waiting.mapped("amount")),
                "schedule": coming,
                "schedule_total": sum(coming.mapped("amount")),
                "funds": funds.get(currency, 0.0),
            })
        return sections

    @api.model
    def _ldm_statement_label(self, move, line):
        if move.move_type == "out_invoice":
            return _("Invoice") + (f" — {move.ref}" if move.ref else "")
        if move.move_type == "out_refund":
            return _("Credit note")
        if move.origin_payment_id or line.payment_id:
            return _("Payment received") + (f" — {move.ref}" if move.ref else "")
        return line.name or move.ref or _("Entry")

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_ldm_client_money(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_client_fund")
        action.update({"domain": [("legal_company_id", "=", self.id)],
                       "context": {"default_legal_company_id": self.id}})
        return action

    def action_ldm_receive_client_money(self):
        self.ensure_one()
        return self.env["legal.client.fund.line"].ldm_action_move("deposit", self.id)

    def action_ldm_to_invoice(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_to_invoice")
        action.update({"domain": [("legal_company_id", "=", self.id)], "context": {}})
        return action

    def action_ldm_engagements(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_engagement")
        action.update({"domain": [("legal_company_id", "=", self.id)],
                       "context": {"default_legal_company_id": self.id}})
        return action

    def action_ldm_open_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("account.action_move_out_invoice_type")
        action.update({"domain": [("move_type", "in", ("out_invoice", "out_refund")),
                                  ("commercial_partner_id", "=", self.partner_id.commercial_partner_id.id)],
                       "context": {"default_move_type": "out_invoice", "default_partner_id": self.partner_id.id}})
        return action

    def action_ldm_statement(self):
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_invoice") \
                and not self.env.user.has_group("account.group_account_readonly"):
            raise AccessError(_("The statement of account is prepared by billing."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Statement of account"),
            "res_model": "legal.statement.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_legal_company_id": self.id},
        }

    def action_ldm_receive_payment(self):
        """A payment or an advance on fees: Odoo's own customer payment, which
        stays as an outstanding credit until an invoice uses it."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Receive a payment"),
            "res_model": "account.payment",
            "view_mode": "form",
            "target": "new",
            "context": {"default_payment_type": "inbound", "default_partner_type": "customer",
                        "default_partner_id": self.partner_id.id},
        }

    def action_ldm_invoice(self):
        self.ensure_one()
        return self.env["legal.invoice.wizard"].ldm_open(clients=self)

    def action_ldm_message(self):
        self.ensure_one()
        owes = self.env.user.has_group("account.group_account_invoice") and self.sudo().balance_due > 0
        return self.env["legal.client.message.wizard"].ldm_open("statement_ready" if owes else False, client=self)

    def ldm_money_summary(self):
        """For the workspace dossier panel: the money chips as plain text."""
        self.ensure_one()
        return {
            "funds": self.ldm_fund_balance_text or "",
            "unbilled": money_text(self.env, [(self.currency_id or self.env.company.currency_id, self.unbilled_amount)]),
            "engagements": self.engagement_count,
        }
