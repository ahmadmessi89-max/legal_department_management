# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .lit_common import LitCase


@tagged("post_install", "-at_install", "ldm")
class TestLitCourt(LitCase):
    """Court stages, challenges, the licence and substitution checks, and the
    two printed documents."""

    def test_a_stage_line_updates_the_matter(self):
        Stage = self.env["legal.court.stage"]
        Stage.create({"task_id": self.lawsuit.id, "stage": "first_instance", "department_id": self.court.id,
                      "case_number": "1234/b", "case_year": 2026})
        self.assertEqual(self.lawsuit.court_stage, "first_instance")
        self.assertEqual(self.lawsuit.court_case_number, "1234/b/2026")
        appeal = Stage.create({"task_id": self.lawsuit.id, "stage": "appeal", "department_id": self.appeal_court.id,
                               "case_number": "88/s/2026"})
        self.assertEqual(self.lawsuit.court_stage, "appeal")
        self.assertEqual(self.lawsuit.court_case_number, "88/s/2026")
        appeal.unlink()
        self.assertEqual(self.lawsuit.court_stage, "first_instance")
        self.assertEqual(self.lawsuit.court_case_number, "1234/b/2026")

    def test_lodging_an_appeal_opens_the_next_stage(self):
        self.env["legal.court.stage"].create({"task_id": self.lawsuit.id, "stage": "first_instance",
                                              "department_id": self.court.id, "case_number": "1234/b"})
        judgment = self.judgment(in_absentia=True, notified_date=self.d("2026-10-01"), result="against")
        self.assertEqual(self.lawsuit.court_stage_ids.judgment_id, judgment, "the judgment closes its stage line")
        appeal = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("civ_2"))
        objection = judgment.deadline_ids - appeal
        self.assertTrue(judgment.ldm_can_challenge)
        action = judgment.with_user(self.lawyer).action_ldm_lodge_challenge()
        Wizard = self.env["legal.judgment.challenge.wizard"].with_user(self.lawyer).with_context(action["context"])
        values = Wizard.default_get(["judgment_id", "date_lodged", "case_year"])
        wizard = Wizard.new(values)
        self.assertEqual(wizard.deadline_id, objection, "the earliest open challenge is proposed")
        wizard = Wizard.create(dict(values, deadline_id=appeal.id, date_lodged=self.d("2026-10-12"),
                                    case_number="501/s"))
        self.assertEqual(wizard.stage, "appeal")
        self.assertEqual(wizard.department_id, self.appeal_court, "the higher court is proposed")
        wizard.action_confirm()
        self.assertEqual(appeal.state, "done")
        self.assertEqual(appeal.date_done, self.d("2026-10-12"))
        self.assertEqual(objection.state, "cancelled")
        self.assertEqual(self.lawsuit.court_stage, "appeal")
        self.assertIn("501/s", self.lawsuit.court_case_number)
        self.assertFalse(judgment.ldm_can_challenge)

    def test_a_late_challenge_is_refused(self):
        judgment = self.judgment(notified_date=self.d("2026-10-01"))
        wizard = self.env["legal.judgment.challenge.wizard"].create({
            "judgment_id": judgment.id, "date_lodged": self.d("2026-10-19")})
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_only_a_lawyer_lodges_a_challenge(self):
        judgment = self.judgment(notified_date=self.d("2026-10-01"))
        self.lawsuit.lawyer_ids = [(4, self.clerk.id)]
        with self.assertRaises(AccessError):
            judgment.with_user(self.clerk).action_ldm_lodge_challenge()

    def test_trainee_before_an_appeal_court_is_warned(self):
        self.lawyer2.ldm_licence_class = "trainee"
        at_appeal = self.hearing(department_id=self.appeal_court.id, attending_user_id=self.lawyer2.id)
        self.assertTrue(at_appeal.licence_warning)
        self.assertIn(self.lawyer2.name, at_appeal.licence_warning)
        at_first_instance = self.hearing(attending_user_id=self.lawyer2.id)
        self.assertFalse(at_first_instance.licence_warning)
        self.lawyer2.ldm_licence_class = "b"
        self.assertFalse(at_appeal.licence_warning)
        result = at_appeal._onchange_licence_class()
        self.assertFalse(result)

    def test_substitution_letter_needed_and_warned(self):
        poa = self.env["legal.poa"].create({"poa_type": "judicial", "principal_company_id": self.client_a.id,
                                            "number": "5521", "notary_office": "Karkh notary office",
                                            "agent_user_ids": [(6, 0, [self.lawyer.id])],
                                            "substitution_allowed": True})
        self.lawsuit.poa_id = poa
        own = self.hearing()
        self.assertFalse(own.needs_substitution_letter)
        other = self.hearing(attending_user_id=self.lawyer2.id)
        self.assertTrue(other.needs_substitution_letter)
        self.assertFalse(other.substitution_warning)
        outside = self.hearing(substitute_partner_id=self.env["res.partner"].create({"name": "Outside Counsel"}).id)
        self.assertTrue(outside.needs_substitution_letter)
        poa.substitution_allowed = False
        self.assertTrue(other.substitution_warning)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "legal_department_management.action_report_ldm_substitution", other.ids)[0].decode()
        self.assertIn("5521", html)
        self.assertIn(self.lawyer2.name, html)
        self.assertIn(self.lawyer.name, html)

    def test_hearing_roll_by_court_and_lawyer(self):
        self.hearing(date=self.d("2031-10-04"), time=9.5, purpose="Pleadings")
        self.hearing(date=self.d("2031-10-05"), department_id=self.appeal_court.id, attending_user_id=self.lawyer2.id)
        self.hearing(date=self.d("2031-11-20"))
        Report = self.env["report.legal_department_management.report_ldm_hearing_roll"]
        values = Report._get_report_values([], {"date_from": "2031-10-01", "date_to": "2031-10-07"})
        self.assertEqual(values["count"], 2)
        courts = [g["court"] for g in values["groups"]]
        self.assertEqual(set(courts), {self.court, self.appeal_court})
        rows = [row for g in values["groups"] for lawyer in g["lawyers"] for row in lawyer["rows"]]
        self.assertIn("09:30", [row["time"] for row in rows])
        html = self.env["ir.actions.report"]._render_qweb_html(
            "legal_department_management.action_report_ldm_hearing_roll", [],
            data={"date_from": "2031-10-01", "date_to": "2031-10-07"})[0].decode()
        self.assertIn(self.appeal_court.name, html)
        self.assertIn("Pleadings", html)
        # From a selection of sessions; an outside lawyer is listed under their own name.
        outside = self.env["res.partner"].create({"name": "Outside Counsel Ali"})
        self.hearing(date=self.d("2031-11-21"), attending_user_id=False, substitute_partner_id=outside.id)
        values = Report._get_report_values(self.lawsuit.hearing_ids.ids, {})
        self.assertEqual(values["count"], 4)
        names = [lawyer["name"] for g in values["groups"] for lawyer in g["lawyers"]]
        self.assertTrue(any("Outside Counsel Ali" in name for name in names))
        # The roll wizard prints with its dates
        wizard = self.env["legal.hearing.roll.wizard"].with_user(self.lawyer).create({
            "date_from": self.d("2031-10-01"), "date_to": self.d("2031-10-07")})
        action = wizard.action_print()
        self.assertEqual(action["data"]["date_to"], "2031-10-07")

    def test_the_roll_respects_record_rules(self):
        self.hearing(date=self.d("2031-10-04"))
        other_client = self.make_matter(client=self.client_b, name="Tigris v. Nahrain")
        self.hearing(other_client, date=self.d("2031-10-04"), attending_user_id=self.lawyer2.id)
        Report = self.env["report.legal_department_management.report_ldm_hearing_roll"].with_user(self.lawyer)
        values = Report._get_report_values([], {"date_from": "2031-10-01", "date_to": "2031-10-07"})
        self.assertEqual(values["count"], 1)

    def test_only_managers_delete_sessions_and_judgments(self):
        hearing = self.hearing()
        judgment = self.judgment()
        with self.assertRaises(AccessError):
            hearing.with_user(self.lawyer).unlink()
        with self.assertRaises(AccessError):
            judgment.with_user(self.lawyer).unlink()
        judgment.with_user(self.manager).unlink()
        hearing.with_user(self.manager).unlink()

    def test_recording_a_session_closes_its_reminder(self):
        hearing = self.hearing(date=self.d("2026-10-01"))
        activity_type = self.env.ref("legal_department_management.ldm_activity_session")
        self.lawsuit.activity_schedule(activity_type_id=activity_type.id, user_id=self.lawyer.id,
                                       summary="Court session on 2026-10-01 — %s" % self.lawsuit.task_number)
        self.assertTrue(self.lawsuit.activity_ids)
        hearing.write({"state": "held", "outcome": "pleading"})
        self.assertFalse(self.lawsuit.activity_ids.filtered(lambda a: a.activity_type_id == activity_type))

    def test_calendar_shades_weekends_and_holidays(self):
        days = self.env["legal.hearing"].get_unusual_days("2026-05-24 00:00:00", "2026-06-01 00:00:00")
        self.assertTrue(days["2026-05-27"], "Eid al-Adha")
        self.assertTrue(days["2026-05-29"], "Friday")
        self.assertFalse(days["2026-05-24"], "Sunday is a working day")
