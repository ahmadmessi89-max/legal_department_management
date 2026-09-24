# -*- coding: utf-8 -*-
from odoo import fields, models

# Iraqi Bar Association classes of appearance rights, in the order a lawyer
# progresses through them (Bar Council decision of 15 June 2022):
# trainee (متمرن), then A, B, C, then unrestricted (مطلقة).
LICENCE_CLASSES = [
    ("trainee", "Trainee"),
    ("a", "Class A"),
    ("b", "Class B"),
    ("c", "Class C"),
    ("unrestricted", "Unrestricted"),
]


class ResUsers(models.Model):
    _inherit = "res.users"

    ldm_bar_number = fields.Char(string="Bar membership number")
    ldm_licence_class = fields.Selection(LICENCE_CLASSES, string="Licence class")
    ldm_licence_date = fields.Date(string="Licence class since")
    ldm_training_path = fields.Selection([("training", "Training"), ("graduated", "Graduated path")],
                                         string="Training path")
    ldm_supervisor_id = fields.Many2one("res.users", string="Training supervisor")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["ldm_bar_number", "ldm_licence_class", "ldm_licence_date",
                                              "ldm_training_path", "ldm_supervisor_id"]


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    ldm_show_advanced = fields.Boolean(string="Show all fields on legal forms")
    ldm_recent_template_ids = fields.Many2many("legal.task.template", "ldm_users_settings_recent_template_rel",
                                               "settings_id", "template_id", string="Recent matter types")
