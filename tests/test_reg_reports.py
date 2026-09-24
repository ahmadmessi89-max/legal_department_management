# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.service.model import call_kw
from odoo.tests import tagged

from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegReports(RegCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Task = cls.env["legal.task"]
        cls.government = Task.browse(Task.create_from_template({
            "template_id": cls.t_government.id, "legal_company_id": cls.client_a.id,
            "department_id": cls.registry_body.id, "name": "Annual registry renewal"}))
        cls.lawsuit = Task.browse(Task.create_from_template({
            "template_id": cls.t_lawsuit.id, "legal_company_id": cls.client_b.id, "department_id": cls.court.id,
            "name": "Debt recovery against Tigris Trading", "our_role": "plaintiff",
            "key_date": fields.Date.to_string(fields.Date.context_today(Task) + timedelta(days=4))}))
        cls.lawsuit.matter_value = 45000000
        cls.env["legal.task.expense"].create({"task_id": cls.government.id, "name": "Registry fee",
                                              "amount": 25000})

    def test_follow_up_sheet(self):
        html = self.html("report_legal_task_template", self.government.ids, user=self.lawyer)
        self.assertIn(self.government.task_number, html)
        self.assertIn("Annual registry renewal", html)
        for step in self.government.step_ids:
            self.assertIn(step.name, html)
        self.assertIn("At the counter", html)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("25,000", html)
        # Printed by billing, who may not read the notes: still renders.
        self.government.sudo().action_details = "Secret instruction"
        html = self.html("report_legal_task_template", self.government.ids, user=self.billing)
        self.assertNotIn("Secret instruction", html)
        html = self.html("report_legal_task_template", self.government.ids, user=self.lawyer)
        self.assertIn("Secret instruction", html)

    def test_client_file_prints_every_visible_matter(self):
        html = self.html("report_legal_company_template", self.client_a.ids, user=self.lawyer)
        self.assertIn("Annual registry renewal", html)
        self.assertIn("LDM Test Companies Registry", html)
        self.assertNotIn("Debt recovery", html)

    def test_client_file_empty_filter_prints_nothing(self):
        Wizard = self.env["legal.company.report.wizard"].with_user(self.lawyer).with_context(
            active_model="legal.company", active_id=self.client_a.id)
        defaults = Wizard.default_get(["company_id", "filter_state", "show_company_info"])
        self.assertEqual(defaults["company_id"], self.client_a.id)
        self.assertEqual(Wizard.new(defaults).company_id, self.client_a)
        wizard = Wizard.create({"filter_state": "closed"})
        action = wizard.action_print_report()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["data"]["state"], "closed")
        html = self.html("report_legal_company_template", [], data=action["data"], user=self.lawyer)
        self.assertIn("No matter matches these options.", html)
        self.assertNotIn("Annual registry renewal", html)
        # The same dialog with a matching filter.
        wizard.filter_state = "open"
        html = self.html("report_legal_company_template", [], data=wizard._ldm_report_data(), user=self.lawyer)
        self.assertIn("Annual registry renewal", html)

    def test_oversight_grouped_by_client(self):
        Wizard = self.env["legal.general.report.wizard"].with_user(self.manager)
        wizard = Wizard.create({"filter_state": "open", "group_by_company": True})
        data = wizard.action_print_general_report()["data"]
        html = self.html("report_legal_general_overview_template", [], data=data, user=self.manager)
        self.assertIn("LDM Client A", html)
        self.assertIn("LDM Client B", html)
        self.assertIn("Debt recovery against Tigris Trading", html)
        wizard.group_by_company = False
        html = self.html("report_legal_general_overview_template", [], data=wizard._ldm_report_data(),
                         user=self.manager)
        self.assertIn("Annual registry renewal", html)

    def test_oversight_from_the_selection(self):
        Wizard = self.env["legal.general.report.wizard"].with_user(self.manager).with_context(
            active_model="legal.task", active_ids=self.lawsuit.ids)
        defaults = Wizard.default_get(["filter_task_ids", "filter_state", "task_domain"])
        self.assertEqual(defaults["filter_state"], "all")
        wizard = Wizard.create({})
        self.assertEqual(wizard.filter_task_ids, self.lawsuit)
        html = self.html("report_legal_general_overview_template", [], data=wizard._ldm_report_data(),
                         user=self.manager)
        self.assertIn("Debt recovery", html)
        self.assertNotIn("Annual registry renewal", html)
        # The whole filtered list (select all).
        Wizard = Wizard.with_context(active_ids=[], active_domain=[("legal_company_id", "=", self.client_a.id)])
        wizard = Wizard.create({})
        html = self.html("report_legal_general_overview_template", [], data=wizard._ldm_report_data(),
                         user=self.manager)
        self.assertIn("Annual registry renewal", html)
        self.assertNotIn("Debt recovery", html)
        # Nothing matches: nothing is printed.
        wizard.write({"filter_state": "closed"})
        html = self.html("report_legal_general_overview_template", [], data=wizard._ldm_report_data(),
                         user=self.manager)
        self.assertIn("No matter matches these options.", html)

    def test_oversight_respects_what_the_reader_may_see(self):
        wizard = self.env["legal.general.report.wizard"].with_user(self.lawyer).create({"filter_state": "all"})
        html = self.html("report_legal_general_overview_template", [], data=wizard._ldm_report_data(),
                         user=self.lawyer)
        self.assertIn("Annual registry renewal", html)
        self.assertNotIn("Debt recovery", html)

    def monthly(self, data, user=None):
        Report = self.env["report.legal_department_management.report_ldm_monthly_status"]
        return Report.with_user(user or self.manager)._get_report_values([], data=data)

    @staticmethod
    def side(values, key):
        return next(row for row in values["side_rows"] if row["key"] == key)

    def test_monthly_status(self):
        today = fields.Date.context_today(self.lawsuit)
        currency = self.lawsuit.currency_id
        Wizard = self.env["legal.monthly.report.wizard"].with_user(self.manager)
        defaults = Wizard.default_get(["date_from", "date_to"])
        self.assertLess(defaults["date_from"], defaults["date_to"])
        wizard = Wizard.create({"date_from": today.replace(day=1), "date_to": today})
        data = wizard.action_print()["data"]
        self.assertEqual(data["date_to"], fields.Date.to_string(today))
        # Counted from the database as it is (other data included): compare
        # before and after adding one lawsuit and one judgment.
        before = self.monthly(data)
        Task = self.env["legal.task"]
        extra = Task.browse(Task.create_from_template({
            "template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id, "department_id": self.court.id,
            "name": "Recovery of the retention money", "our_role": "plaintiff"}))
        extra.matter_value = 7000000
        self.env["legal.judgment"].create({"task_id": extra.id, "date": today, "result": "for",
                                           "amount_awarded": 3000000, "department_id": self.court.id})
        after = self.monthly(data)
        self.assertEqual(self.side(after, "for")["open"], self.side(before, "for")["open"] + 1)
        self.assertEqual(dict(self.side(after, "for")["value"]).get(currency, 0.0),
                         dict(self.side(before, "for")["value"]).get(currency, 0.0) + 7000000)
        self.assertEqual(sum(r["count"] for r in after["judgment_rows"]),
                         sum(r["count"] for r in before["judgment_rows"]) + 1)
        self.assertIn(self.registry_body.name, [row["title"] for row in after["body_rows"]])
        html = self.html("report_ldm_monthly_status", [], data=data, user=self.manager)
        self.assertIn("Brought by us", html)
        self.assertIn("LDM Test Companies Registry", html)
        html = self.html("report_ldm_monthly_status", [], data=data, user=self.auditor)
        self.assertIn("Brought by us", html)

    def test_register_book_and_letter(self):
        letter = self.Letter.with_user(self.clerk).create({
            "name": "Request for the registry extract", "direction": "outgoing", "date": self.d("2031-06-01"),
            "department_id": self.registry_body.id, "body_html": "<p>Please issue the extract.</p>",
            "cc_lines": "The client\nThe file"})
        letter.action_register()
        void = self.Letter.with_user(self.clerk).create({"name": "Wrong letter", "direction": "outgoing",
                                                         "date": self.d("2031-06-02")})
        void.action_register()
        void._ldm_void("Addressed to the wrong body")
        html = self.html("report_ldm_letter", letter.ids, user=self.clerk)
        self.assertIn("2031/1", html)
        self.assertIn("Please issue the extract.", html)
        self.assertIn("LDM Test Companies Registry", html)
        self.assertIn("The file", html)
        # The list's header button: called the way the web client calls it.
        action = call_kw(self.Letter.with_user(self.clerk), "action_ldm_register_book", [[]], {})
        self.assertEqual(action["res_model"], "legal.register.book.wizard")
        Wizard = self.env["legal.register.book.wizard"].with_user(self.clerk)
        wizard = Wizard.create({"date_from": self.d("2031-01-01"), "date_to": self.d("2031-12-31"),
                                "direction": "outgoing"})
        data = wizard.action_print()["data"]
        html = self.html("report_ldm_register_book", [], data=data, user=self.clerk)
        self.assertIn("Request for the registry extract", html)
        self.assertIn("Addressed to the wrong body", html)
        self.assertIn("o_ldm_r_void", html)
        html = self.html("report_ldm_register_book", [], data=data, user=self.auditor)
        self.assertIn("Request for the registry extract", html)

    def test_opinion_memo(self):
        matter = self.make_matter(template_id=self.env.ref(f"{M}.ldm_template_opinion").id, state="in_progress",
                                  question="Can we terminate?", opinion_html="<p>Yes.</p>")
        matter.with_user(self.manager).action_issue_opinion()
        html = self.html("report_ldm_opinion_memo", matter.ids, user=self.manager)
        self.assertIn(matter.opinion_number, html)
        self.assertIn("Can we terminate?", html)
