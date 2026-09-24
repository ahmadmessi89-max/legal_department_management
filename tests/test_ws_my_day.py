# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import M
from .ws_common import WsCase


@tagged("post_install", "-at_install", "ldm")
class TestWsMyDay(WsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The lawyer's matter: a late step, a session today, a deadline this week.
        cls.suit = cls.open_matter(name="Supply contract claim", kind="litigation", department_id=cls.court.id)
        cls.late_step = cls.step(cls.suit, "Draft the petition", -2)
        cls.later_step = cls.step(cls.suit, "Pay the court fee", 9)
        cls.session = cls.Hearing.create({"task_id": cls.suit.id, "date": cls.today, "time": 10.0,
                                          "attending_user_id": cls.lawyer.id})
        cls.deadline = cls.Deadline.create({"task_id": cls.suit.id, "name": "Reply due", "date_safe": cls.day(3),
                                            "user_id": cls.lawyer.id, "company_id": cls.company.id})
        # A government matter whose counter visits the clerk runs.
        cls.gov = cls.open_matter(name="Tax clearance", kind="government", department_id=cls.registry_body.id,
                                  lawyer_ids=[(6, 0, [cls.lawyer.id, cls.clerk.id])])
        cls.visit = cls.step(cls.gov, "Submit the file at the counter", 0, user=cls.clerk, is_visit=True,
                             department_id=cls.registry_body.id)
        cls.env["legal.task.document"].create({"task_id": cls.gov.id, "name": "Company certificate",
                                               "state": "received"})
        cls.env["legal.task.document"].create({"task_id": cls.gov.id, "name": "Tax card", "state": "missing"})
        # The other lawyer's matter, which the first lawyer must never see.
        cls.other = cls.open_matter(client=cls.client_b, name="Other team's lawsuit")
        cls.other_step = cls.step(cls.other, "Their step", 0)

    def my_day(self, user, scope="me"):
        # A fresh cache, as in a real request: access is checked when a value
        # is fetched, and values already read as superuser would hide a gap.
        self.env.invalidate_all()
        return self.env["legal.task"].with_user(user).get_my_day(scope)

    def test_lawyer_rows_bands_and_actions(self):
        payload = self.my_day(self.lawyer)
        self.assertEqual(payload["scope"], "me")
        self.assertFalse(payload["read_only"])
        overdue = {row["key"]: row for row in self.rows(payload, "overdue")}
        self.assertIn(f"step-{self.late_step.id}", overdue)
        self.assertEqual(overdue[f"step-{self.late_step.id}"]["action"]["type"], "tick")
        today = {row["key"]: row for row in self.rows(payload, "today")}
        self.assertEqual(today[f"hearing-{self.session.id}"]["action"]["type"], "outcome")
        week = {row["key"] for row in self.rows(payload, "week")}
        self.assertIn(f"deadline-{self.deadline.id}", week)
        # Only the next step of a matter is listed: the later one depends on it.
        keys = {row["key"] for row in self.rows(payload)}
        self.assertNotIn(f"step-{self.later_step.id}", keys)
        # Each row says why it is there and which matter it belongs to.
        row = overdue[f"step-{self.late_step.id}"]
        self.assertEqual(row["reason"], "Draft the petition")
        self.assertEqual(row["task_id"], self.suit.id)
        self.assertIn("LDM Client A", row["line"])

    def test_rules_apply(self):
        keys = {row["key"] for row in self.rows(self.my_day(self.lawyer))}
        self.assertNotIn(f"step-{self.other_step.id}", keys)
        # Even a manager-only scope asked for by a lawyer falls back to "me".
        payload = self.my_day(self.lawyer, "all")
        self.assertEqual(payload["scope"], "me")
        self.assertFalse(payload["scopes"])
        self.assertNotIn(f"step-{self.other_step.id}", {row["key"] for row in self.rows(payload)})

    def test_clerk_sees_his_visits_by_body_and_no_outcome_action(self):
        advance = self.env["legal.advance"].create({"name": "Fees", "user_id": self.clerk.id, "amount": 250000,
                                                   "state": "paid"})
        payload = self.my_day(self.clerk)
        visit = next(row for row in self.rows(payload) if row["key"] == f"step-{self.visit.id}")
        self.assertEqual(visit["kind"], "visit")
        self.assertEqual(visit["action"]["type"], "visit")
        self.assertFalse(any(row["action"] and row["action"]["type"] == "outcome" for row in self.rows(payload)))
        self.assertEqual(len(payload["by_body"]), 1)
        group = payload["by_body"][0]
        self.assertEqual(group["body"], self.registry_body.name)
        documents = {doc["name"]: doc["have"] for doc in group["visits"][0]["documents"]}
        self.assertEqual(documents, {"Company certificate": True, "Tax card": False})
        self.assertEqual(payload["advance"][0]["amount"], advance.amount)

    def test_auditor_reads_without_actions(self):
        payload = self.my_day(self.auditor)
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["can_create"])
        self.assertEqual(payload["scope"], "all")
        rows = self.rows(payload)
        self.assertTrue(rows)
        self.assertFalse(any(row["action"] for row in rows))
        self.assertFalse(payload["by_body"])
        self.assertTrue(payload["counts"])

    def test_manager_scopes_bands_and_counts(self):
        tomorrow_session = self.Hearing.create({"task_id": self.other.id, "date": self.day(1)})
        payload = self.my_day(self.manager, "all")
        self.assertEqual(payload["scope"], "all")
        self.assertEqual([s["key"] for s in payload["scopes"]], ["me", "team", "all"])
        keys = {row["key"] for row in self.rows(payload)}
        self.assertIn(f"step-{self.other_step.id}", keys)
        self.assertIn(f"step-{self.late_step.id}", keys)
        bands = {band["key"]: band for band in payload["manager"]}
        self.assertIn(f"unstaffed-{tomorrow_session.id}", {row["key"] for row in bands["unstaffed"]["rows"]})
        counts = {count["key"]: count for count in payload["counts"]}
        self.assertGreaterEqual(counts["overdue"]["count"], 1)
        self.assertEqual(counts["overdue"]["model"], "legal.task")
        # Every count opens exactly the records it counted.
        Task = self.env["legal.task"].with_user(self.manager)
        for key in ("open", "overdue", "week"):
            self.assertEqual(Task.search_count(counts[key]["domain"]), counts[key]["count"], key)

    def test_bands_are_bounded(self):
        task = self.open_matter(name="Many steps")
        for index in range(60):
            other = self.open_matter(name=f"Matter {index}")
            self.step(other, f"Step {index}", -1)
        payload = self.my_day(self.lawyer)
        overdue = self.band(payload, "overdue")
        self.assertGreaterEqual(overdue["count"], 60)
        self.assertEqual(len(overdue["rows"]), 50)
        self.assertTrue(overdue["truncated"])
        self.assertTrue(task)

    def test_approver_chip_and_row_respect_separation_of_duties(self):
        template = self.env.ref(f"{M}.ldm_template_contract_review")
        template.requires_approval = True
        waiting_before = (self.my_day(self.approver)["approvals"] or {}).get("count", 0)
        task = self.env["legal.task"].browse(self.env["legal.task"].with_user(self.lawyer).create_from_template(
            {"template_id": template.id, "legal_company_id": self.client_a.id}))
        self.assertEqual(task.approval_state, "to_approve")
        payload = self.my_day(self.approver)
        self.assertEqual(payload["approvals"]["count"], waiting_before + 1)
        row = next(row for row in self.rows(payload, "today") if row["key"] == f"approval-{task.id}")
        self.assertEqual(row["action"]["type"], "approve")
        # The approver is not on the client's team: the row still names it.
        self.assertIn(self.client_a.name, row["line"])
        # The lawyer who asked sees it waiting, with nothing to do on it.
        lawyer_rows = {row["key"]: row for row in self.rows(self.my_day(self.lawyer))}
        self.assertNotIn(f"approval-{task.id}", lawyer_rows)
        self.assertEqual(lawyer_rows[f"waiting-{task.id}"]["action"], False)
        self.assertFalse(self.my_day(self.lawyer)["approvals"])

    def test_activity_row_and_done(self):
        activity = self.suit.activity_schedule("mail.mail_activity_data_todo", summary="Call the client",
                                               user_id=self.lawyer.id, date_deadline=self.today)
        payload = self.my_day(self.lawyer)
        row = next(row for row in self.rows(payload, "today") if row["key"] == f"activity-{activity.id}")
        self.assertEqual(row["reason"], "Call the client")
        self.env["legal.task"].with_user(self.lawyer).ldm_my_day_activity_done(activity.id)
        self.assertFalse(activity.exists().filtered("active"))

    def test_reminder_activities_are_not_listed_twice(self):
        self.env["legal.task"]._ldm_run_reminders()
        keys = [row["key"] for row in self.rows(self.my_day(self.lawyer))]
        self.assertFalse([key for key in keys if key.startswith("activity-")])

    def test_notification_row_saves_the_date(self):
        judgment = self.env["legal.judgment"].create({"task_id": self.suit.id, "date": self.day(-3)})
        self.Deadline.create({"task_id": self.suit.id, "judgment_id": judgment.id, "name": "Appeal",
                              "state": "awaiting_service", "company_id": self.company.id})
        payload = self.my_day(self.lawyer)
        row = next(row for row in self.rows(payload) if row["key"] == f"notification-{judgment.id}")
        self.assertEqual(row["action"]["type"], "notified")
        self.env["legal.task"].with_user(self.lawyer).ldm_my_day_notified(judgment.id, str(self.day(-1)))
        self.assertEqual(judgment.notified_date, self.day(-1))
        manager = self.my_day(self.manager)
        band = next(band for band in manager["manager"] if band["key"] == "notifications")
        self.assertIn(f"notification-{judgment.id}", {row["key"] for row in band["rows"]})

    def test_all_clear(self):
        idle = new_test_user(self.env, login="ldm_idle", groups=f"base.group_user,{M}.group_legal_user")
        payload = self.my_day(idle)
        self.assertTrue(payload["all_clear"])
        self.assertEqual(payload["total"], 0)

    def test_agenda_groups_by_day(self):
        visit = self.step(self.gov, "Collect the result", 2, user=self.clerk, is_visit=True)
        Task = self.env["legal.task"]
        mine = Task.with_user(self.lawyer).ldm_get_agenda("me", 14)
        keys = {item["key"] for day in mine["days"] for item in day["items"]}
        self.assertIn(f"hearing-{self.session.id}", keys)
        self.assertIn(f"deadline-{self.deadline.id}", keys)
        self.assertNotIn(f"visit-{visit.id}", keys)
        clerk = Task.with_user(self.clerk).ldm_get_agenda("me", 14)
        self.assertIn(f"visit-{visit.id}", {item["key"] for day in clerk["days"] for item in day["items"]})
        dates = [day["date"] for day in mine["days"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(Task.ldm_agenda_calendar_action()["res_model"], "legal.hearing")
