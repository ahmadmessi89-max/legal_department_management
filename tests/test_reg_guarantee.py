# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegGuarantee(RegCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["legal.guarantee"])
        cls.bank = cls.env["res.partner"].create({"name": "Rafidain Bank", "is_company": True})
        cls.beneficiary = cls.env["res.partner"].create({"name": "Ministry of Water Resources", "is_company": True})

    def guarantee(self, days=20, **values):
        vals = {"name": "Performance guarantee — Basra water", "kind": "performance", "number": "LG-778",
                "bank_id": self.bank.id, "beneficiary_id": self.beneficiary.id, "amount": 150000000,
                "legal_company_id": self.client_a.id, "date_expiry": self.today + timedelta(days=days)}
        vals.update(values)
        return self.env["legal.guarantee"].with_user(self.lawyer).create(vals)

    def deadlines(self, guarantee, state="open"):
        return self.env["legal.deadline"].search([("source_model", "=", "legal.guarantee"),
                                                  ("source_id", "=", guarantee.id), ("state", "=", state)])

    def wizard(self, guarantee, action):
        Wizard = self.env["legal.guarantee.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["guarantee_id", "mode", "template_id", "draft_letter", "lang", "date"])
        self.assertEqual(Wizard.new(defaults).guarantee_id, guarantee)
        return Wizard, defaults

    def test_deadline_thirty_days_ahead(self):
        far = self.guarantee(days=90)
        self.assertFalse(self.deadlines(far))
        self.assertFalse(far.is_expiring)
        near = self.guarantee(days=20)
        self.assertTrue(near.is_expiring)
        self.assertEqual(len(self.deadlines(near)), 1)
        self.assertEqual(self.deadlines(near).date_safe, near.date_expiry)
        self.env["legal.guarantee"]._cron_ldm_guarantee_expiry()
        self.assertEqual(len(self.deadlines(near)), 1)
        self.assertIn(near, self.env["legal.guarantee"].search([("is_expiring", "=", True)]))
        self.assertNotIn(far, self.env["legal.guarantee"].search([("is_expiring", "=", True)]))

    def test_request_extension_drafts_the_letter(self):
        guarantee = self.guarantee()
        Wizard, defaults = self.wizard(guarantee, guarantee.action_ldm_request_extension())
        self.assertEqual(defaults["mode"], "request_extension")
        self.assertEqual(defaults["template_id"], self.env.ref(f"{M}.ldm_letter_guarantee_extension").id)
        result = Wizard.create({"lang": "en_US"}).action_confirm()
        letter = self.env["legal.correspondence"].browse(result["res_id"])
        self.assertEqual(guarantee.state, "extension_requested")
        self.assertEqual(letter.guarantee_id, guarantee)
        self.assertEqual(letter.partner_id, self.bank)
        self.assertIn("LG-778", letter.name)
        self.assertIn("Ministry of Water Resources", letter.body_html)

    def test_extension_moves_the_deadline(self):
        guarantee = self.guarantee()
        Wizard, defaults = self.wizard(guarantee, guarantee.action_ldm_extend())
        self.assertFalse(defaults["draft_letter"])
        with self.assertRaises(UserError):
            Wizard.create({"new_expiry": guarantee.date_expiry}).action_confirm()
        Wizard.create({"new_expiry": self.today + timedelta(days=200)}).action_confirm()
        self.assertEqual(guarantee.state, "extended")
        self.assertEqual(guarantee.date_expiry, self.today + timedelta(days=200))
        self.assertFalse(self.deadlines(guarantee))
        self.assertEqual(len(self.deadlines(guarantee, "done")), 1)

    def test_release(self):
        guarantee = self.guarantee()
        Wizard, defaults = self.wizard(guarantee, guarantee.action_ldm_release())
        Wizard.create({"draft_letter": False}).action_confirm()
        self.assertEqual(guarantee.state, "released")
        self.assertEqual(guarantee.release_date, self.today)
        self.assertFalse(self.deadlines(guarantee))
        with self.assertRaises(UserError):
            guarantee.action_ldm_release()

    def test_expired_by_its_date(self):
        guarantee = self.guarantee(days=-1)
        self.assertEqual(guarantee.state, "expired")

    def test_only_lawyers_act(self):
        guarantee = self.guarantee()
        with self.assertRaises(AccessError):
            guarantee.with_user(self.clerk).action_ldm_release()

    def test_reminder_kept_once(self):
        guarantee = self.guarantee(days=10)
        self.env["legal.task"]._ldm_run_reminders()
        self.env["legal.task"]._ldm_run_reminders()
        kind = self.env.ref(f"{M}.ldm_activity_guarantee_expiry")
        self.assertEqual(len(guarantee.activity_ids.filtered(lambda a: a.activity_type_id == kind)), 1)
