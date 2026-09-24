# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo.tests import tagged

from .test_gov_common import GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovCoverage(GovCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.t_service.track_coverage = True

    def rows(self, client, user=None):
        Coverage = self.env["legal.company.coverage"].with_user(user) if user else self.env["legal.company.coverage"]
        return Coverage.search([("legal_company_id", "=", client.id), ("template_id", "=", self.t_service.id)])

    def test_rows_exist_for_services_nobody_started(self):
        row = self.rows(self.client_b)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.coverage_state, "due")
        self.assertTrue(row.is_due)
        self.assertFalse(row.last_task_id)

    def test_done_this_year_open_and_not_done(self):
        done = self.gov_matter(self.client_a)
        done._ldm_close("completed", "")
        self.env.flush_all()
        row_a = self.rows(self.client_a)
        self.assertEqual(row_a.coverage_state, "done")
        self.assertEqual(row_a.last_done_date, self.today)
        self.assertEqual(row_a.last_task_id, done)
        self.gov_matter(self.client_b)
        self.env.flush_all()
        self.assertEqual(self.rows(self.client_b).coverage_state, "open")

    def test_last_years_filing_is_due_again(self):
        old = self.gov_matter(self.client_a)
        old._ldm_close("completed", "")
        old.write({"date_closed": self.today.replace(year=self.today.year - 1)})
        self.env.flush_all()
        row = self.rows(self.client_a)
        self.assertEqual(row.coverage_state, "due")
        self.assertEqual(row.last_done_date, old.date_closed)

    def test_untracked_services_have_no_rows(self):
        self.t_service.track_coverage = False
        self.env.flush_all()
        self.assertFalse(self.rows(self.client_a))

    def test_start_opens_the_quick_create_prefilled(self):
        row = self.rows(self.client_b)
        action = row.action_ldm_start()
        self.assertEqual(action["res_model"], "legal.task.create.wizard")
        self.assertEqual(action["context"]["default_legal_company_id"], self.client_b.id)
        self.assertEqual(action["context"]["default_template_id"], self.t_service.id)

    def test_rows_follow_the_clients_a_lawyer_works_for(self):
        self.assertTrue(self.rows(self.client_a, self.lawyer))
        self.assertFalse(self.rows(self.client_b, self.lawyer))
        self.assertTrue(self.rows(self.client_b, self.manager))
        self.assertTrue(self.rows(self.client_b, self.auditor))

    def test_dossier_tab(self):
        self.assertIn(self.t_service, self.client_a.coverage_ids.template_id)


@tagged("post_install", "-at_install", "ldm")
class TestGovReadiness(GovCase):

    def test_documents_valid_on_the_closing_date(self):
        closing = self.today + timedelta(days=40)
        self.vault_doc(self.dt_card, closing + timedelta(days=100))
        self.vault_doc(self.dt_clearance, closing - timedelta(days=5))
        action = self.client_a.with_user(self.lawyer).action_ldm_readiness()
        Wizard = self.env["legal.readiness.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["legal_company_id", "date", "template_id"])
        self.assertEqual(defaults["legal_company_id"], self.client_a.id)
        draft = Wizard.new(dict(defaults, date=closing, template_id=self.t_service.id))
        by_type = {line.document_type_id: line for line in draft.line_ids}
        self.assertEqual(by_type[self.dt_card].readiness, "valid")
        self.assertEqual(by_type[self.dt_clearance].readiness, "expires")
        self.assertEqual(by_type[self.dt_accounts].readiness, "missing")
        self.assertEqual((draft.ready_count, draft.total_count), (1, 3))
        self.assertIn("1", draft.summary)
        wizard = Wizard.create(dict(defaults, date=self.today, template_id=self.t_service.id))
        self.assertEqual(wizard.ready_count, 2, "Today the clearance is still valid")

    def test_without_a_pack_it_lists_what_the_client_holds(self):
        self.vault_doc(self.dt_chamber, self.today + timedelta(days=5))
        wizard = self.env["legal.readiness.wizard"].create({"legal_company_id": self.client_a.id,
                                                           "date": self.today + timedelta(days=10)})
        self.assertEqual(wizard.line_ids.document_type_id, self.dt_chamber)
        self.assertEqual(wizard.line_ids.readiness, "expires")
