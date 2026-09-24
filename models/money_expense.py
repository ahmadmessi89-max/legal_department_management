# -*- coding: utf-8 -*-
"""Expenses on a matter, in both modes.

What an expense is recharged to the client by default follows the mode (a
department recharges nothing) and the category; who paid decides what else
happens: paid from the client's money we hold writes one client-money
disbursement, paid by an employee comes out of their cash advance.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .ldm_engine import engine_guard

MANAGER = "legal_department_management.group_legal_manager"
LOCKED_WHEN_BILLED = {"amount", "currency_id", "recoverable", "task_id", "paid_by"}
FUND_KEYS = {"paid_by", "amount", "currency_id", "date", "task_id", "receipt_number", "name", "state"}


def ldm_mode(env):
    return env["ir.config_parameter"].sudo().get_param("legal_department_management.mode") or "department"


class LegalTaskExpense(models.Model):
    _inherit = "legal.task.expense"

    paid_by = fields.Selection(
        [("office", "The office"), ("employee", "An employee's advance"),
         ("client_funds", "Client money we hold"), ("client", "The client directly")])
    recoverable = fields.Boolean(compute="_compute_recoverable", store=True, readonly=False, precompute=True,
                                 help="Recharged to the client on the next invoice (Advocacy Law Art. 55).")
    ldm_can_post = fields.Boolean(string="Can be posted", compute="_compute_ldm_can_post")
    ldm_posted = fields.Boolean(string="Posted to accounting", compute="_compute_ldm_posted", compute_sudo=True)

    @api.depends("category_id", "paid_by")
    def _compute_recoverable(self):
        department = ldm_mode(self.env) == "department"
        for expense in self:
            if expense.paid_by in ("client", "client_funds") or department:
                expense.recoverable = False
            elif expense.category_id:
                expense.recoverable = expense.category_id.recoverable_default
            else:
                expense.recoverable = True

    @api.depends_context("uid")
    @api.depends("state", "paid_by", "move_id", "payment_id")
    def _compute_ldm_can_post(self):
        allowed = self._ldm_accounting_allowed()
        for expense in self:
            posted = expense.sudo().move_id or expense.sudo().payment_id
            expense.ldm_can_post = bool(allowed and expense.state == "confirmed" and not posted
                                        and expense.paid_by in ("office", "employee"))

    @api.depends("move_id", "payment_id")
    def _compute_ldm_posted(self):
        for expense in self:
            expense.ldm_posted = bool(expense.move_id or expense.payment_id)

    @api.model
    def _ldm_accounting_allowed(self):
        return bool(self.env["legal.task"]._ldm_feature("group_ldm_accounting_links")
                    and self.env.user.has_group("account.group_account_invoice"))

    @api.onchange("paid_by")
    def _onchange_paid_by(self):
        if self.paid_by == "employee" and not self.employee_user_id:
            self.employee_user_id = self.env.user
        if self.paid_by != "employee":
            self.advance_id = False

    @api.onchange("employee_user_id", "currency_id")
    def _onchange_employee_advance(self):
        if self.paid_by == "employee" and self.employee_user_id and not self.advance_id:
            self.advance_id = self._ldm_open_advance(self.employee_user_id, self.currency_id, self.company_id)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("paid_by") == "employee" and not vals.get("employee_user_id"):
                vals["employee_user_id"] = self.env.user.id
        expenses = super().create(vals_list)
        expenses._ldm_link_advance()
        expenses._ldm_sync_fund_line()
        return expenses

    def write(self, vals):
        if not self.env.su:
            if LOCKED_WHEN_BILLED & set(vals) and any(e.billed for e in self.sudo()):
                raise UserError(_("This expense is already on an invoice. Cancel the invoice first to change it."))
            settled = self.sudo().filtered(lambda e: e.advance_id.state == "settled")
            if settled and {"amount", "currency_id", "advance_id", "paid_by", "employee_user_id"} & set(vals):
                raise UserError(_("This expense was settled against a cash advance and can no longer change."))
        result = super().write(vals)
        if {"paid_by", "employee_user_id", "currency_id"} & set(vals):
            self._ldm_link_advance()
        if FUND_KEYS & set(vals):
            self._ldm_sync_fund_line()
        return result

    def unlink(self):
        if not self.env.su and not self.env.user.has_group(MANAGER):
            raise UserError(_("Only a legal manager can delete an expense. Correct the amount instead."))
        if any(e.billed for e in self.sudo()):
            raise UserError(_("An invoiced expense cannot be deleted. Cancel the invoice first."))
        fund_lines = self.sudo().fund_line_id
        result = super().unlink()
        if fund_lines:
            with engine_guard():
                fund_lines.sudo().unlink()
        return result

    @api.constrains("advance_id", "employee_user_id", "currency_id", "paid_by")
    def _check_advance(self):
        for expense in self.sudo():
            advance = expense.advance_id
            if not advance:
                continue
            if expense.paid_by != "employee":
                raise ValidationError(_("Only an expense paid by an employee can come out of a cash advance."))
            if advance.user_id != expense.employee_user_id:
                raise ValidationError(_("The advance %(advance)s was given to %(user)s, not to the employee who paid.",
                                        advance=advance.name, user=advance.user_id.name))
            if advance.currency_id != expense.currency_id:
                raise ValidationError(_("The advance %s is in another currency.", advance.name))
            if advance.state == "draft":
                raise ValidationError(_("The advance %s has not been handed over yet.", advance.name))

    # ------------------------------------------------------------------
    # Advances and client money
    # ------------------------------------------------------------------
    @api.model
    def _ldm_open_advance(self, user, currency, company=None):
        """The oldest handed-over advance of ``user`` in ``currency`` that still has money."""
        domain = [("user_id", "=", user.id), ("state", "=", "paid"), ("currency_id", "=", currency.id)]
        if company:
            domain.append(("company_id", "=", company.id))
        advances = self.env["legal.advance"].sudo().search(domain, order="date, id")
        return advances.filtered(lambda a: a.currency_id.compare_amounts(a.balance, 0) > 0)[:1] or advances[:1]

    def _ldm_link_advance(self):
        for expense in self.filtered(lambda e: e.paid_by == "employee" and not e.advance_id and e.employee_user_id):
            advance = self._ldm_open_advance(expense.employee_user_id, expense.currency_id, expense.company_id)
            if advance:
                expense.sudo().advance_id = advance

    def _ldm_sync_fund_line(self):
        """One client-money disbursement per expense paid from the client's
        money; removed again when the expense stops being paid that way."""
        Fund = self.env["legal.client.fund.line"]
        for expense in self:
            line = expense.sudo().fund_line_id
            if expense.paid_by == "client_funds" and expense.state == "confirmed":
                values = {
                    "kind": "disbursement",
                    "legal_company_id": expense.task_id.legal_company_id.id,
                    "task_id": expense.task_id.id,
                    "company_id": expense.company_id.id or self.env.company.id,
                    "date": expense.date,
                    "amount": expense.amount,
                    "currency_id": expense.currency_id.id,
                    "receipt_number": expense.receipt_number or False,
                    "note": expense.name,
                }
                with engine_guard():
                    if line:
                        line.write(values)
                    else:
                        line = Fund.sudo().create(values)
                        super(LegalTaskExpense, expense.sudo()).write({"fund_line_id": line.id})
            elif line:
                super(LegalTaskExpense, expense.sudo()).write({"fund_line_id": False})
                with engine_guard():
                    line.unlink()

    # ------------------------------------------------------------------
    # Accounting links
    # ------------------------------------------------------------------
    def action_ldm_post(self):
        if not self._ldm_accounting_allowed():
            raise AccessError(_("Posting expenses needs the accounting links switch and invoicing rights."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Post to accounting"),
            "res_model": "legal.expense.post.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_expense_ids": self.ids},
        }
