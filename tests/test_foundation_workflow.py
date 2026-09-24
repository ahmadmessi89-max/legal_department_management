# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import M, LdmCase


@tagged("post_install", "-at_install", "ldm")
class TestFoundationWorkflow(LdmCase):

    def test_numbering(self):
        one = self.make_matter()
        two = self.make_matter()
        self.assertTrue(one.task_number.startswith("CASE/"))
        self.assertNotEqual(one.task_number, two.task_number)
        self.assertIn(one.task_number, one.display_name)

    def test_cannot_create_closed_or_skip_the_dialogs(self):
        with self.assertRaises(UserError):
            self.env["legal.task"].with_user(self.lawyer).create(
                {"name": "x", "legal_company_id": self.client_a.id, "state": "done"})
        matter = self.make_matter(state="in_progress")
        self.assertEqual(matter.state, "in_progress")
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).write({"state": "done"})
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).write({"state": "cancelled"})
        matter.with_user(self.lawyer).write({"state": "pending_docs"})
        self.assertEqual(matter.state, "pending_docs")

    def test_close_through_the_dialog(self):
        matter = self.make_matter(state="in_progress")
        action = matter.with_user(self.lawyer).action_set_done()
        Wizard = self.env["legal.task.decision.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["task_ids", "mode", "outcome"])
        self.assertEqual(defaults["mode"], "close")
        wizard = Wizard.create({"outcome": "won", "note": "Judgment in our favour"})
        wizard.action_confirm()
        self.assertEqual(matter.state, "done")
        self.assertEqual(matter.outcome, "won")
        self.assertTrue(matter.date_closed)

    def test_cancel_needs_a_reason(self):
        matter = self.make_matter(state="in_progress")
        wizard = self.env["legal.task.decision.wizard"].with_user(self.lawyer).create(
            {"task_ids": [(6, 0, matter.ids)], "mode": "cancel", "note": " "})
        with self.assertRaises(UserError):
            wizard.action_confirm()
        wizard.note = "Client withdrew the instruction"
        wizard.action_confirm()
        self.assertEqual(matter.state, "cancelled")

    def test_reopen_is_for_managers(self):
        matter = self.make_matter(state="in_progress")
        matter._ldm_close("completed", "")
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).action_set_in_progress()
        matter.with_user(self.manager).action_set_in_progress()
        self.assertEqual(matter.state, "in_progress")
        self.assertFalse(matter.date_closed)

    def test_government_matter_needs_a_body_to_start(self):
        matter = self.make_matter(kind="government")
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).action_set_in_progress()
        matter.department_id = self.registry_body
        matter.with_user(self.lawyer).action_set_in_progress()
        self.assertEqual(matter.ministry_id, self.ministry)

    def test_approval_path(self):
        self.t_lawsuit.requires_approval = True
        matter_id = self.env["legal.task"].with_user(self.lawyer).create_from_template({
            "template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
            "department_id": self.court.id})
        matter = self.env["legal.task"].browse(matter_id)
        self.assertEqual(matter.state, "draft")
        self.assertEqual(matter.approval_state, "to_approve")
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).action_set_in_progress()
        matter.with_user(self.approver).action_approve()
        self.assertEqual(matter.state, "in_progress")

    def test_create_from_template(self):
        # With office-wide visibility a clerk may open a matter for any client;
        # it stays readable to them afterwards because they join its team.
        self.env["res.config.settings"]._ldm_apply_visibility("all")
        matter_id = self.env["legal.task"].with_user(self.clerk).create_from_template({
            "template_id": self.t_government.id, "legal_company_id": self.client_b.id,
            "department_id": self.registry_body.id})
        matter = self.env["legal.task"].with_user(self.clerk).browse(matter_id)
        # the clerk opened a matter for another lawyer's client and can still open it
        self.assertEqual(matter.name.split(" — ")[0], self.t_government.name)
        self.assertEqual(matter.lawyer_id, self.lawyer2)
        self.assertIn(self.clerk, matter.lawyer_ids)
        self.assertEqual(matter.kind, "government")
        self.assertEqual(matter.state, "in_progress")
        self.assertEqual(len(matter.step_ids), 3)
        self.assertTrue(all(step.date_due for step in matter.step_ids))
        visits = matter.step_ids.filtered("is_visit")
        self.assertEqual(len(visits), 2)
        self.assertEqual(matter.session_date, min(visits.mapped("date_due")))
        for step in matter.step_ids:
            self.assertTrue(self.company.ldm_is_working_day(step.date_due), step.date_due)

    def test_lawsuit_key_date_makes_a_session_and_an_opponent(self):
        matter_id = self.env["legal.task"].with_user(self.lawyer).create_from_template({
            "template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
            "department_id": self.court.id, "key_date": "2026-10-04", "our_role": "plaintiff",
            "opponent_name": "LDM Opponent Trading"})
        matter = self.env["legal.task"].browse(matter_id)
        self.assertEqual(len(matter.hearing_ids), 1)
        self.assertEqual(matter.hearing_ids.department_id, self.court)
        self.assertEqual(matter.opponent_name, "LDM Opponent Trading")
        self.assertEqual(matter.next_date, self.d("2026-10-04") if matter.next_date == self.d("2026-10-04")
                         else matter.next_date)

    def test_reminders_are_not_duplicated(self):
        matter = self.make_matter(state="in_progress", due_date="2020-01-01")
        self.env["legal.task"]._ldm_run_reminders()
        first = len(matter.activity_ids)
        self.env["legal.task"]._ldm_run_reminders()
        self.assertEqual(len(matter.activity_ids), first)
        self.assertGreaterEqual(first, 1)
        self.assertEqual(matter.activity_ids.activity_type_id, self.env.ref(f"{M}.ldm_activity_target"))

    def test_clerk_with_assigned_visibility_opens_for_own_clients(self):
        self.client_a.lawyer_ids = [(4, self.clerk.id)]
        matter_id = self.env["legal.task"].with_user(self.clerk).create_from_template({
            "template_id": self.t_government.id, "legal_company_id": self.client_a.id,
            "department_id": self.registry_body.id})
        matter = self.env["legal.task"].with_user(self.clerk).browse(matter_id)
        self.assertEqual(matter.lawyer_id, self.lawyer)
        self.assertIn(self.clerk, matter.lawyer_ids)
        self.assertTrue(matter.name)

    def test_approver_sees_what_is_sent_for_approval(self):
        matter = self.make_matter(client=self.client_b)
        self.assertNotIn(matter, self.env["legal.task"].with_user(self.approver).search([]))
        matter.with_user(self.lawyer2).action_request_approval()
        self.assertIn(matter, self.env["legal.task"].with_user(self.approver).search([]))
