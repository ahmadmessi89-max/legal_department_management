# -*- coding: utf-8 -*-
"""Declarations of the work records that hang off a matter: steps, required
documents and document types. Behaviour and views belong to the streams that own
them (workspace for steps, government for documents); the fields live here so
every stream codes against one contract."""
from odoo import api, fields, models


class LegalDocumentType(models.Model):
    _name = "legal.document.type"
    _description = "Document type"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("identity", "Identity"),
            ("registry", "Company registry"),
            ("tax", "Tax"),
            ("social_security", "Social security"),
            ("chamber", "Chamber of commerce"),
            ("contract", "Contract"),
            ("court", "Court"),
            ("poa", "Power of attorney"),
            ("receipt", "Receipt"),
            ("letter", "Official letter"),
            ("other", "Other"),
        ],
        string="Category", default="other", required=True)
    validity = fields.Selection(
        [
            ("none", "Does not expire"),
            ("expiry_date", "Has an expiry date"),
            ("fixed_days", "Valid for a fixed period"),
            ("freshness_days", "Must be recent"),
        ],
        string="Validity", default="none", required=True,
        help="How long a copy of this document can be relied on.")
    validity_days = fields.Integer(aggregator=None, string="Days")


class LegalTaskStep(models.Model):
    _name = "legal.task.step"
    _description = "Matter step"
    _order = "sequence, id"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Step", required=True)
    state = fields.Selection([("todo", "To do"), ("done", "Done"), ("skipped", "Skipped")],
                             string="Status", default="todo", required=True, index=True)
    date_due = fields.Date(string="Due")
    user_id = fields.Many2one("res.users", string="Assigned to", index=True)
    done_date = fields.Date(string="Done on")
    done_by_id = fields.Many2one("res.users", string="Done by")
    note = fields.Char(string="Note")
    is_visit = fields.Boolean(string="Visit to the body")
    department_id = fields.Many2one("legal.department", string="Body")
    receipt_number = fields.Char(string="Receipt number")
    fee_amount = fields.Monetary(string="Fee paid", currency_field="currency_id")
    currency_id = fields.Many2one(related="task_id.currency_id")
    attachment_id = fields.Many2one("ir.attachment", string="Photo of the receipt", ondelete="set null")
    visit_result = fields.Selection([("done", "Done at the counter"), ("pending", "Still pending"),
                                     ("rejected", "Rejected at the counter")], string="Visit result")
    expense_ids = fields.One2many("legal.task.expense", "step_id", string="Expenses")
    document_type_id = fields.Many2one("legal.document.type", string="Produces document", ondelete="set null")
    is_overdue = fields.Boolean(compute="_compute_is_overdue")

    def action_ldm_log_visit(self):
        """Interface (SPEC 14.4): open the counter-visit dialog. The government
        stream replaces this with its wizard; the foundation opens the step."""
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "legal.task.step", "res_id": self.id,
                "view_mode": "form", "target": "new"}

    @api.depends("date_due", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for step in self:
            step.is_overdue = bool(step.state == "todo" and step.date_due and step.date_due < today)


class LegalTaskDocument(models.Model):
    _name = "legal.task.document"
    _description = "Document to collect for a matter"
    _order = "sequence, id"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    document_type_id = fields.Many2one("legal.document.type", string="Document type", ondelete="restrict")
    name = fields.Char(string="Document", required=True)
    mandatory = fields.Boolean(string="Mandatory", default=True)
    state = fields.Selection(
        [
            ("missing", "Missing"),
            ("received", "Received"),
            ("verified", "Verified"),
            ("expired", "Expired"),
            ("not_needed", "Not needed"),
        ],
        string="Status", default="missing", required=True, index=True,
        help="Verified means the issuing body confirmed the document is genuine (صحة صدور).")
    attachment_id = fields.Many2one("ir.attachment", string="File", ondelete="set null")
    received_date = fields.Date(string="Received on")
    expiry_date = fields.Date(string="Expires on")
    company_document_id = fields.Many2one("legal.company.document", string="From the company's records", ondelete="set null")
    original_held = fields.Boolean(string="We hold the original",
                                   help="The client's original is in our custody and must be returned (Advocacy Law Art. 53).")
    note = fields.Char(string="Note")
