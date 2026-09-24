# -*- coding: utf-8 -*-
"""Public holidays the legal manager enters. Each one is a global leave on the
legal working calendar; adding, moving or removing one recounts the open
deadlines and step due dates it touches and tells their owners."""
from datetime import date, datetime, time

import pytz
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date

from .lit_rules import ldm_date


class LegalHoliday(models.Model):
    _name = "legal.holiday"
    _inherit = ["legal.holiday", "mail.thread", "mail.activity.mixin"]

    # Translatable, so the holidays the module ships read in the user's
    # language; one a manager types is kept in the language it was typed in.
    name = fields.Char(translate=True)
    year = fields.Char(string="Year", compute="_compute_year", store=True)
    day_count = fields.Integer(string="Days", compute="_compute_day_count")
    weekday_from = fields.Char(string="Starts on", compute="_compute_day_count")

    @api.depends("date_from")
    def _compute_year(self):
        for holiday in self:
            holiday.year = str(holiday.date_from.year) if holiday.date_from else False

    @api.depends("date_from", "date_to")
    @api.depends_context("lang")
    def _compute_day_count(self):
        for holiday in self:
            holiday.day_count = ((holiday.date_to - holiday.date_from).days + 1
                                 if holiday.date_from and holiday.date_to else 0)
            holiday.weekday_from = (format_date(self.env, holiday.date_from, date_format="EEEE")
                                    if holiday.date_from else False)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for holiday in self:
            if holiday.date_to < holiday.date_from:
                raise ValidationError(_("A holiday cannot end before it starts."))

    @api.onchange("date_from")
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to < self.date_from):
            self.date_to = self.date_from

    # ------------------------------------------------------------------
    # CRUD: keep the calendar in step and recount what the change touches
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("date_from") and not vals.get("date_to"):
                vals["date_to"] = vals["date_from"]
        holidays = super().create(vals_list)
        for holiday in holidays.filtered(lambda h: not h.leave_id):
            holiday._ldm_sync_leave()
        if not self.env.context.get("install_mode"):
            holidays._ldm_apply([(h.date_from, h.date_to) for h in holidays], _("Public holiday added: %s",
                                ", ".join(holidays.mapped("name"))), added=True)
        return holidays

    def write(self, vals):
        before = [(h.date_from, h.date_to) for h in self]
        result = super().write(vals)
        if self.env.context.get("ldm_holiday_sync"):
            return result
        if {"name", "date_from", "date_to", "calendar_id"} & set(vals):
            for holiday in self:
                holiday._ldm_sync_leave()
        if {"date_from", "date_to", "calendar_id"} & set(vals):
            ranges = before + [(h.date_from, h.date_to) for h in self]
            self._ldm_apply(ranges, _("Public holiday changed: %s", ", ".join(self.mapped("name"))), added=True)
        return result

    def unlink(self):
        ranges = [(h.date_from, h.date_to) for h in self]
        names = ", ".join(self.mapped("name"))
        leaves = self.leave_id
        result = super().unlink()
        leaves.sudo().unlink()
        self.env["legal.holiday"]._ldm_apply(ranges, _("Public holiday removed: %s", names), added=False)
        return result

    def _ldm_sync_leave(self):
        """Write this holiday as a global leave (whole local days) on its calendar."""
        self.ensure_one()
        calendar = self.calendar_id
        tz = pytz.timezone(calendar.tz or "Asia/Baghdad")

        def utc(day, moment):
            return tz.localize(datetime.combine(day, moment)).astimezone(pytz.utc).replace(tzinfo=None)

        values = {
            "name": self.name,
            "calendar_id": calendar.id,
            "date_from": utc(self.date_from, time.min),
            "date_to": utc(self.date_to, time(23, 59, 59)),
            "resource_id": False,
            "time_type": "leave",
        }
        if self.leave_id:
            self.leave_id.sudo().write(values)
        else:
            leave = self.env["resource.calendar.leaves"].sudo().create(values)
            self.with_context(ldm_holiday_sync=True).write({"leave_id": leave.id})

    @api.model
    def _ldm_apply(self, ranges, reason, added=True):
        """Recount the open deadlines whose last day the change can move, and
        (when days were added) roll the open steps due on them to the next
        working day. One message per matter, to the people whose dates moved."""
        ranges = [(a, b) for a, b in ranges if a and b]
        if not ranges:
            return []
        first = min(a for a, _b in ranges)
        last = max(b for _a, b in ranges)
        Deadline = self.env["legal.deadline"].sudo()
        deadlines = Deadline.search([
            ("state", "=", "open"), ("rule_id", "!=", False), ("rule_id.extends_on_holiday", "=", True),
            ("date_safe", "<=", last), ("date_deadline", ">=", first),
        ])
        moves = deadlines._ldm_recompute_dates()
        step_moves = []
        if added:
            steps = self.env["legal.task.step"].sudo().search([
                ("state", "=", "todo"), ("date_due", ">=", first), ("date_due", "<=", last)])
            for step in steps:
                task = step.task_id
                calendar = task.department_id._ldm_calendar() if task.department_id else task.company_id._ldm_calendar()
                new_due = task.company_id.ldm_roll_forward(step.date_due, calendar)
                if new_due != step.date_due:
                    step_moves.append((step, step.date_due, new_due))
                    step.date_due = new_due
        self._ldm_notify(moves, step_moves, reason)
        return moves + step_moves

    @api.model
    def _ldm_notify(self, moves, step_moves, reason):
        Deadline = self.env["legal.deadline"]
        by_record = {}
        for deadline, old_safe, new_safe, old_legal, new_legal in moves:
            record = deadline.task_id or deadline
            owner = deadline.user_id or deadline.task_id.lawyer_id
            line = _("%(now)s (the legal last day was %(old)s)",
                     now=Deadline._ldm_describe(deadline, new_safe, new_legal),
                     old=ldm_date(self.env, old_legal) if old_legal else "-")
            by_record.setdefault(record, []).append((line, owner))
        for step, old_due, new_due in step_moves:
            owner = step.user_id or step.task_id.lawyer_id
            line = _("Step %(step)s: now due %(new)s (was %(old)s)", step=step.name,
                     new=ldm_date(self.env, new_due), old=ldm_date(self.env, old_due))
            by_record.setdefault(step.task_id, []).append((line, owner))
        for record, rows in by_record.items():
            partners = self.env["res.users"].browse([o.id for _l, o in rows if o]).filtered("active").partner_id
            body = Markup("<p>%s</p><ul>%s</ul>") % (
                reason, Markup("").join(Markup("<li>%s</li>") % line for line, _o in rows))
            record.sudo().message_post(body=body, partner_ids=partners.ids, message_type="comment",
                                       subtype_xmlid="mail.mt_note", author_id=self.env.user.partner_id.id)

    # ------------------------------------------------------------------
    # December reminder
    # ------------------------------------------------------------------
    @api.model
    def _cron_ldm_holiday_review(self, today=None):
        """Every December, ask the legal managers to enter or confirm next
        year's holidays: the Hijri ones move every year, and the endowment
        offices announce the Eid dates only shortly before."""
        today = today or fields.Date.context_today(self)
        if today.month != 12:
            return False
        next_year = today.year + 1
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        for company in self.env["res.company"].search([]):
            calendar = company._ldm_calendar()
            anchor = self.search([("calendar_id", "=", calendar.id)], order="date_from desc", limit=1)
            if not anchor:
                continue
            for manager in self.env["legal.task"]._ldm_managers(company):
                done = anchor.activity_ids.filtered(
                    lambda a: a.user_id == manager and str(next_year) in (a.summary or ""))
                if done:
                    continue
                lang_self = self.with_context(lang=manager.lang or "en_US")
                anchor.activity_schedule(
                    activity_type_id=todo.id if todo else False,
                    summary=lang_self.env._("Enter the public holidays for %s", next_year),
                    note=lang_self.env._("Check the Eid dates announced by the endowment offices and any days "
                                         "the Council of Ministers added, then mark them as confirmed."),
                    user_id=manager.id,
                    date_deadline=date(today.year, 12, 31))
        return True
