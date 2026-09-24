# -*- coding: utf-8 -*-
import base64
import re

from odoo import api, fields, models
from odoo.tools import html_escape

from .ldm_text import initial

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

    def write(self, vals):
        result = super().write(vals)
        if "name" in vals:
            self._ldm_refresh_letter_avatars(self)
        return result

    @api.model
    def _ldm_refresh_letter_avatars(self, users=None):
        """Odoo draws an internal user's letter avatar once, when the user is
        created, stores it, and keeps it when the name changes. Redraw the
        stored letter avatars whose letter is not the one that names the user;
        photos and other pictures are never touched. Idempotent: runs on every
        install and upgrade (all users) and after a rename (those users)."""
        letter_in = re.compile(rb"^\s*(?:<\?xml[^>]*>)?\s*<svg[^>]*><rect [^>]*/><text [^>]*>([^<]*)</text></svg>\s*$")
        if users is None:
            users = self.with_context(active_test=False).search([("share", "=", False)])
        for user in users.sudo().filtered(lambda u: not u.share and u.image_1920):
            try:
                drawn = letter_in.match(base64.b64decode(user.image_1920))
            except ValueError:
                continue
            if drawn and drawn.group(1).decode() != str(html_escape(initial(user.name))):
                user.image_1920 = user.partner_id._avatar_generate_svg()


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _avatar_generate_svg(self):
        """Odoo's letter avatar, with the letter that names the person: a title
        (المحامية، المستشار، د.) or the Arabic article before the name would give
        most of a legal team the same "ا". Odoo's colour is kept."""
        svg = super()._avatar_generate_svg()
        name = self[self._avatar_name_field] or ""
        letter = initial(name)
        if not name or letter == name[:1].upper():
            return svg
        old, new = (f">{html_escape(c)}</text>".encode() for c in (name[:1].upper(), letter))
        return base64.b64encode(base64.b64decode(svg).replace(old, new, 1))


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    ldm_show_advanced = fields.Boolean(string="Show all fields on legal forms")
    ldm_recent_template_ids = fields.Many2many("legal.task.template", "ldm_users_settings_recent_template_rel",
                                               "settings_id", "template_id", string="Recent matter types")
