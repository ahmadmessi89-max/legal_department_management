# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegPoa(RegCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["legal.poa"])

    def poa(self, **values):
        vals = {"principal_company_id": self.client_a.id, "poa_type": "judicial", "number": "1234",
                "notary_office": "Karkh notary", "agent_user_ids": [(6, 0, [self.lawyer.id])]}
        vals.update(values)
        return self.Poa.with_user(self.lawyer).create(vals)

    def expiry_deadlines(self, poa, state="open"):
        return self.env["legal.deadline"].search([("source_model", "=", "legal.poa"), ("source_id", "=", poa.id),
                                                  ("kind", "=", "expiry"), ("state", "=", state)])

    def test_expired_by_its_date(self):
        poa = self.poa(date_expiry=self.today - timedelta(days=1))
        self.assertEqual(poa.state, "expired")
        self.assertEqual(poa.expiry_status, "expired")
        poa.write({"date_expiry": self.today + timedelta(days=200)})
        self.assertEqual(poa.state, "active")
        self.assertEqual(poa.expiry_status, "valid")

    def test_one_expiry_deadline_in_the_warning_window(self):
        far = self.poa(date_expiry=self.today + timedelta(days=200))
        self.assertFalse(self.expiry_deadlines(far))
        poa = self.poa(date_expiry=self.today + timedelta(days=20))
        self.assertEqual(poa.expiry_status, "expiring")
        deadline = self.expiry_deadlines(poa)
        self.assertEqual(len(deadline), 1)
        self.assertEqual(deadline.date_safe, poa.date_expiry)
        self.assertEqual(deadline.user_id, self.lawyer)
        self.assertEqual(deadline.legal_company_id, self.client_a)
        self.Poa._cron_ldm_poa_expiry()
        self.Poa._cron_ldm_poa_expiry()
        self.assertEqual(len(self.expiry_deadlines(poa)), 1)
        poa.write({"date_expiry": self.today + timedelta(days=25)})
        self.assertEqual(self.expiry_deadlines(poa).date_safe, self.today + timedelta(days=25))
        # Renewed: the reminder was answered.
        poa.write({"date_expiry": self.today + timedelta(days=400)})
        self.assertFalse(self.expiry_deadlines(poa))
        self.assertEqual(len(self.expiry_deadlines(poa, "done")), 1)

    def test_the_cron_expires(self):
        poa = self.poa(date_expiry=self.today + timedelta(days=5))
        self.env.cr.execute("UPDATE legal_poa SET date_expiry = %s WHERE id = %s",
                            (self.today - timedelta(days=2), poa.id))
        poa.invalidate_recordset(["date_expiry"])
        self.Poa._cron_ldm_poa_expiry()
        self.assertEqual(poa.state, "expired")

    def test_status_is_guarded(self):
        poa = self.poa()
        for values in ({"state": "revoked"}, {"state": "expired"}, {"revoke_reason": "x"},
                       {"revoked_date": self.today}):
            with self.assertRaises(AccessError):
                poa.write(values)
        created = self.Poa.with_user(self.lawyer).create({"principal_company_id": self.client_a.id,
                                                          "state": "revoked"})
        self.assertEqual(created.state, "active")

    def test_revocation_flags_matters(self):
        poa = self.poa(date_expiry=self.today + timedelta(days=10))
        matter = self.make_matter(poa_id=poa.id, state="in_progress")
        closed = self.make_matter(poa_id=poa.id, state="in_progress")
        closed._ldm_close("completed", "")
        action = poa.action_ldm_revoke()
        Wizard = self.env["legal.poa.revoke.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["poa_id", "date", "reason"])
        self.assertEqual(defaults["poa_id"], poa.id)
        self.assertEqual(defaults["date"], self.today)
        self.assertIn(matter, Wizard.new(defaults).open_task_ids._origin)
        wizard = Wizard.create({"reason": "Client ended the mandate by notarial notice 77"})
        wizard.action_confirm()
        self.assertEqual(poa.state, "revoked")
        self.assertEqual(poa.revoke_reason, "Client ended the mandate by notarial notice 77")
        self.assertEqual(matter.ldm_poa_state, "revoked")
        self.assertIn("notarial notice 77", matter.message_ids[:1].body)
        self.assertTrue(matter.activity_ids.filtered(lambda a: a.user_id == matter.lawyer_id))
        self.assertIn(closed, poa.task_ids)
        self.assertFalse(closed.activity_ids)
        self.assertFalse(self.expiry_deadlines(poa))
        self.assertEqual(len(self.expiry_deadlines(poa, "cancelled")), 1)
        # Revoked is final: a later date does not bring it back.
        with self.assertRaises(UserError):
            poa._ldm_revoke(self.today, "again")
        poa.write({"date_expiry": self.today + timedelta(days=300)})
        self.assertEqual(poa.state, "revoked")

    def test_only_lawyers_revoke(self):
        poa = self.poa()
        with self.assertRaises(AccessError):
            poa.with_user(self.clerk)._ldm_revoke(self.today, "reason")
        with self.assertRaises(UserError):
            poa._ldm_revoke(self.today, " ")

    def test_who_can_act_today(self):
        general = self.poa(number="G-1")
        at_registry = self.poa(number="S-1", body_ids=[(6, 0, [self.registry_body.id])])
        at_court = self.poa(number="S-2", body_ids=[(6, 0, [self.court.id])])
        expired = self.poa(number="E-1", date_expiry=self.today - timedelta(days=3))
        other_client = self.poa(number="O-1", principal_company_id=self.client_b.id)
        today = fields.Date.to_string(self.today)
        can_act = [("state", "=", "active"), "|", ("date_expiry", "=", False), ("date_expiry", ">=", today),
                   "|", ("date_issued", "=", False), ("date_issued", "<=", today)]
        before_registry = ["|", ("body_ids", "=", False), ("body_ids", "ilike", "Companies Registry")]
        found = self.Poa.with_user(self.lawyer).search(
            [("principal_company_id", "=", self.client_a.id)] + can_act + before_registry)
        self.assertIn(general, found)
        self.assertIn(at_registry, found)
        self.assertNotIn(at_court, found)
        self.assertNotIn(expired, found)
        self.assertNotIn(other_client, found)
        action = self.client_a.action_ldm_view_poas()
        self.assertEqual(action["domain"], [("principal_company_id", "=", self.client_a.id)])
        self.assertTrue(action["context"]["search_default_filter_can_act"])
        self.assertEqual(self.client_a.poa_count, 3)

    def test_expiry_status_search(self):
        soon = self.poa(date_expiry=self.today + timedelta(days=3))
        later = self.poa(date_expiry=self.today + timedelta(days=300))
        found = self.Poa.search([("expiry_status", "=", "expiring")])
        self.assertIn(soon, found)
        self.assertNotIn(later, found)

    def test_scan_upload(self):
        poa = self.poa()
        poa.write({"scan": "aGVsbG8=", "scan_name": "deed.pdf"})
        self.assertEqual(poa.attachment_id.name, "deed.pdf")
        self.assertEqual(poa.attachment_id.res_model, "legal.poa")
        self.assertEqual(poa.scan, b"aGVsbG8=")

    def test_reminders_are_kept_once(self):
        poa = self.poa(date_expiry=self.today + timedelta(days=12))
        Task = self.env["legal.task"]
        Task._ldm_run_reminders()
        Task._ldm_run_reminders()
        reminders = poa.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref(f"{M}.ldm_activity_poa_expiry"))
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders.user_id, self.lawyer)
        poa._ldm_revoke(self.today, "Ended")
        self.assertFalse(poa.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref(f"{M}.ldm_activity_poa_expiry")))
