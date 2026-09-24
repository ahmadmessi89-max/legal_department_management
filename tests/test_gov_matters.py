# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo.tests import tagged

from .test_gov_common import GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovMatters(GovCase):

    def test_target_days_come_from_the_type_then_the_body(self):
        matter = self.gov_matter()
        self.assertEqual(matter.ldm_target_days, 5, "The type has none, so the body's usual time applies")
        self.t_service.target_days = 12
        self.assertEqual(matter.ldm_target_days, 12)

    def test_past_target_filter_and_domain(self):
        late = self.gov_matter()
        on_time = self.gov_matter()
        not_submitted = self.gov_matter()
        late.with_user(self.lawyer).write({"waiting_on": "body", "date_submitted": self.today - timedelta(days=30)})
        on_time.with_user(self.lawyer).write({"waiting_on": "body", "date_submitted": self.today - timedelta(days=1)})
        self.assertTrue(late.ldm_body_due_date)
        self.assertLess(late.ldm_body_due_date, self.today)
        self.assertGreater(late.days_at_body, 5)
        Task = self.env["legal.task"].with_user(self.lawyer)
        found = Task.search(Task._ldm_past_target_domain())
        self.assertIn(late, found)
        self.assertNotIn(on_time, found)
        self.assertNotIn(not_submitted, found)
        self.assertEqual(Task.search([("ldm_past_target", "=", True), ("id", "in", (late | on_time).ids)]), late)
        self.assertTrue(late.ldm_past_target)
        self.assertFalse(on_time.ldm_past_target)
        late.with_user(self.lawyer).write({"waiting_on": "us"})
        self.assertFalse(late.ldm_body_due_date, "Back with us: no answer is expected from the body")

    def test_filter_exists_in_the_search_view(self):
        arch = self.env["legal.task"].with_user(self.lawyer).get_views([(False, "search")])["views"]["search"]["arch"]
        self.assertIn("filter_past_target", arch)

    def test_expiring_documents_are_reminded_on_the_matter(self):
        matter = self.gov_matter()
        card = matter.document_ids.filtered(lambda d: d.document_type_id == self.dt_card)
        card.write({"state": "received", "expiry_date": self.today + timedelta(days=1)})
        Task = self.env["legal.task"]
        items = Task._ldm_reminder_items(self.company, self.today, self.today + timedelta(days=3))
        mine = [i for i in items if i[0] == matter and i[4] == "ldm_activity_expiry"]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0][2], card.expiry_date)
        expiry_type = self.env.ref("legal_department_management.ldm_activity_expiry")
        Task._ldm_run_reminders()
        Task._ldm_run_reminders()
        activities = matter.activity_ids.filtered(lambda a: a.activity_type_id == expiry_type)
        self.assertEqual(len(activities), 1, "Running the reminders twice changes nothing")
        self.assertEqual(activities.user_id, self.lawyer)

    def test_log_visit_button_in_the_cockpit(self):
        arch = self.env["legal.task"].with_user(self.clerk).get_views([(False, "form")])["views"]["form"]["arch"]
        self.assertIn("action_ldm_log_visit", arch)
        auditor_arch = self.env["legal.task"].with_user(self.auditor).get_views([(False, "form")])["views"]["form"]["arch"]
        self.assertNotIn("action_ldm_log_visit", auditor_arch)
        self.assertNotIn("action_ldm_take_from_vault", auditor_arch)
