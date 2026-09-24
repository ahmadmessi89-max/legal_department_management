# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta

import pytz

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ldm_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Legal working calendar",
        help="Working days and public holidays used to count legal deadlines and step offsets. "
        "When empty, the company's own working calendar is used.",
    )
    ldm_approval_sod = fields.Boolean(
        string="Requester may not approve",
        default=True,
        help="The person who sent a matter for approval cannot approve it themselves.",
    )
    ldm_conflict_policy = fields.Selection(
        [("warn", "Warn, a manager may override"), ("block", "Block")],
        string="Conflict of interest",
        default="warn",
        required=True,
    )
    ldm_fee_cap_check = fields.Boolean(
        string="Check the 20% fee cap",
        default=True,
        help="Advocacy Law 173 of 1965, Art. 56: fees may not exceed 20% of the matter's value, "
        "except in criminal matters.",
    )
    ldm_reminder_days = fields.Integer(string="Remind before (working days)", default=3)
    ldm_poa_warning_days = fields.Integer(string="Warn before a power of attorney expires (days)", default=30)
    ldm_engagement_required = fields.Boolean(
        string="Warn when a matter has no signed fee agreement",
        help="Law office: a matter that starts work without a signed fee agreement is flagged. "
        "Advocacy Law Art. 65: fee claims without a written agreement lapse after 3 years.")
    ldm_retainer_min_local = fields.Monetary(
        string="Minimum monthly retainer (local company)", currency_field="currency_id", default=300000,
        help="Iraqi Bar administrative order 3021 of 2021. Verify the current amount.")
    ldm_retainer_min_foreign = fields.Monetary(
        string="Minimum monthly retainer (foreign company)", currency_field="currency_id", default=600000,
        help="Iraqi Bar administrative order 3021 of 2021. Verify the current amount.")

    # ------------------------------------------------------------------
    # Working-day arithmetic, used by every clock in the module
    # ------------------------------------------------------------------
    def _ldm_calendar(self):
        self.ensure_one()
        return self.ldm_calendar_id or self.resource_calendar_id

    @api.model
    def _ldm_working_days(self, calendar, first, last):
        """Set of dates between ``first`` and ``last`` (inclusive) on which
        ``calendar`` has working time once its public holidays are applied.
        One interval query for the whole range."""
        tz = pytz.timezone(calendar.tz or "Asia/Baghdad")
        start = tz.localize(datetime.combine(first, time.min))
        end = tz.localize(datetime.combine(last, time.max))
        intervals = calendar._work_intervals_batch(start, end)[False]
        days = set()
        for begin, stop, _meta in intervals:
            days.add(begin.astimezone(tz).date())
            days.add((stop - timedelta(seconds=1)).astimezone(tz).date())
        return days

    def ldm_add_working_days(self, start, days, calendar=None):
        """Return the date ``days`` working days after ``start`` (before it when negative).

        Counting starts the day after ``start``: CCP Art. 25(1) does not count the
        start day. Falls back to calendar days when no working calendar is set, so
        a company configured in a hurry still gets a usable date.
        """
        self.ensure_one()
        if not start:
            return False
        if not days:
            return start
        calendar = calendar or self._ldm_calendar()
        if not calendar:
            return start + timedelta(days=days)
        step = 1 if days > 0 else -1
        # Wide enough for any legal period: two calendar days per working day plus holidays.
        span = abs(days) * 2 + 40
        first, last = sorted([start + timedelta(days=step), start + timedelta(days=step * span)])
        working = self._ldm_working_days(calendar, first, last)
        remaining = abs(days)
        current = start
        for _guard in range(span):
            current = current + timedelta(days=step)
            if current in working:
                remaining -= 1
                if remaining == 0:
                    return current
        return start + timedelta(days=days)

    def ldm_roll_forward(self, day, calendar=None):
        """``day`` if it is a working day, else the next working day (CCP Art. 25(2))."""
        self.ensure_one()
        if not day:
            return False
        calendar = calendar or self._ldm_calendar()
        if not calendar:
            return day
        working = self._ldm_working_days(calendar, day, day + timedelta(days=40))
        current = day
        for _guard in range(41):
            if current in working:
                return current
            current = current + timedelta(days=1)
        return day

    def ldm_statutory_dates(self, event_date, period, unit="days", calendar=None, extends_on_holiday=True,
                            max_months=0, cap_from=None):
        """Dates of a statutory period that starts on ``event_date``.

        Iraqi challenge periods are calendar days, not working days. The event
        day itself is not counted (CCP Art. 25(1)), so a 15-day period from a
        notification on the 1st ends on the 16th. Only a last day that falls on
        a holiday moves, to the next working day (Art. 25(2)).

        Returns ``(date_safe, date_deadline)``: the unmoved last day, which is the
        date to act by, and the legal last day after the holiday roll. With
        ``max_months`` the period can never end later than that many months after
        ``cap_from`` (e.g. correction of a cassation decision, Art. 221).
        """
        self.ensure_one()
        if not event_date or not period:
            return False, False
        if unit == "months":
            last = event_date + relativedelta(months=period)
        else:
            last = event_date + timedelta(days=period)
        if max_months:
            cap = (cap_from or event_date) + relativedelta(months=max_months)
            last = min(last, cap)
        deadline = self.ldm_roll_forward(last, calendar) if extends_on_holiday else last
        return last, deadline

    def ldm_is_working_day(self, day, calendar=None):
        self.ensure_one()
        calendar = calendar or self._ldm_calendar()
        if not calendar or not day:
            return True
        return day in self._ldm_working_days(calendar, day, day)
