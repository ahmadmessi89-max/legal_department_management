# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .lit_common import LitCase

FIELDS = ["hearing_id", "main_outcome", "attendance", "needed_days", "judgment_date", "law", "court_degree",
          "in_absentia", "pronounced_in_presence", "add_period", "rule_id", "period_start"]


@tagged("post_install", "-at_install", "ldm")
class TestLitOutcome(LitCase):
    """The session-outcome dialog, the way the client opens it."""

    def open_dialog(self, hearing, user=None, **answers):
        Wizard = self.env["legal.hearing.outcome.wizard"]
        if user:
            Wizard = Wizard.with_user(user)
        action = hearing.action_ldm_record_outcome()
        Wizard = Wizard.with_context(action["context"])
        values = Wizard.default_get(FIELDS)
        values.update(answers)
        return Wizard.create(values)

    def test_dialog_through_default_get_and_new(self):
        hearing = self.hearing()
        Wizard = self.env["legal.hearing.outcome.wizard"].with_context(default_hearing_id=hearing.id)
        values = Wizard.default_get(FIELDS)
        self.assertEqual(values["hearing_id"], hearing.id)
        self.assertEqual(values["main_outcome"], "adjourned")
        self.assertEqual(values["attendance"], "present")
        wizard = Wizard.new(values)
        self.assertEqual(wizard.outcome, "adjourned")
        self.assertTrue(wizard.show_next)
        self.assertTrue(wizard.next_required)
        self.assertEqual(wizard.judgment_date, hearing.date)
        self.assertEqual(wizard.law, "civil")
        self.assertEqual(wizard.court_degree, "first_instance")
        self.assertEqual(wizard.needed_days, 3)
        self.assertTrue(wizard.pronounced_in_presence)
        self.assertFalse(wizard.rule_id)
        self.assertIn(hearing.department_id.name, wizard.session_label)
        wizard.main_outcome = "left_for_review"
        self.assertFalse(wizard.show_next)
        self.assertEqual(wizard.rule_id, self.rule("civ_9"))
        self.assertTrue(wizard.period_preview)
        wizard.main_outcome = "more"
        wizard.more_outcome = "suspended"
        self.assertEqual(wizard.outcome, "suspended")
        self.assertEqual(wizard.rule_id, self.rule("civ_10"))
        self.assertEqual(wizard.period_start, self.d("2027-01-01"))

    def test_adjourned_in_one_step(self):
        """Adjourned to a date, with what is needed before it: the session,
        the next session, the to-do and one chatter line."""
        hearing = self.hearing()
        before = self.env["mail.message"].search_count([("model", "=", "legal.task"), ("res_id", "=", self.lawsuit.id),
                                                        ("message_type", "=", "comment")])
        wizard = self.open_dialog(hearing, user=self.lawyer, next_date=self.d("2026-10-22"),
                                  needed_before="Bring the expert's report")
        result = wizard.action_confirm()
        self.assertEqual(result["params"]["next"]["type"], "ir.actions.act_window_close")
        self.assertEqual(hearing.state, "held")
        self.assertEqual(hearing.outcome, "adjourned")
        self.assertEqual(hearing.needed_before, "Bring the expert's report")
        following = hearing.next_hearing_id
        self.assertEqual(following.date, self.d("2026-10-22"))
        self.assertEqual(following.state, "planned")
        self.assertEqual(following.department_id, self.court)
        self.assertEqual(following.attending_user_id, self.lawyer)
        self.assertEqual(following.previous_hearing_id, hearing)
        self.assertEqual(self.lawsuit.session_date, self.d("2026-10-22"))
        # Three working days before Thursday 22 October: Monday 19 October.
        todo = self.lawsuit.activity_ids.filtered(lambda a: a.summary == "Bring the expert's report")
        self.assertEqual(len(todo), 1)
        self.assertEqual(todo.date_deadline, self.d("2026-10-19"))
        after = self.env["mail.message"].search_count([("model", "=", "legal.task"), ("res_id", "=", self.lawsuit.id),
                                                       ("message_type", "=", "comment")])
        self.assertEqual(after, before + 1)

    def test_nothing_is_written_when_the_next_date_is_missing(self):
        hearing = self.hearing()
        wizard = self.open_dialog(hearing)
        with self.assertRaises(UserError):
            wizard.action_confirm()
        self.assertEqual(hearing.state, "planned")
        self.assertFalse(hearing.next_hearing_id)
        wizard.next_date = self.d("2026-09-30")
        with self.assertRaises(UserError):
            wizard.action_confirm()
        self.assertEqual(hearing.state, "planned")

    def test_a_session_is_recorded_once(self):
        hearing = self.hearing()
        self.open_dialog(hearing, next_date=self.d("2026-10-22")).action_confirm()
        with self.assertRaises(UserError):
            self.open_dialog(hearing, next_date=self.d("2026-10-29")).action_confirm()

    def test_judgment_with_its_deadlines(self):
        hearing = self.hearing()
        wizard = self.open_dialog(hearing, user=self.lawyer, main_outcome="judgment", result="against",
                                  amount_awarded=25000000, notified_date=self.d("2026-10-01"))
        self.assertIn(self.rule("civ_2").name, str(wizard.deadline_preview))
        wizard.action_confirm()
        judgment = self.lawsuit.judgment_ids
        self.assertEqual(len(judgment), 1)
        self.assertEqual(judgment.hearing_id, hearing)
        self.assertEqual(judgment.result, "against")
        self.assertEqual(judgment.amount_awarded, 25000000)
        appeal = judgment.deadline_ids
        self.assertEqual(appeal.rule_id, self.rule("civ_2"))
        self.assertEqual(appeal.date_deadline, self.d("2026-10-18"))
        self.assertFalse(hearing.next_hearing_id)

    def test_left_for_review_proposes_the_renewal_period(self):
        hearing = self.hearing()
        self.open_dialog(hearing, main_outcome="left_for_review", attendance="both_absent").action_confirm()
        deadline = self.lawsuit.deadline_ids
        self.assertEqual(deadline.rule_id, self.rule("civ_9"))
        self.assertEqual(deadline.date_start, self.d("2026-10-01"))
        self.assertEqual(deadline.date_safe, self.d("2026-10-11"))
        self.assertEqual(deadline.source_model, "legal.hearing")

    def test_suspension_counts_from_its_end(self):
        hearing = self.hearing()
        self.open_dialog(hearing, main_outcome="more", more_outcome="suspended").action_confirm()
        deadline = self.lawsuit.deadline_ids
        self.assertEqual(deadline.rule_id, self.rule("civ_10"))
        # Three months after 1 October, then 15 days: Saturday 16 January 2027.
        self.assertEqual(deadline.date_safe, self.d("2027-01-16"))
        self.assertEqual(deadline.date_deadline, self.d("2027-01-17"))

    def test_the_period_can_be_declined(self):
        hearing = self.hearing()
        self.open_dialog(hearing, main_outcome="more", more_outcome="stayed", add_period=False).action_confirm()
        self.assertFalse(self.lawsuit.deadline_ids)

    def test_a_clerk_records_an_adjournment_but_not_a_judgment(self):
        self.lawsuit.lawyer_ids = [(4, self.clerk.id)]
        hearing = self.hearing(attending_user_id=self.clerk.id)
        self.open_dialog(hearing, user=self.clerk, main_outcome="left_for_review").action_confirm()
        self.assertEqual(self.lawsuit.deadline_ids.rule_id, self.rule("civ_9"))
        other = self.hearing(date=self.d("2026-10-08"))
        with self.assertRaises(AccessError):
            self.open_dialog(other, user=self.clerk, main_outcome="judgment").action_confirm()
        self.assertEqual(other.state, "planned")

    def test_the_auditor_cannot_open_the_dialog(self):
        hearing = self.hearing()
        with self.assertRaises(AccessError):
            self.open_dialog(hearing, user=self.auditor)

    def test_a_next_date_on_a_friday_is_flagged(self):
        hearing = self.hearing()
        wizard = self.open_dialog(hearing, next_date=self.d("2026-10-09"))
        self.assertTrue(wizard.next_date_warning)
        wizard.next_date = self.d("2026-10-11")
        self.assertFalse(wizard.next_date_warning)

    def test_matter_level_entry_opens_the_oldest_planned_session(self):
        today = fields.Date.context_today(self.lawsuit)
        later = self.hearing(date=today + timedelta(days=10))
        self.assertFalse(self.lawsuit.ldm_session_to_record, "a future session is not waiting to be recorded")
        first = self.hearing(date=today - timedelta(days=3))
        action = self.lawsuit.action_ldm_record_outcome()
        self.assertEqual(action["res_model"], "legal.hearing.outcome.wizard")
        self.assertEqual(action["context"]["default_hearing_id"], first.id)
        self.assertNotEqual(first, later)
        self.assertTrue(self.lawsuit.ldm_session_to_record)
