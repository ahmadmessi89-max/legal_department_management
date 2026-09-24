# -*- coding: utf-8 -*-
""""To invoice": one list of everything that can go on the next invoice.

Three sources, read through one SQL view so they can be listed, grouped by
client and currency, filtered and selected together: fee instalments that are
due, approved billable time, and confirmed expenses that are recharged to the
client. Nothing is copied; each row points at its source, and the source leaves
the list as soon as it is linked to an invoice line.
"""
from odoo import _, api, fields, models, tools


class LegalBillable(models.Model):
    _name = "legal.billable"
    _description = "To invoice"
    _auto = False
    _order = "legal_company_id, currency_id, date, id"
    _rec_name = "name"
    # Pending writes to these fields are flushed before the view is read.
    _depends = {
        "legal.engagement.line": ["engagement_id", "name", "date", "task_id", "amount", "state", "invoice_line_id"],
        "legal.engagement": ["legal_company_id", "company_id", "currency_id", "lawyer_id", "date_start"],
        "legal.time.entry": ["task_id", "description", "date", "currency_id", "duration", "amount", "user_id",
                             "billable", "state", "invoice_line_id"],
        "legal.task.expense": ["task_id", "name", "date", "currency_id", "amount", "recoverable", "state",
                               "invoice_line_id", "paid_by"],
        "legal.task": ["legal_company_id", "engagement_id", "company_id", "lawyer_id"],
        "legal.company": ["partner_id", "name"],
    }

    kind = fields.Selection([("fee", "Fee"), ("time", "Time"), ("expense", "Expense")], string="What",
                            readonly=True)
    name = fields.Char(string="Description", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    legal_company_id = fields.Many2one("legal.company", string="Client", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Invoice to", readonly=True)
    task_id = fields.Many2one("legal.task", string="Matter", readonly=True)
    engagement_id = fields.Many2one("legal.engagement", string="Fee agreement", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    group_key = fields.Char(string="Client and currency", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    amount = fields.Monetary(string="Amount", currency_field="currency_id", readonly=True)
    user_id = fields.Many2one("res.users", string="Lawyer", readonly=True)
    fee_line_id = fields.Many2one("legal.engagement.line", string="Instalment", readonly=True)
    time_entry_id = fields.Many2one("legal.time.entry", string="Time entry", readonly=True)
    expense_id = fields.Many2one("legal.task.expense", string="Expense", readonly=True)
    is_overdue = fields.Boolean(string="Overdue", compute="_compute_is_overdue")
    ldm_can_message = fields.Boolean(compute="_compute_ldm_can_message")

    @api.depends_context("uid")
    def _compute_ldm_can_message(self):
        allowed = self.env["legal.task"]._ldm_user_can_message()
        for row in self:
            row.ldm_can_message = allowed and row.kind == "fee"

    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for row in self:
            row.is_overdue = bool(row.kind == "fee" and row.date and row.date < today)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT l.id * 10 + 1 AS id,
                       'fee' AS kind,
                       l.name AS name,
                       COALESCE(l.date, e.date_start) AS date,
                       e.legal_company_id AS legal_company_id,
                       lc.partner_id AS partner_id,
                       COALESCE(l.task_id, (
                           SELECT min(m.id) FROM legal_task m WHERE m.engagement_id = e.id HAVING count(*) = 1
                       )) AS task_id,
                       e.id AS engagement_id,
                       e.company_id AS company_id,
                       e.currency_id AS currency_id,
                       1.0 AS quantity,
                       l.amount AS amount,
                       e.lawyer_id AS user_id,
                       l.id AS fee_line_id,
                       NULL::integer AS time_entry_id,
                       NULL::integer AS expense_id,
                       lc.name || ' · ' || (SELECT c.name FROM res_currency c WHERE c.id = e.currency_id) AS group_key
                  FROM legal_engagement_line l
                  JOIN legal_engagement e ON e.id = l.engagement_id
                  JOIN legal_company lc ON lc.id = e.legal_company_id
                 WHERE l.state = 'due' AND l.invoice_line_id IS NULL
                UNION ALL
                SELECT t.id * 10 + 2,
                       'time',
                       t.description,
                       t.date,
                       m.legal_company_id,
                       lc.partner_id,
                       t.task_id,
                       m.engagement_id,
                       m.company_id,
                       COALESCE(t.currency_id, rc.currency_id),
                       t.duration,
                       t.amount,
                       t.user_id,
                       NULL::integer,
                       t.id,
                       NULL::integer,
                       lc.name || ' · ' || (SELECT c.name FROM res_currency c
                                             WHERE c.id = COALESCE(t.currency_id, rc.currency_id))
                  FROM legal_time_entry t
                  JOIN legal_task m ON m.id = t.task_id
                  JOIN legal_company lc ON lc.id = m.legal_company_id
                  JOIN res_company rc ON rc.id = m.company_id
                 WHERE t.billable AND t.state = 'approved' AND t.invoice_line_id IS NULL AND t.amount <> 0
                UNION ALL
                SELECT x.id * 10 + 3,
                       'expense',
                       x.name,
                       x.date,
                       m.legal_company_id,
                       lc.partner_id,
                       x.task_id,
                       m.engagement_id,
                       m.company_id,
                       x.currency_id,
                       1.0,
                       x.amount,
                       m.lawyer_id,
                       NULL::integer,
                       NULL::integer,
                       x.id,
                       lc.name || ' · ' || (SELECT c.name FROM res_currency c WHERE c.id = x.currency_id)
                  FROM legal_task_expense x
                  JOIN legal_task m ON m.id = x.task_id
                  JOIN legal_company lc ON lc.id = m.legal_company_id
                 WHERE x.recoverable AND x.state = 'confirmed' AND x.invoice_line_id IS NULL
                   AND x.paid_by IN ('office', 'employee') AND x.amount <> 0
            )
        """)

    def action_ldm_invoice(self):
        return self.env["legal.invoice.wizard"].ldm_open(billables=self)

    def action_ldm_remind(self):
        self.ensure_one()
        if self.kind != "fee":
            return False
        return self.env["legal.client.message.wizard"].ldm_open("instalment_due", fee_line=self.fee_line_id)

    def action_ldm_open_source(self):
        self.ensure_one()
        source = self.fee_line_id.engagement_id or self.time_entry_id or self.expense_id
        return {"type": "ir.actions.act_window", "res_model": source._name, "res_id": source.id,
                "views": [[False, "form"]], "target": "current", "name": _("To invoice")}
