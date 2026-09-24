# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests import tagged

from .lit_common import LitCase

# Every seeded period started on Thursday 1 October 2026, counted by hand.
# Calendar days from the day after the event (CCP Art. 25(1)); a last day on a
# Friday, Saturday or public holiday moves to the next working day (Art. 25(2)).
BY_HAND = {
    (3, "days"): ("2026-10-04", "2026-10-04"),      # Sunday
    (7, "days"): ("2026-10-08", "2026-10-08"),      # Thursday
    (10, "days"): ("2026-10-11", "2026-10-11"),     # Sunday
    (15, "days"): ("2026-10-16", "2026-10-18"),     # Friday -> Sunday
    (21, "days"): ("2026-10-22", "2026-10-22"),     # Thursday
    (30, "days"): ("2026-10-31", "2026-11-01"),     # Saturday -> Sunday
    (60, "days"): ("2026-11-30", "2026-11-30"),     # Monday
    (3, "months"): ("2027-01-01", "2027-01-03"),    # New Year's Day, a Friday -> Sunday
    (6, "months"): ("2027-04-01", "2027-04-01"),    # Thursday
    (84, "months"): ("2033-10-01", "2033-10-02"),   # Saturday -> Sunday
}

SEEDED = {
    "civ_1": "CIV-1", "civ_2": "CIV-2", "civ_3": "CIV-3", "civ_4": "CIV-4", "civ_5": "CIV-5", "civ_6": "CIV-6",
    "civ_7": "CIV-7", "civ_8": "CIV-8", "civ_9": "CIV-9", "civ_10": "CIV-10", "civ_11": "CIV-11", "civ_12": "CIV-12",
    "crm_1": "CRM-1", "crm_2_violation": "CRM-2.1", "crm_2_misdemeanour": "CRM-2.2", "crm_2_felony": "CRM-2.3",
    "crm_3": "CRM-3", "crm_4": "CRM-4",
    "adm_1": "ADM-1", "adm_2": "ADM-2", "adm_3": "ADM-3", "adm_4_grievance": "ADM-4.1",
    "adm_4_decision": "ADM-4.2", "adm_4_suit": "ADM-4.3", "adm_5": "ADM-5",
    "lab_1": "LAB-1", "lab_2": "LAB-2",
    "exe_1": "EXE-1", "exe_2": "EXE-2", "exe_3": "EXE-3", "exe_4": "EXE-4", "exe_5": "EXE-5",
    "tax_4": "TAX-4", "tax_5": "TAX-5",
}


