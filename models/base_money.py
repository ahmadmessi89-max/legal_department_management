# -*- coding: utf-8 -*-
"""Declarations for money on matters: expense lines (both modes), fee
agreements with their schedule, time entries and conflict checks (office mode).
The money stream owns behaviour, invoicing and views."""
from odoo import api, fields, models

FEE_TYPES = [
    ("lump_sum", "Lump sum"),
    ("installments", "Instalments"),
    ("success", "Success fee"),
    ("retainer", "Retainer"),
    ("per_transaction", "Per transaction"),
    ("per_hearing", "Per hearing"),
    ("consultation", "Consultation"),
    ("hourly", "Hourly"),
]


class LegalExpenseCategory(models.Model):
    _name = "legal.expense.category"
    _description = "Expense category"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    recoverable_default = fields.Boolean(string="Recharged to the client by default", default=True)
    account_id = fields.Many2one("account.account", string="Expense account", ondelete="set null",
                                 company_dependent=True)


class LegalTaskExpense(models.Model):
    _name = "legal.task.expense"
    _description = "Expense on a matter"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    legal_company_id = fields.Many2one(related="task_id.legal_company_id", store=True, string="Client")
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    category_id = fields.Many2one("legal.expense.category", string="Category", ondelete="restrict")
    name = fields.Char(string="Description", required=True)
    amount = fields.Monetary(string="Amount", required=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    amount_company = fields.Monetary(string="Amount in company currency", currency_field="company_currency_id",
                                     compute="_compute_amount_company", store=True)
    company_currency_id = fields.Many2one(related="task_id.company_id.currency_id", string="Company currency")
    receipt_number = fields.Char(string="Receipt number")
    paid_by = fields.Selection(
        [("office", "Paid by us"), ("employee", "Paid by an employee from an advance"),
         ("client_funds", "Paid from the client's money we hold"), ("client", "Paid by the client directly")],
        string="Paid by", default="office", required=True)
    employee_user_id = fields.Many2one("res.users", string="Employee", ondelete="set null")
    recoverable = fields.Boolean(string="Recharge to the client")
    invoice_line_id = fields.Many2one("account.move.line", string="Invoice line", readonly=True, copy=False,
                                      ondelete="set null", groups="account.group_account_invoice,account.group_account_readonly")
    billed = fields.Boolean(string="Invoiced", compute="_compute_billed", store=True, compute_sudo=True)
    move_id = fields.Many2one("account.move", string="Journal entry", readonly=True, copy=False, ondelete="set null",
                              groups="account.group_account_invoice,account.group_account_readonly")
    payment_id = fields.Many2one("account.payment", string="Payment", readonly=True, copy=False, ondelete="set null",
                                 groups="account.group_account_invoice,account.group_account_readonly")
    advance_id = fields.Many2one("legal.advance", string="Advance", ondelete="set null", index=True)
    fund_line_id = fields.Many2one("legal.client.fund.line", string="Client money line", readonly=True, copy=False,
                                   ondelete="set null")
    attachment_id = fields.Many2one("ir.attachment", string="Receipt", ondelete="set null")
    state = fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed")], string="Status",
                             default="confirmed", required=True)
    step_id = fields.Many2one("legal.task.step", string="Step", ondelete="set null")
    hearing_id = fields.Many2one("legal.hearing", string="Visit", ondelete="set null")

    @api.depends("amount", "currency_id", "date", "task_id.company_id")
    def _compute_amount_company(self):
        for line in self:
            company = line.task_id.company_id or self.env.company
            if not line.currency_id or line.currency_id == company.currency_id:
                line.amount_company = line.amount
            else:
                line.amount_company = line.currency_id._convert(
                    line.amount, company.currency_id, company, line.date or fields.Date.context_today(line))

    @api.depends("invoice_line_id")
    def _compute_billed(self):
        for line in self:
            line.billed = bool(line.invoice_line_id)


