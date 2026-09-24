# -*- coding: utf-8 -*-
"""The matter's litigation side: the court stage mirror and the reminders that
go to the legal managers."""
from odoo import _, api, fields, models

from .ldm_reminders import ldm_day, ldm_key


class LegalTask(models.Model):
    _inherit = "legal.task"

    ldm_session_to_record = fields.Boolean(
        string="A session is waiting to be recorded", compute="_compute_ldm_session_to_record",
        help="A planned court session whose day has come and whose outcome is not recorded yet.")

    @api.depends("hearing_ids.state", "hearing_ids.date")
    @api.depends_context("tz")
    def _compute_ldm_session_to_record(self):
        today = fields.Date.context_today(self)
        for task in self:
            task.ldm_session_to_record = bool(task.hearing_ids.filtered(
                lambda h: h.state == "planned" and h.date and h.date <= today))

    def action_ldm_record_outcome(self):
        """Record the outcome of the earliest planned session: the one that was
        held first and is still waiting to be written up."""
        self.ensure_one()
        hearing = self.hearing_ids.filtered(lambda h: h.state == "planned").sorted(lambda h: (h.date, h.time, h.id))[:1]
        if not hearing:
            return super().action_ldm_record_outcome()
        return hearing.action_ldm_record_outcome()

    def _ldm_sync_court_stage(self):
        """court_stage and court_case_number follow the latest court stage line."""
        for task in self:
            latest = task.court_stage_ids.sorted(lambda line: (line.sequence, line.id))[-1:]
            if not latest:
                continue
            values = {}
            if task.court_stage != latest.stage:
                values["court_stage"] = latest.stage
            number = latest._ldm_case_number()
            if number and task.court_case_number != number:
                values["court_case_number"] = number
            if values:
                task.write(values)

    @api.model
    def _ldm_reminder_items(self, company, today, horizon):
        """Add what the legal managers must hear about: tomorrow's sessions that
        nobody is attending, and our deadlines that end by the next working day
        and are still open (SPEC 8, escalation at T-1)."""
        items = super()._ldm_reminder_items(company, today, horizon)
        managers = self._ldm_managers(company)
        if not managers:
            return items
        next_day = company.ldm_add_working_days(today, 1)
        sessions = self.env["legal.hearing"].search([
            ("company_id", "=", company.id), ("state", "=", "planned"), ("date", ">", today),
            ("date", "<=", next_day), ("attending_user_id", "=", False), ("substitute_partner_id", "=", False)])
        for hearing in sessions:
            for manager in managers:
                env = self._ldm_reminder_env(manager)
                summary = env._(
                    "Nobody is attending the court session on %(date)s — %(number)s",
                    date=ldm_day(env, hearing.date, today), number=hearing.task_id.task_number)
                items.append((hearing.task_id, manager, hearing.date, summary, "ldm_activity_session",
                              ldm_key(hearing, "unattended")))
        deadlines = self.env["legal.deadline"].search([
            ("company_id", "=", company.id), ("state", "=", "open"), ("our_action", "=", True),
            ("rule_id", "!=", False), ("task_id", "!=", False), ("date_safe", "!=", False),
            ("date_safe", "<=", next_day)])
        for deadline in deadlines:
            owner = deadline.user_id or deadline.task_id.lawyer_id
            for manager in managers - owner:
                env = self._ldm_reminder_env(manager)
                summary = env._(
                    "Deadline about to end, still open: %(name)s — %(number)s",
                    name=deadline.with_env(env).name, number=deadline.task_id.task_number)
                items.append((deadline.task_id, manager, deadline.date_safe, summary, "ldm_activity_deadline",
                              ldm_key(deadline, "escalation")))
        return items

    def action_ldm_open_sessions(self):
        """The matter's court sessions on the calendar."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "legal_department_management.action_ldm_hearing_calendar")
        action.update({"domain": [("task_id", "=", self.id)], "name": _("Court sessions of %s", self.display_name),
                       "context": {"default_task_id": self.id, "default_department_id": self.department_id.id,
                                   "default_attending_user_id": self.lawyer_id.id}})
        return action
