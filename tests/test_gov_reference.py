# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import tagged

from ..models import gov_reference_data as LIB
from ..models.ldm_text import normalize
from .test_gov_common import GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovReference(GovCase):

    def counts(self):
        env = self.env(context=dict(self.env.context, active_test=False))
        return {model: env[model].search_count([]) for model in (
            "legal.ministry", "legal.department", "legal.department.contact", "legal.task.template",
            "legal.task.template.step", "legal.task.template.document", "legal.document.type")}

    def neutralise(self, model, names, codes=(), code_field="code"):
        """Rename records that already carry a library name or code (a database
        where the library was loaded before), so the test starts from SAG's shape."""
        keys = {normalize(n) for n in names} | {normalize(n, drop_article=True) for n in names}
        for record in self.env[model].with_context(active_test=False).search([]):
            if (record[code_field] or "") in codes or normalize(record.name) in keys \
                    or normalize(record.name, drop_article=True) in keys:
                record.write({"name": f"Neutralised {model} {record.id}", code_field: False})

    def load(self):
        return self.env["legal.reference.library"].ldm_load()

    def test_loading_twice_creates_nothing_the_second_time(self):
        self.load()
        after_first = self.counts()
        report = self.load()
        self.assertEqual(self.counts(), after_first)
        self.assertEqual(sum(created for created, _kept in report.values()), 0)
        self.assertEqual(report["services"][1], len(LIB.SERVICES))

    def test_merges_into_bodies_spelled_differently(self):
        self.neutralise("legal.ministry", ["وزارة المالية"], ("IQ-MOF",))
        self.neutralise("legal.department", ["الهيئة العامة للضرائب"], ("IQ-MOF-GCT",))
        # SAG-shaped spellings: taa marbuta written as haa, hamza dropped, doubled spaces
        finance = self.env["legal.ministry"].create({"name": "وزارة  الماليه"})
        tax = self.env["legal.department"].create({"name": "الهيئه العامه  للضرائب", "ministry_id": finance.id,
                                                   "phone": "0770 000 0000"})
        self.load()
        ministries = self.env["legal.ministry"].with_context(active_test=False).search([])
        self.assertEqual(len(ministries.filtered(lambda m: normalize(m.name) == normalize("وزارة المالية"))), 1)
        self.assertEqual(finance.code, "IQ-MOF")
        bodies = self.env["legal.department"].with_context(active_test=False).search([])
        self.assertEqual(len(bodies.filtered(lambda d: normalize(d.name) == normalize("الهيئة العامة للضرائب"))), 1)
        self.assertEqual(tax.code, "IQ-MOF-GCT")
        self.assertEqual(tax.phone, "0770 000 0000", "What the user typed is kept")
        self.assertEqual(tax.target_days, 15, "Empty fields are filled")
        service = self.env["legal.task.template"].search([("ldm_ref_code", "=", "SVC-TAX-C")])
        self.assertEqual(service.department_id, tax)

    def test_sag_courts_are_classified_and_linked(self):
        self.neutralise("legal.ministry", ["مجلس القضاء الأعلى"], ("IQ-SJC",))
        self.neutralise("legal.department", ["محكمة بداءة الكرخ", "محكمة استئناف بغداد/الكرخ الاتحادية",
                                             "محكمة التمييز الاتحادية"], ("IQ-SJC-FI-KRK", "IQ-SJC-APP-KRK",
                                                                          "IQ-SJC-CASS"))
        council = self.env["legal.ministry"].create({"name": "مجلس القضاء الاعلى"})
        karkh = self.env["legal.department"].create({"name": "محكمة بداءة الكرخ", "ministry_id": council.id})
        self.assertEqual(karkh.body_kind, "government")
        self.load()
        self.assertEqual(council.body_kind, "judicial")
        self.assertEqual(karkh.body_kind, "court")
        self.assertEqual(karkh.court_degree, "first_instance")
        self.assertEqual(karkh.parent_id.code, "IQ-SJC-APP-KRK")
        self.assertEqual(karkh.parent_id.parent_id.code, "IQ-SJC-CASS")
        self.assertEqual(karkh.parent_id.court_degree, "appeal")

    def test_services_carry_steps_visits_and_documents(self):
        self.load()
        service = self.env["legal.task.template"].search([("ldm_ref_code", "=", "SVC-TAX-C")])
        self.assertEqual(len(service), 1)
        self.assertEqual(service.kind, "government")
        self.assertTrue(service.track_coverage)
        self.assertEqual(len(service.step_ids), 4)
        self.assertEqual(service.step_ids.sorted("sequence")[0].offset_from, "start")
        self.assertEqual(len(service.step_ids.filtered("is_visit")), 3)
        self.assertEqual(set(service.document_ids.document_type_id.mapped("code")),
                         {"tax_card", "final_accounts", "incorporation_certificate", "runner_authorisation"})
        if self.env["res.lang"]._lang_get("ar_001"):
            self.assertEqual(service.with_context(lang="ar_001").name, "براءة ذمة للشركات")
            self.assertEqual(service.with_context(lang="en_US").name, "Tax clearance for companies")
        matter = self.env["legal.task"].browse(self.env["legal.task"].with_user(self.lawyer).create_from_template(
            {"template_id": service.id, "legal_company_id": self.client_a.id}))
        self.assertEqual(matter.department_id, service.department_id)
        self.assertEqual(len(matter.step_ids.filtered("is_visit")), 3)
        self.assertEqual(len(matter.document_ids), 4)
        self.assertEqual(matter.ldm_target_days, 15, "The body's usual answer time applies")

    def test_uses_the_shipped_document_types(self):
        self.load()
        card = self.env.ref("legal_department_management.ldm_doctype_tax_card")
        self.assertEqual(self.env["legal.document.type"].search_count([("code", "=", "tax_card")]), 1)
        if self.env["res.lang"]._lang_get("ar_001"):
            self.assertEqual(card.with_context(lang="ar_001").name, "البطاقة الضريبية")

    def test_settings_button(self):
        with self.assertRaises(AccessError):
            self.env["res.config.settings"].with_user(self.lawyer).action_ldm_load_reference_data()
        action = self.env["res.config.settings"].with_user(self.manager).action_ldm_load_reference_data()
        self.assertEqual(action["tag"], "display_notification")
        again = self.env["res.config.settings"].with_user(self.manager).action_ldm_load_reference_data()
        self.assertEqual(again["params"]["type"], "info")