class LegalEngagement(models.Model):
    _name = "legal.engagement"
    _description = "Fee agreement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(string="Agreement", required=True, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    legal_company_id = fields.Many2one("legal.company", string="Client", required=True, ondelete="restrict",
                                       index=True, tracking=True)
    partner_id = fields.Many2one(related="legal_company_id.partner_id", string="Invoice to")
    task_ids = fields.One2many("legal.task", "engagement_id", string="Matters")
    lawyer_id = fields.Many2one("res.users", string="Responsible lawyer", default=lambda self: self.env.user)
    date_start = fields.Date(string="Start", default=fields.Date.context_today)
    date_end = fields.Date(string="End")
    fee_type = fields.Selection(FEE_TYPES, string="Fee arrangement", required=True, default="lump_sum", tracking=True)
    amount = fields.Monetary(string="Agreed fee", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    success_percent = fields.Float(aggregator=None, string="Success fee (%)",
                                   help="Can be combined with any arrangement, e.g. a lump sum plus a success fee.")
    cap_override_reason = fields.Text(string="Why the 20% cap is exceeded", tracking=True)
    retainer_period = fields.Selection([("monthly", "Monthly"), ("yearly", "Yearly")], string="Retainer billed")
    retainer_next_date = fields.Date(string="Next retainer invoice")
    hourly_rate = fields.Monetary(string="Hourly rate", currency_field="currency_id")
    bar_withholding = fields.Boolean(string="Bar 5% withholding",
                                     help="Iraqi Bar administrative order 3021 of 2021 on company legal-adviser retainers.")
    signed = fields.Boolean(string="Signed", tracking=True)
    signed_date = fields.Date(string="Signed on")
    attachment_id = fields.Many2one("ir.attachment", string="Signed copy", ondelete="set null")
    state = fields.Selection([("draft", "Draft"), ("active", "Active"), ("closed", "Closed")],
                             string="Status", default="draft", required=True, tracking=True)
    line_ids = fields.One2many("legal.engagement.line", "engagement_id", string="Schedule", copy=True)
    note = fields.Text(string="Scope and terms")


class LegalEngagementLine(models.Model):
    _name = "legal.engagement.line"
    _description = "Fee schedule line"
    _order = "sequence, date, id"

    engagement_id = fields.Many2one("legal.engagement", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="engagement_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="engagement_id.currency_id")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description", required=True)
    trigger_event = fields.Selection(
        [("signing", "On signing"), ("filing", "When the case is filed"),
         ("judgment_first_instance", "At the first-instance judgment"),
         ("judgment_final", "When the judgment becomes final"), ("execution_opened", "When execution opens"),
         ("collection", "When money is collected"), ("closing", "When the matter closes"),
         ("date", "On a date"), ("manual", "When we decide")],
        string="Due", default="date", required=True)
    date = fields.Date(string="Date")
    task_id = fields.Many2one("legal.task", string="Matter", ondelete="set null")
    amount = fields.Monetary(string="Amount", required=True, currency_field="currency_id")
    invoice_line_id = fields.Many2one("account.move.line", string="Invoice line", readonly=True, copy=False,
                                      ondelete="set null", groups="account.group_account_invoice,account.group_account_readonly")
    state = fields.Selection([("planned", "Planned"), ("due", "Due"), ("invoiced", "Invoiced"), ("paid", "Paid"),
                              ("waived", "Waived")],
                             string="Status", default="planned", required=True, index=True)


class LegalTimeEntry(models.Model):
    _name = "legal.time.entry"
    _description = "Time entry"
    _order = "date desc, id desc"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    legal_company_id = fields.Many2one(related="task_id.legal_company_id", store=True, string="Client")
    user_id = fields.Many2one("res.users", string="Who", required=True, default=lambda self: self.env.user, index=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    duration = fields.Float(string="Hours", required=True)
    description = fields.Char(string="What was done", required=True)
    billable = fields.Boolean(string="Billable", default=True)
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    rate = fields.Monetary(string="Rate", currency_field="currency_id")
    amount = fields.Monetary(string="Value", currency_field="currency_id", compute="_compute_amount", store=True)
    invoice_line_id = fields.Many2one("account.move.line", string="Invoice line", readonly=True, copy=False,
                                      ondelete="set null", groups="account.group_account_invoice,account.group_account_readonly")
    state = fields.Selection([("draft", "Draft"), ("approved", "Approved"), ("invoiced", "Invoiced")],
                             string="Status", default="draft", required=True, index=True)

    @api.depends("duration", "rate", "billable")
    def _compute_amount(self):
        for entry in self:
            entry.amount = entry.duration * entry.rate if entry.billable else 0.0


class LegalConflictCheck(models.Model):
    _name = "legal.conflict.check"
    _description = "Conflict of interest check"
    _order = "id desc"

    task_id = fields.Many2one("legal.task", string="Matter", ondelete="set null", index=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    query = fields.Char(string="Names checked", required=True)
    hits = fields.Json(string="Matches")
    hit_count = fields.Integer(string="Matches found")
    decision = fields.Selection([("pending", "Waiting for a partner"), ("clear", "No conflict"),
                                 ("override", "Accepted despite a match"), ("declined", "Declined")],
                                string="Decision", required=True, default="clear")
    decided_by_id = fields.Many2one("res.users", string="Decided by", readonly=True)
    reason = fields.Text(string="Reason")
    user_id = fields.Many2one("res.users", string="Checked by", required=True, default=lambda self: self.env.user)
    date = fields.Datetime(string="Checked on", required=True, default=fields.Datetime.now)


class LegalClientFundLine(models.Model):
    """Client money the office holds (أمانات الموكلين): deposits for court fees
    and experts, collections from execution, and what is paid out of them. An
    operational ledger in v1; posting to the general ledger comes later."""

    _name = "legal.client.fund.line"
    _description = "Client money movement"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    legal_company_id = fields.Many2one("legal.company", string="Client", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    task_id = fields.Many2one("legal.task", string="Matter", ondelete="set null", index=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    kind = fields.Selection(
        [("deposit", "Received from the client"), ("disbursement", "Paid out for the client"),
         ("execution_collection", "Collected through execution"), ("transfer_to_fees", "Applied to our fees"),
         ("refund", "Returned to the client")],
        string="Movement", required=True, default="deposit", tracking=True)
    amount = fields.Monetary(string="Amount", required=True, currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    signed_amount = fields.Monetary(string="Effect on balance", currency_field="currency_id",
                                    compute="_compute_signed_amount", store=True)
    receipt_number = fields.Char(string="Receipt number")
    attachment_id = fields.Many2one("ir.attachment", string="Receipt", ondelete="set null")
    note = fields.Char(string="Note")
    override_reason = fields.Text(string="Why the balance may go below zero", readonly=True)

    @api.depends("kind", "amount")
    def _compute_signed_amount(self):
        for line in self:
            incoming = line.kind in ("deposit", "execution_collection")
            line.signed_amount = line.amount if incoming else -line.amount


class LegalAdvance(models.Model):
    """Cash advanced to a runner (سلفة) to pay government fees, settled against
    the receipts of the expenses paid from it."""

    _name = "legal.advance"
    _description = "Cash advance"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(string="Purpose", required=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    user_id = fields.Many2one("res.users", string="Given to", required=True, index=True,
                              default=lambda self: self.env.user, tracking=True)
    task_id = fields.Many2one("legal.task", string="Matter", ondelete="set null")
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string="Amount", required=True, currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    expense_ids = fields.One2many("legal.task.expense", "advance_id", string="Paid from it")
    returned_amount = fields.Monetary(string="Cash returned", currency_field="currency_id")
    spent_amount = fields.Monetary(string="Spent", currency_field="currency_id", compute="_compute_balance", store=True)
    balance = fields.Monetary(string="Still to account for", currency_field="currency_id",
                              compute="_compute_balance", store=True)
    state = fields.Selection([("draft", "Draft"), ("paid", "Handed over"), ("settled", "Settled")],
                             string="Status", default="draft", required=True, tracking=True)

    @api.depends("amount", "returned_amount", "expense_ids.amount", "expense_ids.currency_id")
    def _compute_balance(self):
        for advance in self:
            spent = sum(e.amount for e in advance.expense_ids if e.currency_id == advance.currency_id)
            advance.spent_amount = spent
            advance.balance = advance.amount - spent - advance.returned_amount
