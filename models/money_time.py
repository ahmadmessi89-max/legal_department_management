# -*- coding: utf-8 -*-
"""Time entries, their approval, and the server side of the top-bar timer.

The timer's state lives on the user's settings record (which matter, since
when) so it survives a reload and follows the user to another device. It is
stored as a plain id, not a relation, so that loading the web client never
reads a matter the user can no longer open.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .ldm_engine import engine_guard, in_engine

MANAGER = "legal_department_management.group_legal_manager"
BILLING = "legal_department_management.group_ldm_billing_user"
TIME_GROUP = "legal_department_management.group_ldm_time"


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    ldm_timer_task_ref = fields.Integer(aggregator=None, string="Timer running on matter")
    ldm_timer_start = fields.Datetime(string="Timer started at")

    @api.model
    def _get_fields_blacklist(self):
        return super()._get_fields_blacklist() + ["ldm_timer_task_ref", "ldm_timer_start"]


class LegalTimeEntry(models.Model):
    _inherit = "legal.time.entry"

    engagement_id = fields.Many2one(related="task_id.engagement_id", string="Fee agreement")
    ldm_can_approve = fields.Boolean(compute="_compute_ldm_can_approve")

    @api.depends_context("uid")
    @api.depends("state", "task_id.lawyer_id", "user_id")
    def _compute_ldm_can_approve(self):
        for entry in self:
            entry.ldm_can_approve = entry._ldm_may_approve()

    def _ldm_may_approve(self):
        user = self.env.user
        if self.env.su or user.has_group(MANAGER) or user.has_group(BILLING):
            return True
        return all(entry.task_id.lawyer_id == user and entry.user_id != user for entry in self)

    @api.onchange("task_id")
    def _onchange_task_rate(self):
        engagement = self.task_id.engagement_id
        if engagement.hourly_rate and not self.rate:
            self.rate = engagement.hourly_rate
            self.currency_id = engagement.currency_id

    @api.constrains("duration")
    def _check_duration(self):
        for entry in self:
            if entry.duration <= 0 or entry.duration > 24:
                raise ValidationError(_("A time entry must be more than zero and at most 24 hours."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("task_id") and not vals.get("rate"):
                engagement = self.env["legal.task"].browse(vals["task_id"]).engagement_id
                if engagement.hourly_rate:
                    vals["rate"] = engagement.hourly_rate
                    vals["currency_id"] = engagement.currency_id.id
            if not (self.env.su or in_engine()) and vals.get("state", "draft") != "draft":
                vals["state"] = "draft"
        return super().create(vals_list)

    def write(self, vals):
        if not (self.env.su or in_engine()):
            if any(e.state == "invoiced" for e in self) and set(vals) - {"description"}:
                raise UserError(_("Invoiced time can no longer change."))
            if "state" in vals and not in_engine():
                raise UserError(_("Use Approve to approve time."))
            if any(e.state == "approved" for e in self) and {"duration", "rate", "billable", "task_id"} & set(vals) \
                    and not self._ldm_may_approve():
                raise UserError(_("This time is approved; ask whoever approved it to change it."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            if any(e.state != "draft" for e in self):
                raise UserError(_("Only draft time can be deleted."))
            if any(e.user_id != self.env.user for e in self) and not self.env.user.has_group(MANAGER):
                raise UserError(_("You can only delete your own time."))
        return super().unlink()

    def action_ldm_approve(self):
        entries = self.filtered(lambda e: e.state == "draft")
        if not entries._ldm_may_approve():
            raise AccessError(_("The matter's responsible lawyer, a legal manager or billing approves time."))
        with engine_guard():
            entries.write({"state": "approved"})
        return True

    def action_ldm_reset(self):
        entries = self.filtered(lambda e: e.state == "approved")
        if not entries._ldm_may_approve():
            raise AccessError(_("The matter's responsible lawyer, a legal manager or billing approves time."))
        with engine_guard():
            entries.write({"state": "draft"})
        return True

    # ------------------------------------------------------------------
    # Timer (called by static/src/money/timer_systray.js)
    # ------------------------------------------------------------------
    @api.model
    def _ldm_timer_settings(self):
        if not self.env.user.has_group(TIME_GROUP):
            raise AccessError(_("Time tracking is switched off."))
        return self.env["res.users.settings"]._find_or_create_for_user(self.env.user)

    @api.model
    def ldm_timer_state(self):
        """``{"running": bool, "task_id", "task_name", "started", "elapsed"}`` (elapsed in seconds)."""
        if not self.env.user.has_group(TIME_GROUP):
            return {"running": False, "enabled": False}
        settings = self._ldm_timer_settings()
        task = self.env["legal.task"].browse(settings.ldm_timer_task_ref).exists()
        if not task or not settings.ldm_timer_start:
            return {"running": False, "enabled": True}
        try:
            task.check_access("read")
            name = task.display_name
        except AccessError:
            name = _("A matter you can no longer open")
        elapsed = (fields.Datetime.now() - settings.ldm_timer_start).total_seconds()
        return {"running": True, "enabled": True, "task_id": task.id, "task_name": name,
                "started": fields.Datetime.to_string(settings.ldm_timer_start), "elapsed": max(0, int(elapsed))}

    @api.model
    def ldm_timer_start(self, task_id):
        settings = self._ldm_timer_settings()
        task = self.env["legal.task"].browse(task_id).exists()
        if not task:
            raise UserError(_("Open a matter to start the timer on it."))
        task.check_access("read")
        running = self.env["legal.task"].browse(settings.ldm_timer_task_ref).exists()
        if running and settings.ldm_timer_start and running != task:
            raise UserError(_("The timer is already running on %s. Stop it first.", running.sudo().display_name))
        if not settings.ldm_timer_start:
            settings.write({"ldm_timer_task_ref": task.id, "ldm_timer_start": fields.Datetime.now()})
        return self.ldm_timer_state()

    @api.model
    def ldm_timer_stop(self, description, billable=True, duration=None):
        """Turn the running timer into a time entry. ``duration`` (hours) replaces
        the measured time when the user corrected it in the dialog."""
        settings = self._ldm_timer_settings()
        task = self.env["legal.task"].browse(settings.ldm_timer_task_ref).exists()
        if not task or not settings.ldm_timer_start:
            raise UserError(_("The timer is not running."))
        if not (description or "").strip():
            raise UserError(_("Say what was done."))
        if duration is None:
            seconds = (fields.Datetime.now() - settings.ldm_timer_start).total_seconds()
            duration = max(round(seconds / 3600.0, 2), 0.01)
        entry = self.create({
            "task_id": task.id, "user_id": self.env.uid, "date": fields.Date.context_today(self),
            "duration": duration, "description": description.strip(), "billable": bool(billable),
        })
        settings.write({"ldm_timer_task_ref": 0, "ldm_timer_start": False})
        return {"id": entry.id, "duration": entry.duration, "task_name": task.display_name}

    @api.model
    def ldm_timer_discard(self):
        settings = self._ldm_timer_settings()
        settings.write({"ldm_timer_task_ref": 0, "ldm_timer_start": False})
        return True

    @api.model
    def ldm_timer_recent_matters(self, limit=7):
        """The user's open matters, most recently changed first, to start the timer on."""
        tasks = self.env["legal.task"].search(
            [("state", "in", ("draft", "in_progress", "pending_docs")),
             "|", ("lawyer_id", "=", self.env.uid), ("lawyer_ids", "in", [self.env.uid])],
            order="write_date desc", limit=limit)
        return [{"id": t.id, "name": t.display_name, "client": t.legal_company_id.display_name} for t in tasks]
