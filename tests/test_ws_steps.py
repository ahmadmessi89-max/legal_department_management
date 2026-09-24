# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .ws_common import WsCase


@tagged("post_install", "-at_install", "ldm")
class TestWsSteps(WsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.matter = cls.open_matter(name="Registry amendment", kind="government", department_id=cls.registry_body.id,
                                     lawyer_ids=[(6, 0, [cls.lawyer.id, cls.clerk.id])])
        cls.visit = cls.step(cls.matter, "Pay the fee at the counter", 0, user=cls.clerk, is_visit=True,
                             fee_amount=25000, receipt_number="R-1")
        cls.plain = cls.step(cls.matter, "Collect the certificate", 1, user=cls.clerk)

    def test_tick_and_undo_a_paid_visit(self):
        Step = self.env["legal.task.step"].with_user(self.clerk)
        result = Step.browse(self.visit.id).action_ldm_toggle_done()
        self.assertEqual(result["state"], "done")
        self.assertEqual(self.visit.state, "done")
        self.assertEqual(self.visit.done_by_id, self.clerk)
        self.assertEqual(self.visit.done_date, self.today)
        # Exactly one expense line for the fee, linked to the step.
        self.assertEqual(len(self.visit.expense_ids), 1)
        self.assertEqual(result["expense_ids"], self.visit.expense_ids.ids)
        self.assertEqual(self.visit.expense_ids.amount, 25000)
        self.assertEqual(self.visit.expense_ids.receipt_number, "R-1")
        # Undo puts the step back and removes the expense that click created.
        Step.browse(self.visit.id).action_ldm_undo_done(result["expense_ids"])
        self.assertEqual(self.visit.state, "todo")
        self.assertFalse(self.visit.done_date)
        self.assertFalse(self.visit.expense_ids)

    def test_second_tick_does_not_book_twice(self):
        Step = self.env["legal.task.step"].with_user(self.clerk).browse(self.visit.id)
        Step.action_ldm_toggle_done()
        Step.action_ldm_toggle_done()  # open again (no Undo): the expense stays
        again = Step.action_ldm_toggle_done()
        self.assertEqual(len(self.visit.expense_ids), 1)
        self.assertEqual(again["expense_ids"], [])

    def test_undo_never_removes_other_expenses(self):
        other = self.env["legal.task.expense"].create({"task_id": self.matter.id, "name": "Court fee", "amount": 5000})
        Step = self.env["legal.task.step"].with_user(self.clerk).browse(self.plain.id)
        Step.action_ldm_toggle_done()
        Step.action_ldm_undo_done([other.id])
        self.assertTrue(other.exists())
        self.assertEqual(self.plain.state, "todo")

    def test_tick_closes_its_reminder(self):
        self.env["legal.task"]._ldm_run_reminders()
        step_type = self.env.ref("legal_department_management.ldm_activity_step")
        reminders = self.matter.activity_ids.filtered(
            lambda a: a.activity_type_id == step_type and self.visit.name in (a.summary or ""))
        self.assertTrue(reminders)
        self.env["legal.task.step"].with_user(self.clerk).browse(self.visit.id).action_ldm_toggle_done()
        self.assertFalse(reminders.exists().filtered("active"))

    def test_auditor_and_closed_matters_cannot_tick(self):
        with self.assertRaises(AccessError):
            self.env["legal.task.step"].with_user(self.auditor).browse(self.plain.id).action_ldm_toggle_done()
        self.matter._ldm_close("completed", "")
        with self.assertRaises(UserError):
            self.env["legal.task.step"].with_user(self.clerk).browse(self.plain.id).action_ldm_toggle_done()

    def test_attach_a_file_to_a_document(self):
        document = self.env["legal.task.document"].create({"task_id": self.matter.id, "name": "Tax card"})
        attachment = self.env["ir.attachment"].create({"name": "tax.pdf", "raw": b"%PDF-1.4",
                                                       "res_model": "legal.task", "res_id": self.matter.id})
        Task = self.env["legal.task"].with_user(self.lawyer).browse(self.matter.id)
        result = Task.ldm_attach_document(document.id, [attachment.id])
        self.assertEqual(result["state"], "received")
        self.assertEqual(document.attachment_id, attachment)
        self.assertEqual(document.received_date, self.today)
        general = self.env["ir.attachment"].create({"name": "note.pdf", "raw": b"%PDF-1.4",
                                                    "res_model": "legal.task", "res_id": self.matter.id})
        Task.ldm_attach_document(False, [general.id])
        self.assertIn(general, self.matter.attachment_ids)
        stranger = self.env["ir.attachment"].create({"name": "x.pdf", "raw": b"%PDF-1.4"})
        with self.assertRaises(UserError):
            Task.ldm_attach_document(document.id, [stranger.id])
