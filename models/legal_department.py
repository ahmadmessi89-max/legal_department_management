# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .ldm_text import normalize
from .legal_ministry import GOVERNORATES

COURT_DEGREES = [
    ("first_instance", "First instance (appealable)"),
    ("first_instance_final", "First instance (final degree)"),
    ("appeal", "Court of appeal"),
    ("cassation", "Court of cassation"),
    ("personal_status", "Personal status"),
    ("labour", "Labour"),
    ("investigation", "Investigation"),
    ("misdemeanour", "Misdemeanour"),
    ("felony", "Felony"),
    ("administrative", "Administrative"),
    ("employee", "Civil service"),
    ("execution", "Execution directorate"),
    ("other", "Other"),
]


class LegalDepartment(models.Model):
    _name = "legal.department"
    _description = "Government body, directorate or court"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, index=True)
    ministry_id = fields.Many2one("legal.ministry", string="Ministry / authority", ondelete="restrict", index=True)
    code = fields.Char(string="Code")
    contact_person = fields.Char(string="Contact person")
    phone = fields.Char(string="Phone")
    address = fields.Text(string="Address")
    notes = fields.Text(string="Notes")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)

    body_kind = fields.Selection(
        [
            ("government", "Government department"),
            ("court", "Court"),
            ("notary", "Notary"),
            ("execution", "Execution directorate"),
            ("registry", "Registry"),
            ("other", "Other"),
        ],
        string="Kind",
        default="government",
        required=True,
    )
    court_degree = fields.Selection(COURT_DEGREES, string="Court degree")
    parent_id = fields.Many2one(
        "legal.department", string="Higher court", index=True, ondelete="set null",
        help="The court that hears appeals or cassation from this court.")
    governorate = fields.Selection(GOVERNORATES, string="Governorate")
    resource_calendar_id = fields.Many2one("resource.calendar", string="Working calendar")
    working_hours = fields.Char(string="Opening hours")
    target_days = fields.Integer(string="Usual answer time (working days)")
    addressee_title = fields.Char(string="Letters are addressed to",
                                  help="Title used at the head of official letters, e.g. the director general.")
    location_url = fields.Char(string="Map link")
    contact_ids = fields.One2many("legal.department.contact", "department_id", string="Contacts")
    template_ids = fields.One2many("legal.task.template", "department_id", string="Services")
    task_count = fields.Integer(string="Matters", compute="_compute_task_count")
    open_task_count = fields.Integer(string="Open matters", compute="_compute_task_count")

    @api.constrains("name", "ministry_id")
    def _check_unique_department(self):
        for record in self:
            key = normalize(record.name)
            if not key:
                continue
            others = self.with_context(active_test=False).search(
                [("id", "!=", record.id), ("ministry_id", "=", record.ministry_id.id)])
            if any(normalize(other.name) == key for other in others):
                if record.ministry_id:
                    raise ValidationError(_("“%(name)s” already exists under %(ministry)s.",
                                            name=record.name.strip(), ministry=record.ministry_id.name))
                raise ValidationError(_("A body named “%s” already exists.", record.name.strip()))

    @api.constrains("parent_id")
    def _check_parent(self):
        for record in self:
            if record.parent_id and record._has_cycle():
                raise ValidationError(_("A court cannot be its own higher court."))

    def _compute_task_count(self):
        task = self.env["legal.task"]
        totals = dict((d.id, c) for d, c in task._read_group(
            [("department_id", "in", self.ids)], ["department_id"], ["__count"]))
        opened = dict((d.id, c) for d, c in task._read_group(
            [("department_id", "in", self.ids), ("state", "not in", ("done", "cancelled"))],
            ["department_id"], ["__count"]))
        for record in self:
            record.task_count = totals.get(record.id, 0)
            record.open_task_count = opened.get(record.id, 0)

    def _ldm_calendar(self):
        """The calendar that counts time at this body: its own, then its
        ministry's, then the company's legal calendar."""
        self.ensure_one()
        return (self.resource_calendar_id or self.ministry_id.resource_calendar_id
                or self.env.company._ldm_calendar())

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({
            "name": _("Matters at %s", self.name),
            "domain": [("department_id", "=", self.id)],
            "context": {"default_department_id": self.id},
        })
        return action


class LegalDepartmentContact(models.Model):
    _name = "legal.department.contact"
    _description = "Contact at a government body"
    _order = "sequence, id"

    department_id = fields.Many2one("legal.department", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Name", required=True)
    role = fields.Char(string="Role or counter")
    phone = fields.Char(string="Phone")
    notes = fields.Char(string="Notes")
