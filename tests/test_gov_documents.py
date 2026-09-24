# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_gov_common import PNG, GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovDocuments(GovCase):

    def doc(self, matter, doc_type):
        return matter.document_ids.filtered(lambda d: d.document_type_id == doc_type)

    def test_matter_type_creates_the_checklist(self):
        matter = self.gov_matter()
        self.assertEqual(len(matter.document_ids), 3)
        self.assertEqual(set(matter.document_ids.mapped("state")), {"missing"})
        self.assertEqual(matter.missing_document_count, 2)

    def test_receiving_fills_the_dates(self):
        matter = self.gov_matter()
        card = self.doc(matter, self.dt_card)
        card.with_user(self.clerk).action_ldm_mark_received()
        self.assertEqual(card.state, "received")
        self.assertEqual(card.received_date, self.today)
        self.assertFalse(card.expiry_date, "A tax card has its own expiry date; nothing is guessed")
        accounts = self.doc(matter, self.dt_accounts)
        accounts.with_user(self.clerk).write({"state": "received"})
        self.assertEqual(accounts.expiry_date, self.today + timedelta(days=365),
                         "Final accounts are valid for a fixed period from receipt")
        self.assertEqual(matter.missing_document_count, 1)

    def test_confirmation_of_issuance_hands_the_matter_to_the_issuer(self):
        matter = self.gov_matter()
        card = self.doc(matter, self.dt_card)
        with self.assertRaises(UserError):
            card.with_user(self.clerk).action_ldm_request_verification()
        card.with_user(self.clerk).action_ldm_mark_received()
        card.with_user(self.clerk).action_ldm_request_verification()
        self.assertEqual(card.state, "awaiting_verification")
        self.assertEqual(matter.waiting_on, "verification")
        self.assertEqual(matter.date_submitted, self.today)
        card.with_user(self.clerk).write({"verification_ref": "QR-7781"})
        card.with_user(self.clerk).action_ldm_mark_verified()
        self.assertEqual(card.state, "verified")
        self.assertEqual(card.verification_date, self.today)
        self.assertEqual(matter.waiting_on, "us", "Nothing else awaits confirmation, so the ball is ours again")

    def test_take_the_copy_from_the_clients_records(self):
        attachment = self.env["ir.attachment"].create({"name": "card.png", "datas": PNG})
        held = self.vault_doc(self.dt_card, self.today + timedelta(days=200), attachment_id=attachment.id)
        self.vault_doc(self.dt_card, self.today - timedelta(days=5), number="OLD")
        matter = self.gov_matter()
        card = self.doc(matter, self.dt_card)
        card.write({"state": "missing", "company_document_id": False, "attachment_id": False})
        self.assertTrue(card.ldm_in_vault, "The row offers the copy the records hold")
        self.assertFalse(self.doc(matter, self.dt_clearance).ldm_in_vault)
        card.with_user(self.clerk).action_ldm_take_from_vault()
        self.assertEqual(card.state, "received")
        self.assertEqual(card.company_document_id, held, "The valid copy is taken, not the expired one")
        self.assertEqual(card.expiry_date, held.date_expiry)
        self.assertEqual(card.attachment_id.res_model, "legal.task")
        self.assertEqual(card.attachment_id.res_id, matter.id)
        clearance = self.doc(matter, self.dt_clearance)
        with self.assertRaises(UserError):
            clearance.with_user(self.clerk).action_ldm_take_from_vault()

    def test_opening_a_matter_ticks_what_the_vault_holds(self):
        self.vault_doc(self.dt_clearance, self.today + timedelta(days=90))
        matter = self.gov_matter()
        self.assertEqual(self.doc(matter, self.dt_clearance).state, "received")
        self.assertEqual(self.doc(matter, self.dt_card).state, "missing")

    def test_uploading_the_scan_means_received(self):
        matter = self.gov_matter()
        card = self.doc(matter, self.dt_card)
        card.with_user(self.clerk).write({"file_name": "card.png", "file_data": PNG})
        self.assertEqual(card.state, "received")
        self.assertEqual(card.attachment_id.name, "card.png")
        self.assertEqual(card.attachment_id.res_id, matter.id)

    def test_file_a_received_document_in_the_vault(self):
        matter = self.gov_matter()
        card = self.doc(matter, self.dt_card)
        card.write({"state": "received", "expiry_date": self.today + timedelta(days=300)})
        with self.assertRaises(UserError):
            card.with_user(self.clerk).action_ldm_save_to_vault()
        card.with_user(self.lawyer).action_ldm_save_to_vault()
        vault = card.company_document_id
        self.assertTrue(vault)
        self.assertEqual(vault.legal_company_id, self.client_a)
        self.assertEqual(vault.date_expiry, card.expiry_date)
        next_matter = self.gov_matter()
        self.assertEqual(self.doc(next_matter, self.dt_card).state, "received",
                         "The next matter of the same client takes it from the records")

    def test_daily_job_marks_expired_documents(self):
        matter = self.gov_matter()
        card = self.doc(matter, self.dt_card)
        card.write({"state": "received", "expiry_date": self.today - timedelta(days=1)})
        messages = len(matter.message_ids)
        self.env["legal.task.document"]._cron_ldm_mark_expired()
        self.assertEqual(card.state, "expired")
        self.assertEqual(matter.missing_document_count, 2)
        self.assertGreater(len(matter.message_ids), messages)
        self.env["legal.task.document"]._cron_ldm_mark_expired()
        self.assertEqual(len(matter.message_ids), messages + 1, "Running it again says nothing new")

    def test_state_has_the_confirmation_step(self):
        values = [v for v, _label in self.env["legal.task.document"]._fields["state"].selection]
        self.assertEqual(values, ["missing", "received", "awaiting_verification", "verified", "expired", "not_needed"])
