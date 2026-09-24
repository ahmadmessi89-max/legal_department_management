# -*- coding: utf-8 -*-
"""Ministries, government bodies and courts.

A clerk looks a body up by whatever name they know it by: its own, its
ministry's, a code, with or without hamza or taa marbuta. Each record keeps a
normalised search key so the picker finds "الهيئه العامه للضرائب" when the body
is stored as "الهيئة العامة للضرائب", and finds every department of "المالية"
when the ministry's name is typed.
"""
from odoo import _, api, fields, models
from odoo.fields import Domain

from .ldm_text import normalize, tokens


def _search_key(*parts):
    return normalize(" ".join(p for p in parts if p), drop_article=True)


def _key_domain(value):
    """Every word typed must appear in the key, in any order and spelling."""
    words = tokens(value)
    if not words:
        return Domain.FALSE
    return Domain.AND([Domain("ldm_search_key", "ilike", word) for word in words])


class LegalMinistry(models.Model):
    _inherit = "legal.ministry"

    ldm_search_key = fields.Char(compute="_compute_ldm_search_key", store=True, index=True,
                                 string="Search key")

    @api.depends("name", "code")
    def _compute_ldm_search_key(self):
        for ministry in self:
            ministry.ldm_search_key = _search_key(ministry.name, ministry.code)

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator in ("ilike", "like", "=ilike") and isinstance(value, str) and value.strip():
            domain = Domain(domain) | _key_domain(value)
        return domain


class LegalDepartment(models.Model):
    _inherit = "legal.department"
    _rec_names_search = ["name", "code", "ministry_id.name"]

    ldm_search_key = fields.Char(compute="_compute_ldm_search_key", store=True, index=True,
                                 string="Search key")
    template_count = fields.Integer(string="Number of services", compute="_compute_template_count")
    lower_court_ids = fields.One2many("legal.department", "parent_id", string="Courts below")

    @api.depends("name", "code", "ministry_id.name", "ministry_id.code")
    def _compute_ldm_search_key(self):
        for body in self:
            body.ldm_search_key = _search_key(body.name, body.code, body.ministry_id.name, body.ministry_id.code)

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator in ("ilike", "like", "=ilike") and isinstance(value, str) and value.strip():
            domain = Domain(domain) | _key_domain(value)
        return domain

    @api.depends_context("formatted_display_name")
    @api.depends("name", "ministry_id.name", "governorate")
    def _compute_display_name(self):
        """In a picker's dropdown the ministry (and the governorate of a court)
        shows as a second, muted line, so two bodies with the same name under
        different ministries can be told apart. Everywhere else the name alone."""
        formatted = self.env.context.get("formatted_display_name")
        governorates = dict(self._fields["governorate"]._description_selection(self.env)) if formatted else {}
        for body in self:
            name = body.name or ""
            if formatted:
                secondary = [body.ministry_id.name] if body.ministry_id else []
                if body.body_kind == "court" and body.governorate:
                    secondary.append(governorates.get(body.governorate))
                secondary = [s for s in secondary if s]
                if secondary:
                    name = f"{name}\n--{' · '.join(secondary)}--"
            body.display_name = name

    def _compute_template_count(self):
        groups = self.env["legal.task.template"]._read_group(
            [("department_id", "in", self.ids)], ["department_id"], ["__count"])
        counts = {body.id: count for body, count in groups}
        for body in self:
            body.template_count = counts.get(body.id, 0)

    @api.onchange("body_kind")
    def _onchange_body_kind(self):
        if self.body_kind != "court":
            self.court_degree = False
            self.parent_id = False

    def action_view_open_tasks(self):
        action = self.action_view_tasks()
        action["context"] = dict(action.get("context") or {}, search_default_filter_open=1)
        return action

    def action_view_templates(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_task_template")
        action.update({
            "name": _("Services at %s", self.name),
            "domain": [("department_id", "=", self.id)],
            "context": {"default_department_id": self.id, "default_kind": "government"},
        })
        return action
