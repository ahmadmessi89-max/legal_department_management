# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import M
from .ws_common import WsCase


@tagged("post_install", "-at_install", "ldm")
class TestWsCockpit(WsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.suit = cls.open_matter(name="Supply claim", kind="litigation", department_id=cls.court.id,
                                   court_stage="appeal")
        cls.session = cls.Hearing.create({"task_id": cls.suit.id, "date": cls.day(4), "time": 9.5,
                                          "attending_user_id": cls.lawyer.id})
        cls.step(cls.suit, "Prepare the appeal memo", 6)
        # Court stage lines are the source of truth (the litigation stream keeps
        # court_stage on the matter in step with the latest line).
        cls.env["legal.court.stage"].create({"task_id": cls.suit.id, "sequence": 10, "stage": "first_instance",
                                             "case_number": "1834/b/2026"})
        cls.env["legal.court.stage"].create({"task_id": cls.suit.id, "sequence": 20, "stage": "appeal",
                                             "case_number": "412/s/2026"})
        cls.gov = cls.open_matter(name="Tax clearance", kind="government", department_id=cls.registry_body.id)
        cls.visit = cls.step(cls.gov, "Submit at the counter", 1, is_visit=True, department_id=cls.registry_body.id)
        Document = cls.env["legal.task.document"]
        Document.create({"task_id": cls.gov.id, "name": "Certificate", "state": "received"})
        Document.create({"task_id": cls.gov.id, "name": "Tax card", "state": "missing"})
        Document.create({"task_id": cls.gov.id, "name": "Old letter", "state": "not_needed"})

    def cockpit(self, task, user=None):
        self.env.invalidate_all()
        return task.with_user(user or self.lawyer).ldm_cockpit

    def test_next_item_and_vitals(self):
        payload = self.cockpit(self.suit)
        self.assertEqual(payload["next"]["kind"], "hearing")
        self.assertEqual(payload["next"]["id"], self.session.id)
        self.assertTrue(payload["next"]["can_act"])
        self.assertEqual(payload["next"]["days"], 4)
        vitals = {vital["key"]: vital for vital in payload["vitals"]}
        self.assertEqual(vitals["next"]["days"], 4)
        self.assertIn("sessions", vitals)
        self.assertNotIn("steps", vitals)  # a lawsuit shows its stages, not a step count
        gov = {vital["key"]: vital for vital in self.cockpit(self.gov)["vitals"]}
        self.assertEqual(gov["documents"]["value"], "1 of 2")
        self.assertEqual(gov["documents"]["tone"], "warning")
        self.assertEqual(gov["documents"]["tab"], "documents")
        self.assertEqual(self.cockpit(self.gov)["next"]["kind"], "visit")

    def test_phase_rail_for_lawsuits(self):
        phases = self.cockpit(self.suit)["phases"]
        self.assertEqual([p["key"] for p in phases], ["first_instance", "appeal", "cassation", "execution"])
        self.assertEqual([p["status"] for p in phases], ["done", "current", "todo", "todo"])
        self.assertEqual(phases[0]["case_number"], "1834/b/2026")
        self.assertEqual(self.cockpit(self.gov)["phases"], [])

    def test_approval_banner_replaces_the_card(self):
        template = self.env.ref(f"{M}.ldm_template_contract_review")
        template.requires_approval = True
        Task = self.env["legal.task"]
        task = Task.browse(Task.with_user(self.lawyer).create_from_template(
            {"template_id": template.id, "legal_company_id": self.client_a.id}))
        payload = self.cockpit(task)
        self.assertEqual(payload["approval"]["state"], "to_approve")
        self.assertFalse(payload["approval"]["can_decide"])
        self.assertFalse(payload["next"])
        self.assertTrue(self.cockpit(task, self.approver)["approval"]["can_decide"])
        self.env.invalidate_all()
        preview = task.with_user(self.approver).ldm_approval_preview()
        self.assertEqual(preview["requested_by"], self.lawyer.name)
        self.assertTrue(preview["can_decide"])
        self.assertEqual(len(preview["steps"]), len(template.step_ids))

    def test_auditor_reads_a_read_only_cockpit(self):
        payload = self.cockpit(self.suit, self.auditor)
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["next"]["can_act"])

    def test_form_budgets(self):
        """At most two header buttons show at once; the rest go in the ⋯ menu."""
        arch = self.env["legal.task"].with_user(self.lawyer).get_views([(False, "form")])["views"]["form"]["arch"]
        self.assertIn('js_class="ldm_matter_form"', arch)
        for widget in ("ldm_next_step", "ldm_matter_vitals", "ldm_phase_rail", "ldm_advanced_toggle"):
            self.assertIn(widget, arch)
        self.assertIn('widget="ldm_step_checklist"', arch)
        self.assertIn('widget="ldm_document_checklist"', arch)
        auditor = self.env["legal.task"].with_user(self.auditor).get_views([(False, "form")])["views"]["form"]["arch"]
        self.assertNotIn('class="o_ldm_more"', auditor)
        self.assertNotIn("action_set_cancelled", auditor)

    def test_dossier_counts_as_the_reader(self):
        self.open_matter(name="Second registry file", department_id=self.registry_body.id)
        closed = self.open_matter(name="Old registry file", department_id=self.registry_body.id)
        closed._ldm_close("completed", "")
        # A confidential matter of the same client, handled by another lawyer.
        self.make_matter(client=self.client_a, lawyer=self.lawyer2, name="Secret", confidential=True,
                         department_id=self.court.id, state="in_progress")
        client = self.client_a.with_user(self.lawyer)
        client.invalidate_recordset(["ldm_dossier"])
        dossier = client.ldm_dossier
        bodies = {body["id"]: body for body in dossier["bodies"]}
        self.assertEqual(bodies[self.registry_body.id]["open"], 2)
        self.assertEqual(bodies[self.registry_body.id]["done"], 1)
        self.assertEqual(bodies[self.court.id]["open"], 1)  # the confidential one is not counted
        self.assertLessEqual(len(dossier["now"]), 5)
        self.assertEqual(dossier["now"][0]["id"], self.gov.id)  # the earliest date first
        manager = self.client_a.with_user(self.manager)
        self.assertEqual({b["id"]: b for b in manager.ldm_dossier["bodies"]}[self.court.id]["open"], 2)
        action = client.ldm_open_matters(self.registry_body.id)
        self.assertIn(("department_id", "=", self.registry_body.id), action["domain"])
        self.assertEqual(client.ldm_action_sessions()["res_model"], "legal.hearing")

    def test_flags_come_from_real_data(self):
        self.gov.is_urgent = True
        flags = {flag["key"] for flag in self.cockpit(self.gov)["flags"]}
        self.assertIn("urgent", flags)
        self.assertIn("missing_documents", flags)  # the tax card is missing
        self.assertNotIn("past_target", flags)
        self.registry_body.target_days = 2
        self.gov.write({"waiting_on": "body", "date_submitted": self.day(-10)})
        flags = {flag["key"] for flag in self.cockpit(self.gov)["flags"]}
        self.assertIn("past_target", flags)

    def test_suggested_target_date_is_arithmetic(self):
        template = self.env.ref(f"{M}.ldm_template_government")
        self.gov.write({"template_id": template.id})
        self.registry_body.target_days = 5
        suggestion = self.cockpit(self.gov)["suggestion"]
        self.assertTrue(suggestion)
        expected = self.gov.company_id.ldm_add_working_days(self.gov.date_opened, template.duration_days,
                                                            self.calendar)
        self.assertGreaterEqual(suggestion["date"], str(expected))
        self.assertEqual(len(suggestion["reasons"]), 2)
        self.gov.with_user(self.lawyer).action_ldm_use_suggested_target()
        self.assertEqual(str(self.gov.due_date), suggestion["date"])
        self.assertFalse(self.cockpit(self.gov)["suggestion"])
        # Lawsuits follow the court's dates: no suggestion.
        self.assertFalse(self.cockpit(self.suit)["suggestion"])
