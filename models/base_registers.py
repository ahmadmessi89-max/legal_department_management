# -*- coding: utf-8 -*-
"""Declarations for the registers: powers of attorney, correspondence, letter
templates, requests from other departments, the company document vault and
recurring obligations. The registers and government streams own behaviour."""
from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain

from .legal_task_template import MATTER_KINDS  # noqa: F401  (kept for streams)


class LegalPoa(models.Model):
    _name = "legal.poa"
    _description = "Power of attorney"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_expiry, id desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    poa_type = fields.Selection(
        [("general", "General"), ("special", "Special"), ("judicial", "For litigation"),
         ("authorisation", "Authorisation"), ("consular", "Consular"), ("other", "Other")],
        string="Type", default="special", required=True, tracking=True)
    principal_company_id = fields.Many2one("legal.company", string="Principal", index=True, ondelete="restrict", tracking=True)
    principal_partner_id = fields.Many2one("res.partner", string="Principal (person)", ondelete="restrict")
    agent_user_ids = fields.Many2many("res.users", "legal_poa_agent_user_rel", "poa_id", "user_id", string="Agents")
    agent_partner_ids = fields.Many2many("res.partner", "legal_poa_agent_partner_rel", "poa_id", "partner_id",
                                         string="Other agents")
    notary_office = fields.Char(string="Notary office")
    number = fields.Char(string="Number", tracking=True)
    date_issued = fields.Date(string="Issued on")
    date_expiry = fields.Date(string="Expires on", tracking=True)
    scope = fields.Text(string="Scope")
    body_ids = fields.Many2many("legal.department", "legal_poa_department_rel", "poa_id", "department_id",
                                string="Valid before")
    substitution_allowed = fields.Boolean(string="Agent may delegate")
    original_location = fields.Char(string="Original kept at")
    attachment_id = fields.Many2one("ir.attachment", string="Scan", ondelete="set null")
    qr_reference = fields.Char(string="QR reference")
    state = fields.Selection([("active", "Active"), ("expired", "Expired"), ("revoked", "Revoked")],
                             string="Status", default="active", required=True, tracking=True, index=True)
    revoked_date = fields.Date(string="Revoked on", readonly=True)
    revoke_reason = fields.Text(string="Revocation reason", readonly=True)
    task_ids = fields.One2many("legal.task", "poa_id", string="Matters relying on it")

    @api.depends("poa_type", "number", "principal_company_id.name", "principal_partner_id.name")
    def _compute_name(self):
        types = dict(self._fields["poa_type"]._description_selection(self.env))
        for poa in self:
            principal = poa.principal_company_id.name or poa.principal_partner_id.name or ""
            parts = [types.get(poa.poa_type, ""), poa.number or "", principal]
            poa.name = " · ".join(p for p in parts if p)


class LegalLetterTemplate(models.Model):
    _name = "legal.letter.template"
    _description = "Letter template"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    direction = fields.Selection([("outgoing", "Outgoing letter"), ("notice", "Notice"), ("client", "Message to a client")],
                                 string="Use", default="outgoing", required=True)
    subject = fields.Char(string="Subject", translate=True)
    body = fields.Text(string="Body", translate=True,
                       help="Plain text with placeholders in braces, for example {matter_number}, {client}, {body}, "
                       "{today}, {responsible}. Nothing else is evaluated.")


class LegalCorrespondence(models.Model):
    _name = "legal.correspondence"
    _description = "Correspondence"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Subject", required=True, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    direction = fields.Selection([("incoming", "Incoming"), ("outgoing", "Outgoing")],
                                 string="Direction", required=True, default="outgoing", index=True)
    number = fields.Char(string="Number", copy=False, tracking=True, index=True)
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    sender_ref = fields.Char(string="Their number")
    sender_date = fields.Date(string="Their date")
    received_date = fields.Date(string="Received on")
    referred_by = fields.Char(string="Referred by", help="Who wrote the instruction on the letter (هامش).")
    referral_note = fields.Text(string="Instruction")
    instruction_due = fields.Date(string="Instruction due")
    signatory_id = fields.Many2one("res.users", string="Signed by")
    signatory_title = fields.Char(string="Signatory title")
    cc_lines = fields.Text(string="Copies to", help="One addressee per line (نسخة منه إلى).")
    lang = fields.Selection(lambda self: self.env["res.lang"].get_installed(), string="Letter language",
                            default=lambda self: "ar_001" if self.env["res.lang"]._lang_get("ar_001") else self.env.lang)
    department_id = fields.Many2one("legal.department", string="Body", ondelete="restrict")
    partner_id = fields.Many2one("res.partner", string="Other party", ondelete="restrict")
    task_id = fields.Many2one("legal.task", string="Matter", index=True, ondelete="set null")
    legal_company_id = fields.Many2one("legal.company", string="Client", index=True, ondelete="restrict")
    template_id = fields.Many2one("legal.letter.template", string="Template", ondelete="set null")
    body_html = fields.Html(string="Letter")
    reply_to_id = fields.Many2one("legal.correspondence", string="Replies to", ondelete="set null")
    reply_due_date = fields.Date(string="Reply due")
    attachment_ids = fields.Many2many("ir.attachment", "legal_correspondence_attachment_rel",
                                      "correspondence_id", "attachment_id", string="Files")
    state = fields.Selection([("draft", "Draft"), ("registered", "Registered"), ("void", "Void")],
                             string="Status", default="draft", required=True, tracking=True, index=True)
    void_reason = fields.Text(string="Why it was voided", readonly=True)


