# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .lit_common import LitCase


@tagged("post_install", "-at_install", "ldm")
class TestLitEngine(LitCase):
    """Judgments propose their challenge periods; chains start the next
    period; the daily run closes lapsed periods and reports missed ones once."""

    def messages(self, record):
        return self.env["mail.message"].search([("model", "=", record._name), ("res_id", "=", record.id),
                                                ("message_type", "=", "comment")])

    # ------------------------------------------------------------------
    # Judgments
    # ------------------------------------------------------------------
    def test_judgment_without_notification_waits(self):
        judgment = self.judgment()
        self.assertEqual(len(judgment.deadline_ids), 1)
        deadline = judgment.deadline_ids
        self.assertEqual(deadline.rule_id, self.rule("civ_2"))
        self.assertEqual(deadline.state, "awaiting_service")
        self.assertFalse(deadline.date_safe)
        self.assertFalse(deadline.date_deadline)
        self.assertEqual(deadline.user_id, self.lawsuit.lawyer_id)
        self.assertIn(deadline, self.lawsuit.deadline_ids)

    def test_writing_the_notification_counts_and_moving_it_moves(self):
        judgment = self.judgment()
        deadline = judgment.deadline_ids
        before = len(self.messages(self.lawsuit))
        judgment.with_user(self.lawyer).ldm_set_notified_date(self.d("2026-10-01"))
        self.assertEqual(deadline.state, "open")
        self.assertEqual((deadline.date_safe, deadline.date_deadline), (date(2026, 10, 16), date(2026, 10, 18)))
        judgment.notified_date = self.d("2026-10-05")
        self.assertEqual((deadline.date_safe, deadline.date_deadline), (date(2026, 10, 20), date(2026, 10, 20)))
        self.assertEqual(len(judgment.deadline_ids), 1, "recounting never duplicates a period")
        self.assertEqual(len(self.messages(self.lawsuit)), before + 2, "each move is told on the matter")
        judgment._ldm_generate_deadlines()
        self.assertEqual(len(judgment.deadline_ids), 1)

    def test_only_a_lawyer_records_the_service_date(self):
        judgment = self.judgment()
        with self.assertRaises(AccessError):
            judgment.with_user(self.clerk).ldm_set_notified_date(self.d("2026-10-01"))

    def test_service_cannot_come_before_the_judgment(self):
        judgment = self.judgment()
        with self.assertRaises(ValidationError):
            judgment.notified_date = self.d("2026-09-01")

    def test_judgment_in_absence_adds_the_objection(self):
        judgment = self.judgment(in_absentia=True, notified_date=self.d("2026-10-01"))
        self.assertEqual(judgment.deadline_ids.mapped("rule_id"), self.rule("civ_1") | self.rule("civ_2"))
        objection = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("civ_1"))
        self.assertEqual(objection.date_safe, self.d("2026-10-11"))

    def test_final_degree_and_appeal_court_judgments(self):
        final = self.judgment(department_id=self.final_court.id, court_degree="first_instance_final")
        self.assertEqual(final.deadline_ids.rule_id, self.rule("civ_4"))
        appeal = self.judgment(department_id=self.appeal_court.id, court_degree="appeal")
        self.assertEqual(appeal.deadline_ids.rule_id, self.rule("civ_3"))

    def test_changing_the_law_replaces_the_periods(self):
        judgment = self.judgment(notified_date=self.d("2026-10-01"))
        civil = judgment.deadline_ids
        judgment.write({"law": "labour", "court_degree": "labour", "department_id": self.labour_court.id})
        self.assertEqual(civil.state, "cancelled")
        labour = judgment.deadline_ids.filtered(lambda d: d.state == "open")
        self.assertEqual(labour.rule_id, self.rule("lab_2"))
        self.assertEqual(labour.date_safe, self.d("2026-10-31"))

    def test_judgment_in_our_favour_runs_for_the_other_side(self):
        judgment = self.judgment(result="for", notified_date=self.d("2026-10-01"))
        deadline = judgment.deadline_ids
        self.assertFalse(deadline.our_action)
        self.assertIn(self.rule("civ_2").name, deadline.name)
        self.assertNotEqual(deadline.name, self.rule("civ_2").name)
        judgment.result = "against"
        self.assertTrue(deadline.our_action)
        self.assertEqual(deadline.name, self.rule("civ_2").name)

    def test_judgment_defaults_come_from_the_matter(self):
        values = self.env["legal.judgment"].with_context(default_task_id=self.lawsuit.id).default_get(
            ["law", "department_id", "court_degree"])
        self.assertEqual(values["law"], "civil")
        self.assertEqual(values["department_id"], self.court.id)
        self.assertEqual(values["court_degree"], "first_instance")
        judgment = self.env["legal.judgment"].new(values)
        self.assertEqual(judgment.court_degree, "first_instance")

    # ------------------------------------------------------------------
    # Chains
    # ------------------------------------------------------------------
    def test_chain_adm1_adm2_adm3(self):
        Deadline = self.env["legal.deadline"]
        grievance = Deadline.create({"task_id": self.lawsuit.id, "rule_id": self.rule("adm_1").id,
                                     "date_start": self.d("2026-10-01")})
        self.assertEqual(grievance.date_safe, self.d("2026-10-31"))
        # The grievance is lodged on 5 October: the authority has 30 days from it.
        grievance.write({"state": "done", "date_done": self.d("2026-10-05")})
        answer = grievance.next_deadline_ids
        self.assertEqual(answer.rule_id, self.rule("adm_2"))
        self.assertEqual(answer.date_start, self.d("2026-10-05"))
        self.assertEqual(answer.date_safe, self.d("2026-11-04"))
        self.assertFalse(answer.our_action, "the authority's time is not ours to miss")
        # No answer by 4 November: silence counts as rejection.
        Deadline._ldm_lapse(self.company, self.d("2026-11-05"))
        self.assertEqual(answer.state, "lapsed")
        self.assertFalse(answer.escalated)
        challenge = answer.next_deadline_ids
        self.assertEqual(challenge.rule_id, self.rule("adm_3"))
        self.assertEqual(challenge.date_start, self.d("2026-11-04"))
        self.assertEqual((challenge.date_safe, challenge.date_deadline), (date(2026, 12, 4), date(2026, 12, 6)))
        self.assertTrue(challenge.our_action)
        # Running again changes nothing.
        Deadline._ldm_lapse(self.company, self.d("2026-11-05"))
        self.assertEqual(len(answer.next_deadline_ids), 1)

    def test_an_explicit_answer_starts_the_challenge_from_its_date(self):
        Deadline = self.env["legal.deadline"]
        answer = Deadline.create({"task_id": self.lawsuit.id, "rule_id": self.rule("adm_2").id,
                                  "date_start": self.d("2026-10-05")})
        answer.write({"state": "done", "date_done": self.d("2026-10-20")})
        challenge = answer.next_deadline_ids
        self.assertEqual(challenge.date_start, self.d("2026-10-20"))
        self.assertEqual(challenge.date_safe, self.d("2026-11-19"))

    def test_chain_exe3_exe4_waits_for_the_decision(self):
        Deadline = self.env["legal.deadline"]
        grievance = Deadline.create({"task_id": self.lawsuit.id, "rule_id": self.rule("exe_3").id,
                                     "date_start": self.d("2026-10-01")})
        self.assertEqual(grievance.date_safe, self.d("2026-10-04"))
        self.lawsuit.lawyer_ids = [(4, self.clerk.id)]
        grievance.with_user(self.clerk).action_ldm_mark_met()
        cassation = grievance.next_deadline_ids
        self.assertEqual(cassation.rule_id, self.rule("exe_4"))
        self.assertEqual(cassation.state, "awaiting_service")
        cassation.date_start = self.d("2026-10-07")
        self.assertEqual(cassation.state, "open")
        self.assertEqual(cassation.date_safe, self.d("2026-10-14"))

    def test_execution_notice_starts_the_debtor_period(self):
        execution = self.make_matter(name="Execution of the Karkh judgment", our_role="defendant",
                                     template_id=self.env.ref("legal_department_management.ldm_template_execution").id)
        line = self.env["legal.court.stage"].create({
            "task_id": execution.id, "stage": "execution", "department_id": self.execution_office.id,
            "execution_file_number": "EX/2026/77"})
        self.assertFalse(execution.deadline_ids)
        line.notification_date = self.d("2026-10-01")
        deadline = execution.deadline_ids
        self.assertEqual(deadline.rule_id, self.rule("exe_1"))
        self.assertEqual(deadline.date_safe, self.d("2026-10-08"))
        self.assertTrue(deadline.our_action, "we act for the debtor here")
        line.notification_date = self.d("2026-10-04")
        self.assertEqual(len(execution.deadline_ids), 1)
        self.assertEqual(deadline.date_safe, self.d("2026-10-11"))

    # ------------------------------------------------------------------
    # Lapse, escalation, finality
    # ------------------------------------------------------------------
    def test_missed_deadline_is_escalated_once(self):
        Deadline = self.env["legal.deadline"]
        deadline = Deadline.create({"task_id": self.lawsuit.id, "rule_id": self.rule("civ_2").id,
                                    "date_start": self.d("2026-10-01")})
        Deadline._ldm_lapse(self.company, self.d("2026-10-18"))
        self.assertEqual(deadline.state, "open", "the legal last day itself still counts")
        before = len(self.messages(self.lawsuit))
        Deadline._ldm_lapse(self.company, self.d("2026-10-19"))
        self.assertEqual(deadline.state, "missed")
        self.assertTrue(deadline.escalated)
        messages = self.messages(self.lawsuit)
        self.assertEqual(len(messages), before + 1)
        notified = messages[0].partner_ids
        self.assertIn(self.manager.partner_id, notified)
        self.assertIn(self.lawyer.partner_id, notified)
        Deadline._ldm_lapse(self.company, self.d("2026-10-20"))
        self.assertEqual(len(self.messages(self.lawsuit)), before + 1, "escalated once")

    def test_the_daily_run_uses_today(self):
        deadline = self.env["legal.deadline"].create({"task_id": self.lawsuit.id, "name": "Old reply",
                                                      "date_safe": self.d("2020-01-05")})
        self.env["legal.deadline"]._cron_ldm_deadlines()
        self.assertEqual(deadline.state, "missed")

    def test_judgment_becomes_final_when_its_windows_lapse(self):
        judgment = self.judgment(notified_date=self.d("2026-10-01"))
        self.env["legal.deadline"]._ldm_lapse(self.company, self.d("2026-10-19"))
        self.assertEqual(judgment.final_date, self.d("2026-10-19"))

    def test_a_met_window_keeps_the_judgment_open(self):
        judgment = self.judgment(notified_date=self.d("2026-10-01"), in_absentia=True)
        objection = judgment.deadline_ids.filtered(lambda d: d.rule_id == self.rule("civ_1"))
        objection.write({"state": "done"})
        self.env["legal.deadline"]._ldm_lapse(self.company, self.d("2026-10-19"))
        self.assertFalse(judgment.final_date)

    def test_managers_hear_about_open_deadlines_and_unattended_sessions(self):
        Task = self.env["legal.task"]
        self.env["legal.deadline"].create({"task_id": self.lawsuit.id, "rule_id": self.rule("civ_2").id,
                                           "date_start": self.d("2026-09-16")})  # act by Thu 1 Oct
        self.hearing(date=self.d("2026-10-04"), attending_user_id=False)  # Sunday after a Thursday
        items = Task._ldm_reminder_items(self.company, self.d("2026-10-01"), self.d("2026-10-06"))
        to_manager = [i for i in items if i[1] == self.manager]
        kinds = {i[4] for i in to_manager}
        self.assertEqual(kinds, {"ldm_activity_deadline", "ldm_activity_session"})
        Task._ldm_run_reminders()

    def test_cancel_and_reopen_rights(self):
        deadline = self.env["legal.deadline"].create({"task_id": self.lawsuit.id, "rule_id": self.rule("civ_2").id,
                                                      "date_start": self.d("2026-10-01")})
        with self.assertRaises(AccessError):
            deadline.with_user(self.clerk).action_ldm_cancel()
        deadline.with_user(self.lawyer).action_ldm_cancel()
        self.assertEqual(deadline.state, "cancelled")
        with self.assertRaises(AccessError):
            deadline.with_user(self.lawyer).action_ldm_reopen()
        deadline.with_user(self.manager).action_ldm_reopen()
        self.assertEqual(deadline.state, "open")
        self.assertEqual(deadline.date_safe, self.d("2026-10-16"))
        with self.assertRaises(AccessError):
            deadline.with_user(self.auditor).action_ldm_mark_met()
