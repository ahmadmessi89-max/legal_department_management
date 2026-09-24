# -*- coding: utf-8 -*-
"""Post expenses to accounting (switch "Post expenses to accounting"): as a
journal entry (expense account against the cash or bank journal) or as an
outgoing payment, linked back to each expense."""
from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..models.ldm_engine import engine_guard


class LegalExpensePostWizard(models.TransientModel):
    _name = "legal.expense.post.wizard"
    _description = "Post expenses to accounting"

    expense_ids = fields.Many2many("legal.task.expense", "ldm_expense_post_wizard_rel", "wizard_id", "expense_id",
                                   string="Expenses")
    mode = fields.Selection([("entry", "Journal entry"), ("payment", "Payment")], string="Post as",
                            required=True, default="entry")
    journal_id = fields.Many2one("account.journal", string="Paid from", required=True,
                                 domain=[("type", "in", ("cash", "bank"))],
                                 default=lambda self: self.env["account.journal"].search(
                                     [("type", "in", ("cash", "bank")), ("company_id", "=", self.env.company.id)],
                                     limit=1))
    expense_account_id = fields.Many2one("account.account", string="Expense account",
                                         domain=[("account_type", "in", ("expense", "expense_direct_cost"))],
                                         help="Used for expenses whose category has no account of its own.")
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)

    def action_post(self):
        self.ensure_one()
        if not self.env["legal.task.expense"]._ldm_accounting_allowed():
            raise AccessError(_("Posting expenses needs the accounting links switch and invoicing rights."))
        expenses = self.expense_ids.filtered("ldm_can_post")
        if not expenses:
            raise UserError(_("These expenses are already posted, or were not paid by the office."))
        for expense in expenses:
            account = expense.category_id.account_id or self.expense_account_id
            if not account:
                raise UserError(_("Choose the expense account, or give the category %s an account.",
                                  expense.category_id.name or _("(none)")))
            label = " — ".join(p for p in (expense.task_id.task_number, expense.name, expense.receipt_number) if p)
            if self.mode == "entry":
                record = self._ldm_entry(expense, account, label)
                values = {"move_id": record.id}
            else:
                record = self._ldm_payment(expense, account, label)
                values = {"payment_id": record.id}
            with engine_guard():
                expense.sudo().write(values)
            expense.task_id.sudo().message_post(body=_("Expense %(name)s posted to accounting (%(ref)s).",
                                                       name=expense.name, ref=record.display_name))
        return {"type": "ir.actions.act_window_close"}

    def _ldm_entry(self, expense, account, label):
        company = expense.company_id or self.env.company
        amount = expense.currency_id._convert(expense.amount, company.currency_id, company, expense.date)
        foreign = expense.currency_id != company.currency_id
        credit_account = self.journal_id.default_account_id
        if not credit_account:
            raise UserError(_("The journal %s has no default account.", self.journal_id.name))
        common = {"name": label, "currency_id": expense.currency_id.id}
        move = self.env["account.move"].with_company(company).create({
            "move_type": "entry",
            "journal_id": self.journal_id.id,
            "date": self.date,
            "ref": label,
            "line_ids": [
                Command.create(dict(common, account_id=account.id, debit=amount, credit=0.0,
                                    amount_currency=expense.amount if foreign else amount)),
                Command.create(dict(common, account_id=credit_account.id, debit=0.0, credit=amount,
                                    amount_currency=-(expense.amount if foreign else amount))),
            ],
        })
        move.action_post()
        return move

    def _ldm_payment(self, expense, account, label):
        payment = self.env["account.payment"].with_company(expense.company_id or self.env.company).create({
            "payment_type": "outbound",
            "partner_type": "supplier",
            "amount": expense.amount,
            "currency_id": expense.currency_id.id,
            "journal_id": self.journal_id.id,
            "date": self.date,
            "memo": label,
            "destination_account_id": account.id,
        })
        payment.action_post()
        return payment
