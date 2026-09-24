# -*- coding: utf-8 -*-
"""Reminders for the registers: powers of attorney about to expire, letters
waiting for an answer, letters of guarantee about to expire.

The foundation's reminder loop (``legal.task._ldm_run_reminders``) expects a
matter as the first element of every item. Register records are not matters,
so their items are produced by ``_ldm_reg_reminder_items`` and run through the
same one-reminder-per-(record, person, kind, subject) rule right after the
foundation's loop. A letter that belongs to a matter is reminded through its
deadline on that matter (the foundation already reminds matter deadlines), so
only letters without a matter get a reminder of their own here.
"""
from datetime import timedelta

from odoo import _, api, fields, models

from .reg_common import ensure_activity
from .reg_guarantee import GUARANTEE_WARNING_DAYS, LIVE_STATES


class LegalTask(models.Model):
    _inherit = "legal.task"

    @api.model
    def _ldm_run_reminders(self):
        result = super()._ldm_run_reminders()
        for company in self.env["res.company"].search([]):
            calendar = company._ldm_calendar()
            tz = (calendar and calendar.tz) or "Asia/Baghdad"
            today = fields.Date.context_today(self.with_context(tz=tz))
            horizon = company.ldm_add_working_days(today, company.ldm_reminder_days or 3)
            for record, user, date, summary, type_xmlid in self.with_company(company)._ldm_reg_reminder_items(
                    company, today, horizon):
                user = user if user and user.active and not user.share else self._ldm_managers(company)[:1]
                if user:
                    ensure_activity(record, user, date, summary, type_xmlid)
        return result

    @api.model
    def _ldm_reg_reminder_items(self, company, today, horizon):
        """(record, user, date, summary, activity type xmlid) for the registers."""
        items = []
        warn = company.ldm_poa_warning_days or 30
        for poa in self.env["legal.poa"].search([("company_id", "=", company.id), ("state", "=", "active"),
                                                 ("date_expiry", "!=", False),
                                                 ("date_expiry", "<=", today + timedelta(days=warn))]):
            items.append((poa, poa._ldm_responsible(), poa.date_expiry,
                          _("Power of attorney expires — %s", poa.name), "ldm_activity_poa_expiry"))
        for letter in self.env["legal.correspondence"].search([
                ("company_id", "=", company.id), ("state", "=", "registered"), ("task_id", "=", False),
                ("reply_done", "=", False), ("reply_due_date", "!=", False), ("reply_due_date", "<=", horizon)]):
            summary = (_("Answer letter %s", letter.display_name) if letter.direction == "incoming"
                       else _("Chase the answer to letter %s", letter.display_name))
            items.append((letter, letter._ldm_owner(), letter.reply_due_date, summary, "ldm_activity_letter_reply"))
        soon = today + timedelta(days=GUARANTEE_WARNING_DAYS)
        for guarantee in self.env["legal.guarantee"].search([
                ("company_id", "=", company.id), ("state", "in", LIVE_STATES), ("date_expiry", "!=", False),
                ("date_expiry", "<=", soon)]):
            items.append((guarantee, guarantee._ldm_responsible(), guarantee.date_expiry,
                          _("Letter of guarantee expires — %s", guarantee.name), "ldm_activity_guarantee_expiry"))
        return items
