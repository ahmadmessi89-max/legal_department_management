# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .ws_common import WsCase

WIZARD = "legal.handover.wizard"


@tagged("post_install", "-at_install", "ldm")
class TestWsHandover(WsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.matter = cls.open_matter(name="Lawsuit to hand over", kind="litigation")
        cls.second = cls.open_matter(name="Second matter")
        cls.near_step = cls.step(cls.matter, "Near step", 2, user=cls.lawyer)
        cls.far_step = cls.step(cls.second, "Far step", 30, user=cls.lawyer)
        cls.session = cls.Hearing.create({"task_id": cls.matter.id, "date": cls.day(3),
                                          "attending_user_id": cls.lawyer.id})
        cls.deadline = cls.Deadline.create({"task_id": cls.matter.id, "name": "Appeal", "date_safe": cls.day(5),
                                            "user_id": cls.lawyer.id, "company_id": cls.company.id})
        cls.activity = cls.matter.activity_schedule("mail.mail_activity_data_todo", summary="Call",
                                                    user_id=cls.lawyer.id, date_deadline=cls.day(1))
        cls.poa = cls.env["legal.poa"].create({"principal_company_id": cls.client_a.id, "number": "77",
                                               "agent_user_ids": [(6, 0, [cls.lawyer.id])]})

    def wizard(self, **vals):
        values = {"from_user_id": self.lawyer.id, "to_user_id": self.lawyer2.id}
        values.update(vals)
        return self.env[WIZARD].with_user(self.manager).create(values)

    def test_dialog_opens_through_default_get_and_new(self):
        Wizard = self.env[WIZARD].with_user(self.manager)
        defaults = Wizard.default_get(list(Wizard._fields))
        self.assertTrue(defaults["scope_matters"])
        self.assertTrue(defaults["scope_steps"])
        preview = Wizard.new({"from_user_id": self.lawyer.id, "to_user_id": self.lawyer2.id})
        self.assertIn(self.poa, preview.poa_ids._origin)
        self.assertTrue(preview.summary)

    def test_permanent_hand_over(self):
        self.wizard(note="Files are in cabinet 3").action_confirm()
        for task in (self.matter, self.second):
            self.assertEqual(task.lawyer_id, self.lawyer2)
            self.assertIn(self.lawyer2, task.lawyer_ids)
            self.assertNotIn(self.lawyer, task.lawyer_ids)
        self.assertEqual(self.near_step.user_id, self.lawyer2)
        self.assertEqual(self.far_step.user_id, self.lawyer2)
        self.assertEqual(self.session.attending_user_id, self.lawyer2)
        self.assertEqual(self.deadline.user_id, self.lawyer2)
        self.assertEqual(self.activity.user_id, self.lawyer2)
        self.assertEqual(self.client_a.lawyer_id, self.lawyer2)
        # One hand-over note per matter, carrying the manager's words.
        notes = self.matter.message_ids.filtered(lambda m: "Files are in cabinet 3" in (m.body or ""))
        self.assertEqual(len(notes), 1)

    def test_cover_until_a_date(self):
        self.wizard(date_end=self.day(10)).action_confirm()
        # The colleague joins; the responsible stays.
        self.assertEqual(self.matter.lawyer_id, self.lawyer)
        self.assertIn(self.lawyer2, self.matter.lawyer_ids)
        self.assertIn(self.lawyer, self.matter.lawyer_ids)
        # Dated work up to the end date moves; later work stays.
        self.assertEqual(self.near_step.user_id, self.lawyer2)
        self.assertEqual(self.far_step.user_id, self.lawyer)
        self.assertEqual(self.client_a.lawyer_id, self.lawyer)

    def test_scope_checkboxes(self):
        self.wizard(scope_matters=False, scope_hearings=False, scope_deadlines=False,
                    scope_activities=False).action_confirm()
        self.assertEqual(self.matter.lawyer_id, self.lawyer)
        self.assertEqual(self.near_step.user_id, self.lawyer2)
        self.assertEqual(self.session.attending_user_id, self.lawyer)

    def test_only_managers(self):
        wizard = self.env[WIZARD].with_user(self.manager).create(
            {"from_user_id": self.lawyer.id, "to_user_id": self.lawyer2.id})
        with self.assertRaises(AccessError):
            wizard.with_user(self.lawyer).action_confirm()
        with self.assertRaises(AccessError):
            self.env[WIZARD].with_user(self.lawyer).create(
                {"from_user_id": self.lawyer.id, "to_user_id": self.lawyer2.id})
