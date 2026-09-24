# -*- coding: utf-8 -*-
"""Letters of guarantee (خطابات الضمان): a deadline 30 days before expiry, the
extension request to the bank, the extension itself and the release, each
letter drafted from a template."""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .reg_common import close_activities, sync_deadline

GUARANTEE_WARNING_DAYS = 30
LIVE_STATES = ("active", "extension_requested", "extended")


class LegalGuarantee(models.Model):
    _name = "legal.guarantee"
    _inherit = ["legal.guarantee", "ldm.reg.scan.mixin"]

    days_to_expiry = fields.Integer(string="Days left", compute="_compute_days_to_expiry")
    is_expiring = fields.Boolean(string="Expires within 30 days", compute="_compute_days_to_expiry",
                                 search="_search_is_expiring")
    release_date = fields.Date(string="Released on", readonly=True, copy=False)
    correspondence_ids = fields.One2many("legal.correspondence", "guarantee_id", string="Letters")

    @api.depends("date_expiry", "state")
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for guarantee in self:
            guarantee.days_to_expiry = (guarantee.date_expiry - today).days if guarantee.date_expiry else 0
            guarantee.is_expiring = bool(guarantee.state in LIVE_STATES and guarantee.date_expiry
                                         and guarantee.days_to_expiry <= GUARANTEE_WARNING_DAYS)

    def _search_is_expiring(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        soon = fields.Date.context_today(self) + timedelta(days=GUARANTEE_WARNING_DAYS)
        domain = [("state", "in", LIVE_STATES), ("date_expiry", "!=", False), ("date_expiry", "<=", soon)]
        positive = (operator == "=") == value
        return domain if positive else ["!", "&", "&"] + domain

    @api.model_create_multi
    def create(self, vals_list):
        guarantees = super().create(vals_list)
        guarantees._ldm_sync_expiry()
        return guarantees

    def write(self, vals):
        result = super().write(vals)
        if {"date_expiry", "state", "legal_company_id", "task_id"} & set(vals) and not self.env.context.get(
                "ldm_guarantee_syncing"):
            self._ldm_sync_expiry()
        return result

    def _ldm_responsible(self):
        self.ensure_one()
        user = self.task_id.lawyer_id or self.legal_company_id.lawyer_id or self.create_uid
        return user if user.active and not user.share else self.env["res.users"]

    def _ldm_sync_expiry(self):
        today = fields.Date.context_today(self)
        for guarantee in self.with_context(ldm_guarantee_syncing=True):
            if guarantee.state in LIVE_STATES and guarantee.date_expiry and guarantee.date_expiry < today:
                guarantee.write({"state": "expired"})
                guarantee.message_post(body=_("This letter of guarantee expired on %s.", guarantee.date_expiry))
            if guarantee.state in LIVE_STATES and guarantee.date_expiry and \
                    guarantee.date_expiry <= today + timedelta(days=GUARANTEE_WARNING_DAYS):
                sync_deadline(guarantee, "expiry", {
                    "name": _("Letter of guarantee expires: %s", guarantee.name),
                    "date_safe": guarantee.date_expiry,
                    "date_deadline": guarantee.date_expiry,
                    "task_id": guarantee.task_id.id or False,
                    "legal_company_id": guarantee.legal_company_id.id or False,
                    "company_id": guarantee.company_id.id,
                    "user_id": guarantee._ldm_responsible().id or False,
                })
            else:
                close = "done" if guarantee.state in ("released", "extended", "active") else (
                    "cancelled" if guarantee.state == "liquidated" else None)
                sync_deadline(guarantee, "expiry", None, close_state=close)
                if guarantee.state not in LIVE_STATES:
                    close_activities(guarantee, "ldm_activity_guarantee_expiry")

    @api.model
    def _cron_ldm_guarantee_expiry(self):
        soon = fields.Date.context_today(self) + timedelta(days=GUARANTEE_WARNING_DAYS)
        self.search([("state", "in", LIVE_STATES), ("date_expiry", "!=", False),
                     ("date_expiry", "<=", soon)])._ldm_sync_expiry()
        return True

    # ------------------------------------------------------------------
    # Actions: each opens the same small dialog in its own mode
    # ------------------------------------------------------------------
    def _ldm_open_wizard(self, mode, title):
        self.ensure_one()
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise AccessError(_("Only a lawyer can act on a letter of guarantee."))
        if self.state not in LIVE_STATES:
            raise UserError(_("%s is no longer live.", self.display_name))
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "legal.guarantee.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_guarantee_id": self.id, "default_mode": mode},
        }

    def action_ldm_request_extension(self):
        return self._ldm_open_wizard("request_extension", _("Ask the bank to extend"))

    def action_ldm_extend(self):
        return self._ldm_open_wizard("extend", _("Record the extension"))

    def action_ldm_release(self):
        return self._ldm_open_wizard("release", _("Release the letter of guarantee"))

    def action_ldm_view_letters(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_correspondence")
        action.update({"name": _("Letters about %s", self.name), "domain": [("guarantee_id", "=", self.id)],
                       "context": {"default_guarantee_id": self.id}})
        return action