@tagged("post_install", "-at_install", "ldm")
class TestLitClocks(LitCase):

    def test_every_row_of_the_research_is_seeded(self):
        for xmlid, code in SEEDED.items():
            rule = self.rule(xmlid)
            self.assertEqual(rule.code, code)
            self.assertTrue(rule.basis, f"{code} has no legal basis")
            self.assertIn(rule.verification, ("verified", "secondary", "unverified"))
        # Confidence as the research marks it
        self.assertEqual(self.rule("civ_2").verification, "verified")
        self.assertEqual(self.rule("exe_1").verification, "secondary")
        self.assertEqual(self.rule("tax_4").verification, "unverified")
        # Chains and outcome-started periods
        self.assertEqual(self.rule("adm_1").next_rule_id, self.rule("adm_2"))
        self.assertEqual(self.rule("adm_2").next_rule_id, self.rule("adm_3"))
        self.assertEqual(self.rule("adm_4_decision").next_rule_id, self.rule("adm_4_suit"))
        self.assertEqual(self.rule("exe_3").next_rule_id, self.rule("exe_4"))
        self.assertEqual(self.rule("civ_9").trigger_outcome, "left_for_review")
        self.assertEqual(self.rule("civ_10").trigger_outcome, "suspended")
        self.assertEqual(self.rule("civ_11").trigger_outcome, "stayed")
        self.assertEqual(self.rule("civ_6").max_months, 6)

    def test_every_seeded_period_from_a_fixed_date(self):
        Deadline = self.env["legal.deadline"]
        for xmlid in SEEDED:
            rule = self.rule(xmlid)
            with self.subTest(rule=rule.code):
                deadline = Deadline.create({"task_id": self.lawsuit.id, "rule_id": rule.id,
                                            "date_start": self.d("2026-10-01")})
                safe, legal = BY_HAND[(rule.days, rule.unit)]
                self.assertEqual(deadline.date_safe, self.d(safe))
                self.assertEqual(deadline.date_deadline, self.d(legal))
                self.assertEqual(deadline.state, "open")
                self.assertEqual(deadline.name, rule.name)

    def test_service_on_thursday_plus_fifteen_days(self):
        """The brief's example: served Thu 1 Oct 2026, 15-day appeal: act by
        Fri 16 Oct, legal last day Sun 18 Oct."""
        judgment = self.judgment(notified_date=self.d("2026-10-01"))
        appeal = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("civ_2"))
        self.assertEqual((appeal.date_safe, appeal.date_deadline), (date(2026, 10, 16), date(2026, 10, 18)))
        self.assertTrue(appeal.rolled)
        self.assertEqual(appeal.kind, "appeal")

    def test_last_day_in_eid_moves_after_eid(self):
        # Eid al-Adha 2026 (estimated) 27-30 May; the 30th is a Saturday.
        judgment = self.judgment(date=self.d("2026-05-10"), notified_date=self.d("2026-05-12"))
        appeal = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("civ_2"))
        self.assertEqual(appeal.date_safe, self.d("2026-05-27"))
        self.assertEqual(appeal.date_deadline, self.d("2026-05-31"))

    def test_criminal_cassation_counts_from_pronouncement(self):
        criminal = self.make_matter(name="Public prosecution v. X", template_id=self.env.ref(
            "legal_department_management.ldm_template_criminal_complaint").id, department_id=self.felony_court.id)
        judgment = self.judgment(criminal, date=self.d("2026-10-01"), department_id=self.felony_court.id,
                                 court_degree="felony", law="criminal", pronounced_in_presence=True)
        cassation = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("crm_3"))
        self.assertEqual(cassation.state, "open")
        self.assertEqual(cassation.date_start, self.d("2026-10-01"))
        self.assertEqual((cassation.date_safe, cassation.date_deadline), (date(2026, 10, 31), date(2026, 11, 1)))
        self.assertEqual(len(judgment.deadline_ids), 1)

    def test_criminal_judgment_in_absence_waits_for_notification(self):
        criminal = self.make_matter(name="Public prosecution v. Y", department_id=self.felony_court.id)
        judgment = self.judgment(criminal, date=self.d("2026-10-01"), department_id=self.felony_court.id,
                                 court_degree="felony", law="criminal", in_absentia=True)
        rules = judgment.deadline_ids.mapped("rule_id")
        self.assertEqual(rules, self.rule("crm_2_felony") | self.rule("crm_3"))
        self.assertEqual(set(judgment.deadline_ids.mapped("state")), {"awaiting_service"})
        judgment.notified_date = self.d("2026-10-01")
        felony = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("crm_2_felony"))
        self.assertEqual((felony.date_safe, felony.date_deadline), (date(2027, 4, 1), date(2027, 4, 1)))

    def test_correction_is_capped_six_months_after_the_decision(self):
        judgment = self.judgment(date=self.d("2026-01-10"), department_id=self.cassation_court.id,
                                 court_degree="cassation", notified_date=self.d("2026-07-08"))
        correction = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("civ_6"))
        # 7 days from 8 July would be 15 July; six months from 10 January is Friday 10 July.
        self.assertEqual(correction.date_safe, self.d("2026-07-10"))
        self.assertEqual(correction.date_deadline, self.d("2026-07-12"))

    def test_a_manual_deadline_without_rule_keeps_its_date(self):
        deadline = self.env["legal.deadline"].create({"task_id": self.lawsuit.id, "name": "Reply to the expert",
                                                      "date_safe": self.d("2026-10-16")})
        self.assertEqual(deadline.date_deadline, self.d("2026-10-16"))
        deadline.date_safe = self.d("2026-10-20")
        self.assertEqual(deadline.date_deadline, self.d("2026-10-20"))

    def test_changing_a_deadline_start_recounts_it(self):
        deadline = self.env["legal.deadline"].create({"task_id": self.lawsuit.id, "rule_id": self.rule("civ_2").id,
                                                      "date_start": self.d("2026-10-01")})
        deadline.date_start = self.d("2026-10-05")
        self.assertEqual((deadline.date_safe, deadline.date_deadline), (date(2026, 10, 20), date(2026, 10, 20)))
