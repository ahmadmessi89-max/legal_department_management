# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

OPEN_STATES = ("draft", "in_progress", "pending_docs")


class LegalCompany(models.Model):
    """The party the legal work is done for: a client of the office, or a
    company of the group in an in-house department. Backed by a partner so it
    can be invoiced, written to and given portal access."""

    _name = "legal.company"
    _description = "Client"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Name", required=True, index=True, tracking=True)
    code = fields.Char(string="Reference", copy=False, tracking=True)
    active = fields.Boolean(default=True, string="Active")
    company_id = fields.Many2one("res.company", string="Company", index=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    partner_id = fields.Many2one("res.partner", string="Contact", ondelete="restrict", index=True, copy=False,
                                 help="The contact used for letters, invoices and portal access.")
    client_kind = fields.Selection([("company", "Company"), ("individual", "Individual")],
                                   string="Client is", default="company", required=True)
    company_type = fields.Selection(
        [
            ("llc", "Limited liability company"),
            ("joint_stock", "Private joint-stock company"),
            ("sole", "Sole proprietorship"),
            ("foreign_branch", "Branch of a foreign company"),
            ("partnership", "General partnership"),
            ("simple", "Simple company"),
            ("mixed", "Mixed company"),
            ("public", "Public company or state body"),
            ("other", "Other"),
        ],
        string="Legal form", default="llc", tracking=True)
    owner_name = fields.Char(string="Managing director", tracking=True)
    entity_type = fields.Char(string="Business activity", tracking=True)
    registration_number = fields.Char(string="Registration number", tracking=True)
    tax_number = fields.Char(string="Tax number", tracking=True)
    social_security_number = fields.Char(string="Social security number")
    chamber_number = fields.Char(string="Chamber of commerce ID")
    chamber_grade = fields.Char(string="Chamber grade")
    national_id = fields.Char(string="National ID")
    # One source of truth: the contact. SAG's own columns are copied onto the
    # contact by the migration and then left unused.
    phone = fields.Char(related="partner_id.phone", readonly=False, string="Phone")
    email = fields.Char(related="partner_id.email", readonly=False, string="Email")
    address = fields.Text(string="Address", tracking=True)
    notes = fields.Text(string="Notes")

    lawyer_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user,
                                tracking=True, index=True)
    lawyer_ids = fields.Many2many("res.users", "legal_company_lawyers_rel", "company_id", "user_id",
                                  string="Lawyers", default=lambda self: [self.env.user.id], tracking=True)
    employee_ids = fields.Many2many("hr.employee", "legal_company_employees_rel", "company_id", "employee_id",
                                    string="Staff team", tracking=True)
    attachment_ids = fields.Many2many("ir.attachment", "legal_company_ir_attachment_rel", "company_id",
                                      "attachment_id", string="Files")

    task_ids = fields.One2many("legal.task", "legal_company_id", string="Matters")
    document_ids = fields.One2many("legal.company.document", "legal_company_id", string="Document vault")
    poa_ids = fields.One2many("legal.poa", "principal_company_id", string="Powers of attorney")
    obligation_ids = fields.One2many("legal.obligation", "legal_company_id", string="Recurring obligations")
    engagement_ids = fields.One2many("legal.engagement", "legal_company_id", string="Fee agreements")

    # Counts are computed as the viewer: a lawyer never learns of matters they
    # cannot open. The stored columns SAG had stay in the table, unused.
    task_count = fields.Integer(string="Number of matters", compute="_compute_counts")
    pending_tasks_count = fields.Integer(string="Open matters", compute="_compute_counts")
    department_count = fields.Integer(string="Bodies", compute="_compute_counts")
    ministry_count = fields.Integer(string="Ministries", compute="_compute_counts")
    document_count = fields.Integer(string="Number of files", compute="_compute_counts")
    open_hearing_count = fields.Integer(string="Sessions in 30 days", compute="_compute_counts")
    expiring_document_count = fields.Integer(string="Expiring documents", compute="_compute_counts")
    poa_count = fields.Integer(string="Active powers of attorney", compute="_compute_counts")
    total_expenses = fields.Monetary(string="Expenses", compute="_compute_counts", currency_field="currency_id")

    def _compute_counts(self):
        Task = self.env["legal.task"]
        ids = self.ids
        totals = {c.id: n for c, n in Task._read_group([("legal_company_id", "in", ids)], ["legal_company_id"], ["__count"])}
        opened = {c.id: n for c, n in Task._read_group(
            [("legal_company_id", "in", ids), ("state", "in", OPEN_STATES)], ["legal_company_id"], ["__count"])}
        bodies = {c.id: n for c, n in Task._read_group(
            [("legal_company_id", "in", ids), ("department_id", "!=", False)],
            ["legal_company_id"], ["department_id:count_distinct"])}
        ministries = {c.id: n for c, n in Task._read_group(
            [("legal_company_id", "in", ids), ("ministry_id", "!=", False)],
            ["legal_company_id"], ["ministry_id:count_distinct"])}
        today = fields.Date.context_today(self)
        from datetime import timedelta
        hearings = {c.id: n for c, n in self.env["legal.hearing"]._read_group(
            [("legal_company_id", "in", ids), ("state", "=", "planned"),
             ("date", ">=", today), ("date", "<=", today + timedelta(days=30))],
            ["legal_company_id"], ["__count"])}
        expiring = {c.id: n for c, n in self.env["legal.company.document"]._read_group(
            [("legal_company_id", "in", ids), ("state", "in", ("expiring", "expired"))],
            ["legal_company_id"], ["__count"])}
        poas = {c.id: n for c, n in self.env["legal.poa"]._read_group(
            [("principal_company_id", "in", ids), ("state", "=", "active")], ["principal_company_id"], ["__count"])}
        expenses = {c.id: amount for c, amount in self.env["legal.task.expense"]._read_group(
            [("legal_company_id", "in", ids)], ["legal_company_id"], ["amount_company:sum"])}
        for record in self:
            record.task_count = totals.get(record.id, 0)
            record.pending_tasks_count = opened.get(record.id, 0)
            record.department_count = bodies.get(record.id, 0)
            record.ministry_count = ministries.get(record.id, 0)
            record.document_count = len(record.attachment_ids)
            record.open_hearing_count = hearings.get(record.id, 0)
            record.expiring_document_count = expiring.get(record.id, 0)
            record.poa_count = poas.get(record.id, 0)
            record.total_expenses = expenses.get(record.id, 0.0)

    # ------------------------------------------------------------------
    # Partner link
    # ------------------------------------------------------------------
    def _ldm_partner_values(self):
        self.ensure_one()
        return {
            "name": self.name,
            "is_company": self.client_kind == "company",
            "street": (self.address or "").strip().split("\n")[0] or False,
            "vat": self.tax_number or False,
            "company_registry": self.registration_number or False,
            "company_id": self.company_id.id or False,
        }

    def _ldm_ensure_partner(self, contact=None):
        """Create the contact of every client that has none. Done with sudo: a
        lawyer registering a client must not need contact-management rights."""
        contact = contact or {}
        for record in self.filtered(lambda r: not r.partner_id):
            values = record._ldm_partner_values()
            values.update({k: v for k, v in contact.get(record.id, {}).items() if v})
            record.partner_id = self.env["res.partner"].sudo().create(values)

    @api.model_create_multi
    def create(self, vals_list):
        contacts = []
        for vals in vals_list:
            contacts.append({"phone": vals.pop("phone", False), "email": vals.pop("email", False)})
        records = super().create(vals_list)
        records._ldm_ensure_partner({rec.id: contact for rec, contact in zip(records, contacts)})
        records._ldm_adopt_attachments()
        return records

    def write(self, vals):
        if {"lawyer_id", "lawyer_ids"} & set(vals) and not self.env.su and not self._ldm_is_manager():
            for record in self:
                if record.lawyer_id != self.env.user:
                    raise UserError(_("Only the lawyer responsible for %s or a legal manager can change who looks after it.",
                                      record.name))
        if {"phone", "email"} & set(vals):
            self.filtered(lambda r: not r.partner_id)._ldm_ensure_partner()
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._ldm_adopt_attachments()
        synced = {"name", "tax_number", "registration_number", "client_kind"}
        if synced & set(vals):
            for record in self.filtered("partner_id"):
                values = record._ldm_partner_values()
                values.pop("company_id", None)
                values.pop("street", None)
                record.partner_id.sudo().write(values)
        return result

    def _ldm_is_manager(self):
        return self.env.user.has_group("legal_department_management.group_legal_manager")

    def _ldm_adopt_attachments(self):
        """Attach the current user's uploads made before the first save (see legal.task)."""
        uid = self.env.uid
        for record in self:
            orphans = record.sudo().attachment_ids.filtered(
                lambda a: not a.res_id and a.res_model in (False, record._name) and a.create_uid.id == uid)
            if orphans:
                orphans.write({"res_model": record._name, "res_id": record.id})

    def unlink(self):
        self.check_access("unlink")
        if not self.env.su and not self.env.user.has_group("legal_department_management.group_legal_manager"):
            raise UserError(_("Only a legal manager can delete a client. Archive it instead."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Actions (names kept from 19.0.6.3.0)
    # ------------------------------------------------------------------
    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({
            "name": _("Matters of %s", self.name),
            "domain": [("legal_company_id", "=", self.id)],
            "context": {"default_legal_company_id": self.id, "search_default_filter_open": 1},
        })
        return action

    def action_create_new_task(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "legal_department_management.action_legal_task_create_wizard")
        action["context"] = {"default_legal_company_id": self.id}
        return action

    def action_print_company_report(self):
        self.ensure_one()
        return self.env.ref("legal_department_management.action_report_legal_company").report_action(self)
