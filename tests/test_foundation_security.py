# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import M, LdmCase


@tagged("post_install", "-at_install", "ldm")
class TestFoundationSecurity(LdmCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m_a = cls.make_matter(name="A's matter")
        cls.m_b = cls.make_matter(client=cls.client_b, name="B's matter")
        cls.m_secret = cls.make_matter(name="Confidential", confidential=True, lawyer=cls.lawyer2,
                                       lawyer_ids=[(6, 0, [cls.lawyer2.id])])
        cls.h_a = cls.env["legal.hearing"].create({"task_id": cls.m_a.id, "date": "2026-10-04"})
        cls.h_b = cls.env["legal.hearing"].create({"task_id": cls.m_b.id, "date": "2026-10-04"})
        cls.h_secret = cls.env["legal.hearing"].create({"task_id": cls.m_secret.id, "date": "2026-10-04"})

    def visible(self, user, model="legal.task"):
        return self.env[model].with_user(user).search([])

    def test_lawyer_sees_assigned_only(self):
        seen = self.visible(self.lawyer)
        self.assertIn(self.m_a, seen)
        self.assertNotIn(self.m_b, seen)

    def test_confidential_hidden_from_client_lawyer(self):
        # lawyer looks after client A, but the confidential matter's team is lawyer2 only
        self.assertNotIn(self.m_secret, self.visible(self.lawyer))
        self.assertIn(self.m_secret, self.visible(self.lawyer2))

    def test_child_records_follow_the_matter(self):
        hearings = self.visible(self.lawyer, "legal.hearing")
        self.assertIn(self.h_a, hearings)
        self.assertNotIn(self.h_b, hearings)
        self.assertNotIn(self.h_secret, hearings)

    def test_manager_and_auditor_see_everything(self):
        for user in (self.manager, self.auditor):
            seen = self.visible(user)
            self.assertTrue({self.m_a, self.m_b, self.m_secret} <= set(seen))

    def test_see_all_never_shows_confidential(self):
        self.env["res.config.settings"]._ldm_apply_visibility("all")
        seen = self.visible(self.lawyer)
        self.assertIn(self.m_b, seen)
        self.assertNotIn(self.m_secret, seen)
        self.assertNotIn(self.h_secret, self.visible(self.lawyer, "legal.hearing"))

    def test_auditor_cannot_change_anything(self):
        matter = self.m_a.with_user(self.auditor)
        with self.assertRaises(AccessError):
            matter.write({"name": "changed"})
        with self.assertRaises(AccessError):
            self.env["legal.task"].with_user(self.auditor).create(
                {"name": "x", "legal_company_id": self.client_a.id})
        with self.assertRaises(AccessError):
            matter.unlink()

    def test_approval_cannot_be_forged(self):
        with self.assertRaises(AccessError):
            self.m_a.with_user(self.lawyer).write({"approval_state": "approved"})
        with self.assertRaises(AccessError):
            self.m_a.with_user(self.lawyer).write({"approver_id": self.approver.id})
        created = self.env["legal.task"].with_user(self.lawyer).create({
            "name": "forged", "legal_company_id": self.client_a.id, "lawyer_id": self.lawyer.id,
            "approval_state": "approved", "approver_id": self.approver.id})
        self.assertEqual(created.approval_state, "draft")
        self.assertFalse(created.approver_id)

    def test_only_approvers_approve_and_not_their_own_request(self):
        self.m_a.with_user(self.lawyer).action_request_approval()
        with self.assertRaises(AccessError):
            self.m_a.with_user(self.lawyer).action_approve()
        approver_matter = self.make_matter(lawyer=self.approver, lawyer_ids=[(6, 0, [self.approver.id])])
        approver_matter.with_user(self.approver).action_request_approval()
        with self.assertRaises(UserError):
            approver_matter.with_user(self.approver).action_approve()
        self.m_a.with_user(self.approver).action_approve()
        self.assertEqual(self.m_a.approval_state, "approved")
        self.assertEqual(self.m_a.approver_id, self.approver)

    def test_settings_admin_is_not_a_legal_manager(self):
        system = self.env.ref("base.group_system")
        manager = self.env.ref(f"{M}.group_legal_manager")
        self.assertNotIn(manager, system.all_implied_ids)

    def test_only_responsible_changes_team_or_confidentiality(self):
        self.m_a.lawyer_ids = [(4, self.lawyer2.id)]
        with self.assertRaises(UserError):
            self.m_a.with_user(self.lawyer2).write({"confidential": True})
        self.m_a.with_user(self.lawyer).write({"confidential": True})
        self.assertTrue(self.m_a.confidential)

    def test_billing_cannot_read_privileged_notes(self):
        self.m_a.action_details = "privileged"
        billing_matter = self.m_a.with_user(self.billing)
        self.assertEqual(billing_matter.name, self.m_a.name)
        with self.assertRaises(AccessError):
            billing_matter.read(["action_details"])
        self.assertNotIn(self.m_secret, self.visible(self.billing))

    def test_only_managers_delete(self):
        with self.assertRaises(AccessError):
            self.m_a.with_user(self.lawyer).unlink()
        with self.assertRaises(AccessError):
            self.h_a.with_user(self.lawyer).unlink()
