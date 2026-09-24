# -*- coding: utf-8 -*-
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.base.models.ir_cron import IrCron as BaseIrCron
from odoo.tests import tagged

from .common import M, LdmCase


@tagged("post_install", "-at_install", "ldm")
class TestCronLanguage(LdmCase):
    """What the daily jobs write and keep is written in the legal team's language."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.arabic = "ar_001" in {code for code, _name in cls.env["res.lang"].get_installed()}

    def test_team_language_is_the_majority_of_legal_staff(self):
        if not self.arabic:
            self.skipTest("Arabic is not installed in this database")
        staff = self.clerk | self.lawyer | self.lawyer2 | self.approver | self.manager
        staff.write({"lang": "ar_001"})
        self.assertEqual(self.env["ir.cron"].ldm_team_lang(), "ar_001")
        staff.write({"lang": "en_US"})
        self.assertEqual(self.env["ir.cron"].ldm_team_lang(), "en_US")

    def test_only_legal_jobs_are_concerned(self):
        legal = self.env.ref(f"{M}.ir_cron_ldm_vault_deadlines")
        self.assertTrue(legal.ldm_is_legal_job())
        other = self.env["ir.cron"].search([("id", "!=", legal.id)]).filtered(
            lambda cron: not cron.ir_actions_server_id.model_id.model.startswith(("legal.", "ldm.")))[:1]
        if other:
            self.assertFalse(other.ldm_is_legal_job())

    def test_a_job_names_a_deadline_in_arabic(self):
        if not self.arabic:
            self.skipTest("Arabic is not installed in this database")
        self.env["res.lang"]._activate_lang("ar_001")
        (self.clerk | self.lawyer | self.lawyer2 | self.approver | self.manager).write({"lang": "ar_001"})
        doc_type = self.env.ref(f"{M}.ldm_doctype_tax_clearance")
        today = fields.Date.context_today(self.env.user)
        doc = self.env["legal.company.document"].create({
            "legal_company_id": self.client_a.id, "document_type_id": doc_type.id, "number": "TC-1",
            "date_issued": today - timedelta(days=300), "date_expiry": today + timedelta(days=5)})
        self.env["legal.deadline"].sudo().search([("source_model", "=", "legal.company.document"),
                                                  ("source_id", "=", doc.id)]).unlink()
        cron = self.env.ref(f"{M}.ir_cron_ldm_vault_deadlines")
        # The scheduler and "Run manually" both reach a job through _callback, which
        # commits; the base runner is replaced by one that records the language.
        seen = {}

        def base_callback(cron_self, cron_name, server_action_id):
            seen["lang"] = cron_self.env.context.get("lang")

        with patch.object(BaseIrCron, "_callback", base_callback):
            cron.with_context(lang=None)._callback(cron.cron_name, cron.ir_actions_server_id.id)
        self.assertEqual(seen["lang"], "ar_001")
        self.env["legal.company.document"].with_context(lang=seen["lang"])._cron_ldm_vault_deadlines()
        deadline = self.env["legal.deadline"].sudo().search([("source_model", "=", "legal.company.document"),
                                                             ("source_id", "=", doc.id)])
        self.assertTrue(deadline)
        arabic_type = doc_type.with_context(lang="ar_001").name
        self.assertIn(arabic_type, deadline.with_context(lang="en_US").name)
        self.assertNotIn("Renew", deadline.name)

    def test_shipped_matter_type_steps_read_in_arabic(self):
        if not self.arabic:
            self.skipTest("Arabic is not installed in this database")
        self.env["legal.task.template.step"]._ldm_translate_shipped_steps()
        template = self.env.ref(f"{M}.ldm_template_execution").with_context(lang="ar_001")
        self.assertIn("فتح الإضبارة التنفيذية في مديرية التنفيذ", template.step_ids.mapped("name"))
        self.assertIn("Open the file at the execution directorate",
                      template.with_context(lang="en_US").step_ids.mapped("name"))
        # a matter opened in Arabic gets Arabic steps
        task = self.env["legal.task"].browse(self.env["legal.task"].with_user(self.lawyer).with_context(
            lang="ar_001").create_from_template({"template_id": template.id, "legal_company_id": self.client_a.id}))
        self.assertIn("فتح الإضبارة التنفيذية في مديرية التنفيذ", task.step_ids.mapped("name"))
