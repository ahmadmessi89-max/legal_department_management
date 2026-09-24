# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .lit_common import LitCase


@tagged("post_install", "-at_install", "ldm")
class TestLitHolidays(LitCase):
    """Holidays entered by the manager move the deadlines and steps they touch."""

    def comments(self, record):
        return self.env["mail.message"].search([("model", "=", record._name), ("res_id", "=", record.id),
                                                ("message_type", "=", "comment")])

    def test_shipped_holidays_are_linked_to_the_calendar(self):
        holidays = self.env["legal.holiday"].search([("calendar_id", "=", self.calendar.id)])
        self.assertGreaterEqual(len(holidays), 22)
        eid = self.env.ref("legal_department_management.ldm_legal_holiday_2026_07")
        self.assertEqual(eid.leave_id, self.env.ref("legal_department_management.ldm_holiday_2026_07"))
        self.assertTrue(eid.estimated)
        self.assertEqual(eid.day_count, 4)
        self.assertEqual(eid.year, "2026")

    def test_a_holiday_on_the_last_day_moves_the_deadline_and_tells_the_lawyer(self):
        deadline = self.env["legal.deadline"].create({"task_id": self.lawsuit.id, "rule_id": self.rule("civ_2").id,
                                                      "date_start": self.d("2026-10-01")})
        self.assertEqual(deadline.date_deadline, self.d("2026-10-18"))
        before = len(self.comments(self.lawsuit))
        holiday = self.env["legal.holiday"].with_user(self.manager).create({
            "name": "Day of mourning", "date_from": self.d("2026-10-18")})
        self.assertEqual(holiday.date_to, self.d("2026-10-18"))
        self.assertTrue(holiday.leave_id)
        self.assertEqual(holiday.leave_id.calendar_id, self.calendar)
        self.assertFalse(self.company.ldm_is_working_day(self.d("2026-10-18")))
        self.assertEqual(deadline.date_safe, self.d("2026-10-16"), "the act-by date never moves")
        self.assertEqual(deadline.date_deadline, self.d("2026-10-19"))
        messages = self.comments(self.lawsuit)
        self.assertEqual(len(messages), before + 1)
        self.assertIn(self.lawyer.partner_id, messages[0].partner_ids)
        # Moving the holiday away gives the day back.
        holiday.with_user(self.manager).write({"date_from": self.d("2026-10-25"), "date_to": self.d("2026-10-25")})
        self.assertEqual(deadline.date_deadline, self.d("2026-10-18"))
        self.assertTrue(self.company.ldm_is_working_day(self.d("2026-10-18")))
        # Removing it altogether leaves the calendar as it was.
        leave = holiday.leave_id
        holiday.with_user(self.manager).unlink()
        self.assertFalse(leave.exists())
        self.assertTrue(self.company.ldm_is_working_day(self.d("2026-10-25")))

    def test_a_new_holiday_moves_open_steps_due_on_it(self):
        step = self.env["legal.task.step"].create({"task_id": self.lawsuit.id, "name": "File the memorandum",
                                                   "date_due": self.d("2026-10-21"), "user_id": self.lawyer.id})
        self.env["legal.holiday"].create({"name": "Extra holiday", "date_from": self.d("2026-10-21"),
                                          "date_to": self.d("2026-10-22")})
        # Wednesday and Thursday off: the next working day is Sunday 25 October.
        self.assertEqual(step.date_due, self.d("2026-10-25"))

    def test_only_managers_edit_holidays(self):
        with self.assertRaises(AccessError):
            self.env["legal.holiday"].with_user(self.lawyer).create({"name": "Not mine",
                                                                     "date_from": self.d("2026-10-21")})
        with self.assertRaises(ValidationError):
            self.env["legal.holiday"].create({"name": "Backwards", "date_from": self.d("2026-10-21"),
                                              "date_to": self.d("2026-10-20")})

    def test_december_reminder_to_review_next_year(self):
        Holiday = self.env["legal.holiday"]
        self.assertFalse(Holiday._cron_ldm_holiday_review(today=self.d("2026-11-30")))
        Holiday._cron_ldm_holiday_review(today=self.d("2026-12-01"))
        anchor = Holiday.search([("calendar_id", "=", self.calendar.id)], order="date_from desc", limit=1)
        reminders = anchor.activity_ids.filtered(lambda a: a.user_id == self.manager)
        self.assertEqual(len(reminders), 1)
        self.assertIn("2027", reminders.summary)
        Holiday._cron_ldm_holiday_review(today=self.d("2026-12-02"))
        self.assertEqual(len(anchor.activity_ids.filtered(lambda a: a.user_id == self.manager)), 1)