class LegalRequest(models.Model):
    _name = "legal.request"
    _description = "Request to the legal team"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="What do you need?", required=True, tracking=True)
    request_type = fields.Selection(
        [("contract", "Contract review"), ("opinion", "Legal opinion"), ("poa", "Power of attorney"),
         ("government", "Government transaction"), ("dispute", "Dispute or lawsuit"), ("other", "Other")],
        string="Kind of help", default="other", required=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    requester_id = fields.Many2one("res.users", string="Requested by", required=True, index=True,
                                   default=lambda self: self.env.user, tracking=True)
    legal_company_id = fields.Many2one("legal.company", string="For which company", ondelete="restrict")
    needed_by = fields.Date(string="Needed by")
    description = fields.Text(string="Details")
    attachment_ids = fields.Many2many("ir.attachment", "legal_request_attachment_rel", "request_id", "attachment_id",
                                      string="Files")
    state = fields.Selection(
        [("new", "Sent"), ("in_review", "Being reviewed"), ("returned", "Returned to you"),
         ("accepted", "Accepted"), ("rejected", "Declined")],
        string="Status", default="new", required=True, tracking=True, index=True)
    return_reason = fields.Text(string="Reason")
    task_id = fields.Many2one("legal.task", string="Matter", readonly=True, ondelete="set null")
    assigned_user_id = fields.Many2one("res.users", string="Handled by", tracking=True)


class LegalCompanyDocument(models.Model):
    _name = "legal.company.document"
    _description = "Company document"
    _inherit = ["mail.thread"]
    _order = "date_expiry, id desc"

    legal_company_id = fields.Many2one("legal.company", string="Client", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="legal_company_id.company_id", store=True, index=True)
    document_type_id = fields.Many2one("legal.document.type", string="Document type", required=True, ondelete="restrict")
    name = fields.Char(string="Description")
    number = fields.Char(string="Number")
    date_issued = fields.Date(string="Issued on")
    date_expiry = fields.Date(string="Expires on", tracking=True)
    attachment_id = fields.Many2one("ir.attachment", string="File", ondelete="set null")
    state = fields.Selection([("valid", "Valid"), ("expiring", "Expiring soon"), ("expired", "Expired")],
                             string="Status", compute="_compute_state", search="_search_state")
    confidential = fields.Boolean(string="Confidential")
    original_held = fields.Boolean(string="We hold the original")
    active = fields.Boolean(default=True)

    @api.depends("date_expiry")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        warn = self.env.company.ldm_poa_warning_days or 30
        for doc in self:
            if doc.date_expiry and doc.date_expiry < today:
                doc.state = "expired"
            elif doc.date_expiry and (doc.date_expiry - today).days <= warn:
                doc.state = "expiring"
            else:
                doc.state = "valid"

    def _search_state(self, operator, value):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=self.env.company.ldm_poa_warning_days or 30)
        domains = {
            "expired": Domain("date_expiry", "<", today),
            "expiring": Domain("date_expiry", ">=", today) & Domain("date_expiry", "<=", soon),
            "valid": Domain("date_expiry", "=", False) | Domain("date_expiry", ">", soon),
        }
        if operator not in ("=", "!=", "in", "not in"):
            return NotImplemented
        values = [value] if isinstance(value, str) else list(value)
        domain = Domain.OR([domains[v] for v in values if v in domains] or [Domain.FALSE])
        return domain if operator in ("=", "in") else ~domain


class LegalObligation(models.Model):
    _name = "legal.obligation"
    _description = "Recurring obligation"
    _order = "next_date, id"

    name = fields.Char(string="Obligation", required=True)
    legal_company_id = fields.Many2one("legal.company", string="Client", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="legal_company_id.company_id", store=True, index=True)
    template_id = fields.Many2one("legal.task.template", string="Opens a matter of type", ondelete="set null")
    recurrence = fields.Selection([("monthly", "Every month"), ("yearly", "Every year")],
                                  string="Repeats", default="yearly", required=True)
    month = fields.Integer(string="Month", default=1)
    day = fields.Integer(string="Day", default=1)
    lead_days = fields.Integer(string="Open the matter this many days before", default=30)
    next_date = fields.Date(string="Next due date")
    last_task_id = fields.Many2one("legal.task", string="Last matter", ondelete="set null")
    active = fields.Boolean(default=True)


class LegalGuarantee(models.Model):
    """A letter of guarantee (خطاب ضمان): bid, performance or advance payment.
    Letting a performance guarantee lapse unextended leaves the contract unsecured."""

    _name = "legal.guarantee"
    _description = "Letter of guarantee"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_expiry, id desc"

    name = fields.Char(string="Reference", required=True, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    kind = fields.Selection([("bid", "Bid"), ("performance", "Performance"), ("advance_payment", "Advance payment"),
                             ("other", "Other")], string="Kind", required=True, default="performance")
    bank_id = fields.Many2one("res.partner", string="Bank", ondelete="restrict")
    number = fields.Char(string="Number")
    amount = fields.Monetary(string="Amount", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    percent = fields.Float(string="Percent of the contract")
    legal_company_id = fields.Many2one("legal.company", string="Principal", ondelete="restrict", index=True)
    beneficiary_id = fields.Many2one("res.partner", string="Beneficiary", ondelete="restrict")
    date_issued = fields.Date(string="Issued on")
    date_expiry = fields.Date(string="Expires on", tracking=True)
    state = fields.Selection([("active", "Active"), ("extension_requested", "Extension requested"),
                              ("extended", "Extended"), ("released", "Released"), ("liquidated", "Liquidated"),
                              ("expired", "Expired")], string="Status", default="active", required=True, tracking=True)
    task_id = fields.Many2one("legal.task", string="Contract matter", ondelete="set null", index=True)
    attachment_id = fields.Many2one("ir.attachment", string="Scan", ondelete="set null")
