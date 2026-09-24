# -*- coding: utf-8 -*-
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .test_gov_common import GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovObligations(GovCase):

    def obligation(self, **values):
        vals = {"name": "Annual tax return", "legal_company_id": self.client_a.id, "template_id": self.t_service.id,
                "recurrence": "yearly", "month": 5, "day": 31, "lead_days": 30}
        vals.update(values)
        return self.env["legal.obligation"].create(vals)

    def test_next_date_is_computed_on_creation(self):
        ob = self.obligation()
        self.assertEqual((ob.next_date.month, ob.next_date.day), (5, 31))
        self.assertGreaterEqual(ob.next_date, self.today)
        self.assertEqual(ob.open_on, ob.next_date - timedelta(days=30))

    def test_short_month_uses_its_last_day(self):
        ob = self.obligation(recurrence="monthly", day=31, next_date=date(2027, 1, 31))
        self.assertEqual(ob._ldm_following(date(2027, 1, 31)), date(2027, 2, 28))
        self.assertEqual(ob._ldm_following(date(2027, 2, 28)), date(2027, 3, 31))
        yearly = self.obligation(month=2, day=29, next_date=date(2028, 2, 29))
        self.assertEqual(yearly._ldm_following(date(2028, 2, 29)), date(2029, 2, 28))

    def test_the_matter_opens_lead_days_before_and_the_date_rolls(self):
        due = self.today + timedelta(days=10)
        ob = self.obligation(next_date=due, month=due.month, day=due.day)
        Obligation = self.env["legal.obligation"]
        Obligation._cron_ldm_open_obligations()
        matter = self.env["legal.task"].search([("ldm_obligation_id", "=", ob.id)])
        self.assertEqual(len(matter), 1)
        self.assertEqual(matter.template_id, self.t_service)
        self.assertEqual(matter.legal_company_id, self.client_a)
        self.assertEqual(matter.due_date, due)
        self.assertEqual(matter.ldm_obligation_period, due)
        self.assertEqual(matter.lawyer_id, self.lawyer)
        self.assertNotIn(self.env.ref("base.user_root"), matter.lawyer_ids)
        self.assertTrue(matter.step_ids)
        self.assertEqual(ob.last_task_id, matter)
        self.assertEqual(ob.last_period_date, due)
        self.assertEqual(ob.next_date, due + relativedelta(years=1))
        Obligation._cron_ldm_open_obligations()
        self.assertEqual(self.env["legal.task"].search_count([("ldm_obligation_id", "=", ob.id)]), 1,
                         "The next period is not due yet: nothing more is opened")

    def test_a_period_is_never_opened_twice(self):
        due = self.today + timedelta(days=5)
        ob = self.obligation(next_date=due)
        self.env["legal.obligation"]._cron_ldm_open_obligations()
        ob.next_date = due  # someone puts the date back by hand
        self.env["legal.obligation"]._cron_ldm_open_obligations()
        self.assertEqual(self.env["legal.task"].search_count([("ldm_obligation_id", "=", ob.id)]), 1)

    def test_nothing_opens_before_the_lead_time(self):
        ob = self.obligation(next_date=self.today + timedelta(days=60))
        self.env["legal.obligation"]._cron_ldm_open_obligations()
        self.assertFalse(self.env["legal.task"].search([("ldm_obligation_id", "=", ob.id)]))

    def test_open_now_is_for_lawyers(self):
        ob = self.obligation(next_date=self.today + timedelta(days=90))
        action = ob.with_user(self.lawyer).action_ldm_open_now()
        self.assertEqual(action["res_model"], "legal.task")
        self.assertEqual(ob.task_count, 1)

    def test_schedule_is_checked(self):
        with self.assertRaises(ValidationError):
            self.obligation(month=13)
        with self.assertRaises(ValidationError):
            self.obligation(day=0)

    def test_an_obligation_without_a_type_reminds_the_client(self):
        ob = self.obligation(template_id=False, next_date=self.today + timedelta(days=5), lead_days=10)
        self.env["legal.obligation"]._cron_ldm_open_obligations()
        self.assertFalse(self.env["legal.task"].search([("ldm_obligation_id", "=", ob.id)]))
        Client = self.env["legal.company"]
        Client._ldm_run_company_reminders()
        Client._ldm_run_company_reminders()
        activity_type = self.env.ref("legal_department_management.ldm_activity_company_expiry")
        reminders = self.client_a.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type and ob.name in (a.summary or ""))
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders.date_deadline, ob.next_date)
