# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo.tests import tagged

from .test_gov_common import GovCase

VAULT = "legal.company.document"


@tagged("post_install", "-at_install", "ldm")
class TestGovVault(GovCase):

    def deadlines(self, doc, states=("open",)):
        return self.env["legal.deadline"].search([("source_model", "=", VAULT), ("source_id", "=", doc.id),
                                                  ("state", "in", states)])

    def test_a_document_expiring_in_20_days_has_one_deadline(self):
        doc = self.vault_doc(self.dt_clearance, self.today + timedelta(days=20))
        deadline = self.deadlines(doc)
        self.assertEqual(len(deadline), 1)
        self.assertEqual(deadline.kind, "expiry")
        self.assertEqual(deadline.legal_company_id, self.client_a)
        self.assertFalse(deadline.task_id)
        self.assertEqual(deadline.date_safe, doc.date_expiry)
        self.assertEqual(deadline.user_id, self.client_a.lawyer_id)
        Vault = self.env[VAULT]
        Vault._cron_ldm_vault_deadlines()
        Vault._cron_ldm_vault_deadlines()
        self.assertEqual(len(self.deadlines(doc, ("open", "done", "missed", "awaiting_service"))), 1,
                         "The daily job is idempotent")
        self.assertEqual(doc.deadline_id, deadline)

    def test_a_far_expiry_has_no_deadline_yet(self):
        doc = self.vault_doc(self.dt_clearance, self.today + timedelta(days=200))
        self.assertFalse(self.deadlines(doc))
        self.assertEqual(doc.state, "valid")

    def test_moving_the_expiry_moves_the_deadline(self):
        doc = self.vault_doc(self.dt_clearance, self.today + timedelta(days=20))
        doc.date_expiry = self.today + timedelta(days=25)
        deadline = self.deadlines(doc)
        self.assertEqual(len(deadline), 1)
        self.assertEqual(deadline.date_safe, self.today + timedelta(days=25))

    def test_renewal_closes_the_deadline(self):
        doc = self.vault_doc(self.dt_clearance, self.today + timedelta(days=20))
        deadline = self.deadlines(doc)
        doc.date_expiry = self.today + timedelta(days=365)
        self.assertEqual(deadline.state, "done")
        self.assertFalse(self.deadlines(doc))

    def test_a_newer_copy_supersedes_the_old_one(self):
        old = self.vault_doc(self.dt_clearance, self.today + timedelta(days=10))
        deadline = self.deadlines(old)
        self.vault_doc(self.dt_clearance, self.today + timedelta(days=370), number="N-2")
        self.env[VAULT]._cron_ldm_vault_deadlines()
        self.assertEqual(deadline.state, "done")

    def test_archiving_cancels_the_deadline(self):
        doc = self.vault_doc(self.dt_clearance, self.today + timedelta(days=20))
        deadline = self.deadlines(doc)
        doc.active = False
        self.assertEqual(deadline.state, "cancelled")

    def test_an_expired_document_is_not_given_a_second_deadline(self):
        doc = self.vault_doc(self.dt_clearance, self.today + timedelta(days=5))
        deadline = self.deadlines(doc)
        deadline.state = "missed"
        self.env[VAULT]._cron_ldm_vault_deadlines()
        self.assertEqual(len(self.deadlines(doc, ("open", "missed"))), 1)

    def test_expiry_from_the_type_when_issued(self):
        doc = self.env[VAULT].create({"legal_company_id": self.client_a.id, "document_type_id": self.dt_accounts.id,
                                      "date_issued": self.today})
        self.assertEqual(doc.date_expiry, self.today + timedelta(days=365))

    def test_valid_on_a_date(self):
        fresh = self.env.ref("legal_department_management.ldm_doctype_electricity_bill")
        bill = self.env[VAULT].create({"legal_company_id": self.client_a.id, "document_type_id": fresh.id,
                                       "date_issued": self.today - timedelta(days=60), "date_expiry": False})
        bill.date_expiry = False
        self.assertTrue(bill._ldm_valid_on(self.today))
        self.assertFalse(bill._ldm_valid_on(self.today + timedelta(days=60)), "A bill goes stale after 90 days")
        certificate = self.vault_doc(self.env.ref("legal_department_management.ldm_doctype_incorporation_certificate"))
        self.assertTrue(certificate._ldm_valid_on(self.today + timedelta(days=3000)))

    def test_client_reminders_are_idempotent(self):
        doc = self.vault_doc(self.dt_chamber, self.today + timedelta(days=12))
        activity_type = self.env.ref("legal_department_management.ldm_activity_company_expiry")
        Client = self.env["legal.company"]
        Client._ldm_run_company_reminders()
        Client._ldm_run_company_reminders()
        activities = self.client_a.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities.user_id, self.lawyer)
        self.assertEqual(activities.date_deadline, doc.date_expiry)

    def test_dossier_counts_expiring_documents(self):
        self.vault_doc(self.dt_chamber, self.today + timedelta(days=12))
        self.vault_doc(self.dt_card, self.today + timedelta(days=300))
        self.assertEqual(self.client_a.expiring_document_count, 1)
        action = self.client_a.action_view_vault()
        self.assertIn(("legal_company_id", "=", self.client_a.id), action["domain"])
