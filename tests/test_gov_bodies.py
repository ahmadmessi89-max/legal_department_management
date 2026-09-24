# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .test_gov_common import GovCase


@tagged("post_install", "-at_install", "ldm")
class TestGovBodies(GovCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.finance = cls.env["legal.ministry"].create({"name": "وزارة الاختبار المالية", "code": "LDMT-FIN"})
        cls.gct = cls.env["legal.department"].create({
            "name": "الهيئة العامة لضرائب الاختبار", "ministry_id": cls.finance.id, "code": "LDMT-GCT"})

    def picker(self, term, user=None):
        Department = self.env["legal.department"].with_user(user or self.clerk)
        return [record_id for record_id, _name in Department.name_search(term, limit=50)]

    def test_picker_finds_a_body_by_its_ministry(self):
        self.assertIn(self.registry_body.id, self.picker("Ministry of Trade"))
        self.assertIn(self.gct.id, self.picker("وزارة الاختبار"))

    def test_picker_ignores_hamza_taa_marbuta_and_articles(self):
        # stored with taa marbuta and hamza-less alef; typed with haa, and without the article
        self.assertIn(self.gct.id, self.picker("الهيئه العامه لضرائب"))
        self.assertIn(self.gct.id, self.picker("هيئة ضرائب الاختبار"))
        self.assertIn(self.gct.id, self.picker("  العامة   لضرائب  "))
        self.assertNotIn(self.gct.id, self.picker("هيئة الكمارك"))

    def test_picker_finds_by_code(self):
        self.assertIn(self.gct.id, self.picker("ldmt-gct"))

    def test_ministry_is_secondary_text_in_the_dropdown(self):
        plain = self.gct.display_name
        formatted = self.gct.with_context(formatted_display_name=True).display_name
        self.assertEqual(plain, "الهيئة العامة لضرائب الاختبار")
        self.assertIn("\n--وزارة الاختبار المالية--", formatted)
        court = self.court.with_context(formatted_display_name=True)
        self.court.governorate = "baghdad"
        self.assertIn("Baghdad", court.display_name)

    def test_search_key_follows_a_renamed_ministry(self):
        self.finance.name = "وزارة التجربة"
        self.assertIn(self.gct.id, self.picker("التجربة"))

    def test_ministry_picker_is_normalised_too(self):
        found = [i for i, _n in self.env["legal.ministry"].name_search("وزاره الاختبار الماليه")]
        self.assertIn(self.finance.id, found)

    def test_open_matters_and_services(self):
        matter = self.gov_matter()
        self.assertEqual(self.tax_body.open_task_count, 1)
        self.assertEqual(self.tax_body.template_count, 1)
        action = self.tax_body.action_view_open_tasks()
        self.assertEqual(action["context"].get("search_default_filter_open"), 1)
        self.assertIn(("department_id", "=", self.tax_body.id), action["domain"])
        self.assertTrue(matter)

    def test_changing_kind_clears_court_fields(self):
        form_record = self.env["legal.department"].new({"name": "x", "body_kind": "court", "court_degree": "appeal",
                                                        "parent_id": self.court.id})
        form_record.body_kind = "government"
        form_record._onchange_body_kind()
        self.assertFalse(form_record.court_degree)
        self.assertFalse(form_record.parent_id)

    def test_directory_is_read_only(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_body_directory")
        self.assertIn("kanban", action["view_mode"])
        for view_type in ("kanban", "list", "form"):
            arch = self.env["legal.department"].with_user(self.clerk).get_views(
                [(self.env.ref(f"legal_department_management.view_ldm_body_directory_{view_type}").id, view_type)]
            )["views"][view_type]["arch"]
            self.assertIn('create="0"', arch.replace("'", '"').replace('create="false"', 'create="0"'))
