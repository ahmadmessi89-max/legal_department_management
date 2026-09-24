# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .ldm_text import normalize

GOVERNORATES = [
    ("baghdad", "Baghdad"), ("basra", "Basra"), ("nineveh", "Nineveh"), ("erbil", "Erbil"),
    ("sulaymaniyah", "Sulaymaniyah"), ("duhok", "Duhok"), ("kirkuk", "Kirkuk"), ("anbar", "Anbar"),
    ("babil", "Babil"), ("karbala", "Karbala"), ("najaf", "Najaf"), ("diyala", "Diyala"),
    ("wasit", "Wasit"), ("saladin", "Saladin"), ("qadisiyyah", "Al-Qadisiyyah"), ("maysan", "Maysan"),
    ("dhi_qar", "Dhi Qar"), ("muthanna", "Al-Muthanna"), ("halabja", "Halabja"),
]


class LegalMinistry(models.Model):
    _name = "legal.ministry"
    _description = "Ministry / public authority"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, index=True, translate=False)
    code = fields.Char(string="Code")
    body_kind = fields.Selection(
        [
            ("ministry", "Ministry"),
            ("commission", "Independent commission"),
            ("judicial", "Judicial council"),
            ("governorate", "Governorate"),
            ("union", "Union or chamber"),
            ("other", "Other"),
        ],
        string="Kind",
        default="ministry",
    )
    website = fields.Char(string="Website")
    phone = fields.Char(string="Phone")
    address = fields.Text(string="Address")
    notes = fields.Text(string="Notes")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    governorate = fields.Selection(GOVERNORATES, string="Governorate")
    resource_calendar_id = fields.Many2one(
        "resource.calendar", string="Working calendar",
        help="Used for deadlines at this authority's departments that have no calendar of their own.")

    department_ids = fields.One2many("legal.department", "ministry_id", string="Departments")
    department_count = fields.Integer(string="Number of departments", compute="_compute_department_count")
    task_count = fields.Integer(string="Matters", compute="_compute_task_count")

    @api.constrains("name")
    def _check_unique_name(self):
        for record in self:
            key = normalize(record.name)
            if not key:
                continue
            others = self.with_context(active_test=False).search([("id", "!=", record.id)])
            if any(normalize(other.name) == key for other in others):
                raise ValidationError(_("A ministry or authority named “%s” already exists.", record.name.strip()))

    @api.depends("department_ids")
    def _compute_department_count(self):
        for record in self:
            record.department_count = len(record.department_ids)

    def _compute_task_count(self):
        groups = self.env["legal.task"]._read_group(
            [("ministry_id", "in", self.ids)], ["ministry_id"], ["__count"])
        counts = {ministry.id: count for ministry, count in groups}
        for record in self:
            record.task_count = counts.get(record.id, 0)

    def action_view_departments(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_department")
        action.update({
            "name": _("Departments of %s", self.name),
            "domain": [("ministry_id", "=", self.id)],
            "context": {"default_ministry_id": self.id},
        })
        return action

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({
            "name": _("Matters at %s", self.name),
            "domain": [("ministry_id", "=", self.id)],
            "context": {},
        })
        return action
