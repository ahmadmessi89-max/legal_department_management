# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .test_gov_common import PNG, GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovVisit(GovCase):

    def open_visit(self, matter):
        return matter.step_ids.filtered(lambda s: s.is_visit and s.state == "todo").sorted("sequence")[:1]

    def wizard(self, step, user=None, **values):
        """Build the dialog the way the web client does: the action's context,
        default_get, then create with what the user typed."""
        user = user or self.clerk
        action = step.with_user(user).action_ldm_log_visit()
        Wizard = self.env["legal.visit.wizard"].with_user(user).with_context(action["context"])
        defaults = Wizard.default_get(list(Wizard._fields))
        defaults.update(values)
        return Wizard.create(defaults)

    def test_dialog_opens_through_default_get_and_new(self):
        matter = self.gov_matter()
        step = self.open_visit(matter)
        action = step.with_user(self.clerk).action_ldm_log_visit()
        self.assertEqual(action["res_model"], "legal.visit.wizard")
        self.assertEqual(action["target"], "new")
        Wizard = self.env["legal.visit.wizard"].with_user(self.clerk).with_context(action["context"])
        defaults = Wizard.default_get(["step_id", "task_id", "result", "visit_date"])
        self.assertEqual(defaults["step_id"], step.id)
        self.assertEqual(defaults["task_id"], matter.id)
        self.assertEqual(defaults["result"], "done")
        draft = Wizard.new(defaults)
        self.assertEqual(draft.department_id, self.tax_body)
        self.assertEqual(draft.visit_name, step.name)
        self.assertEqual(draft.currency_id, matter.currency_id)
        self.assertEqual(draft.waiting_on, "body", "Another visit is planned, so the body has the file")
        draft.result = "rejected"
        self.assertEqual(draft.waiting_on, "us")

    def test_visit_with_a_fee_creates_exactly_one_expense(self):
        matter = self.gov_matter()
        step = self.open_visit(matter)
        before = len(matter.message_ids)
        wizard = self.wizard(step, fee_amount=25000, receipt_number="R-5521", photo=PNG, photo_name="receipt.png",
                             waiting_for="Nothing")
        wizard.action_confirm()
        self.assertEqual(step.state, "done")
        self.assertEqual(step.visit_result, "done")
        self.assertEqual(step.receipt_number, "R-5521")
        self.assertEqual(step.fee_amount, 25000)
        self.assertEqual(step.done_by_id, self.clerk)
        expenses = self.env["legal.task.expense"].search([("task_id", "=", matter.id)])
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses.step_id, step)
        self.assertEqual(expenses.amount, 25000)
        self.assertEqual(expenses.receipt_number, "R-5521")
        self.assertEqual(expenses.category_id, self.env["legal.expense.category"]._ldm_government_fee())
        self.assertTrue(expenses.attachment_id)
        self.assertEqual(step.attachment_id, expenses.attachment_id)
        self.assertEqual(expenses.attachment_id.res_model, "legal.task")
        self.assertEqual(matter.expenses_amount, 25000)
        self.assertEqual(matter.waiting_on, "body")
        self.assertEqual(matter.date_submitted, self.today)
        self.assertEqual(len(matter.message_ids), before + 1)
        self.assertIn("R-5521", matter.message_ids[0].body)

    def test_visit_without_a_fee_creates_no_expense(self):
        matter = self.gov_matter()
        self.wizard(self.open_visit(matter)).action_confirm()
        self.assertFalse(matter.expense_ids)

    def test_still_pending_keeps_the_visit_open_on_a_new_date(self):
        matter = self.gov_matter()
        step = self.open_visit(matter)
        back = self.today + timedelta(days=4)
        self.wizard(step, result="pending", next_date=back, waiting_for="The manager's signature").action_confirm()
        self.assertEqual(step.state, "todo")
        self.assertEqual(step.date_due, back)
        self.assertEqual(step.visit_result, "pending")
        self.assertEqual(step.visit_waiting_for, "The manager's signature")
        self.assertEqual(matter.waiting_on, "body")

    def test_rejected_hands_the_ball_back_to_us(self):
        matter = self.gov_matter()
        matter.with_user(self.lawyer).write({"waiting_on": "body", "date_submitted": self.today - timedelta(days=9)})
        step = self.open_visit(matter)
        self.wizard(step, result="rejected", waiting_for="A renewed tax card").action_confirm()
        self.assertEqual(step.state, "todo")
        self.assertEqual(matter.waiting_on, "us")

    def test_resubmission_restarts_the_clock_at_the_body(self):
        matter = self.gov_matter()
        matter.with_user(self.lawyer).write({"waiting_on": "us", "date_submitted": self.today - timedelta(days=30)})
        self.wizard(self.open_visit(matter), result="pending").action_confirm()
        self.assertEqual(matter.date_submitted, self.today)

    def test_done_with_a_next_date_plans_the_follow_up(self):
        matter = self.gov_matter()
        step = self.open_visit(matter)
        later = self.today + timedelta(days=7)
        steps_before = len(matter.step_ids)
        self.wizard(step, next_step="Collect the stamped copy", next_date=later).action_confirm()
        self.assertEqual(len(matter.step_ids), steps_before + 1)
        new = matter.step_ids.filtered(lambda s: s.name == "Collect the stamped copy")
        self.assertTrue(new.is_visit)
        self.assertEqual(new.date_due, later)
        self.assertEqual(new.department_id, self.tax_body)

    def test_last_visit_done_hands_the_matter_back(self):
        matter = self.gov_matter()
        for step in matter.step_ids.filtered("is_visit").sorted("sequence"):
            self.wizard(step).action_confirm()
        self.assertEqual(matter.waiting_on, "us")
        self.assertFalse(matter.step_ids.filtered(lambda s: s.is_visit and s.state == "todo"))

    def test_unplanned_visit_from_the_matter(self):
        matter = self.gov_matter()
        for step in matter.step_ids.filtered("is_visit"):
            step.state = "done"
        action = matter.with_user(self.clerk).action_ldm_log_visit()
        Wizard = self.env["legal.visit.wizard"].with_user(self.clerk).with_context(action["context"])
        values = Wizard.default_get(list(Wizard._fields))
        self.assertFalse(values.get("step_id"))
        wizard = Wizard.create(dict(values, fee_amount=5000))
        self.assertIn(self.tax_body.name, wizard.visit_name)
        wizard.action_confirm()
        visit = matter.step_ids.filtered(lambda s: s.is_visit and s.fee_amount == 5000)
        self.assertEqual(len(visit), 1)
        self.assertEqual(visit.state, "done")
        self.assertEqual(len(matter.expense_ids), 1)

    def test_the_auditor_cannot_log_a_visit(self):
        matter = self.gov_matter()
        step = self.open_visit(matter)
        with self.assertRaises(AccessError):
            self.env["legal.visit.wizard"].with_user(self.auditor).create(
                {"task_id": matter.id, "step_id": step.id})

    def test_a_closed_matter_takes_no_visit(self):
        matter = self.gov_matter()
        step = self.open_visit(matter)
        wizard = self.wizard(step)
        matter._ldm_close("completed", "")
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_log_visit_refuses_a_step_that_is_not_a_visit(self):
        matter = self.gov_matter()
        desk_step = matter.step_ids.filtered(lambda s: not s.is_visit)[:1]
        with self.assertRaises(UserError):
            desk_step.action_ldm_log_visit()
