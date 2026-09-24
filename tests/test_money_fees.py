# -*- coding: utf-8 -*-
"""Fee agreements: the 20% cap, retainers, the Bar minimum, the schedule's
events and what the close dialog does with the remaining instalments."""
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .test_money_common import RATE, MoneyCase


@tagged("post_install", "-at_install", "ldm")
class TestMoneyFees(MoneyCase):

    # ------------------------------------------------------------------
    # 20% cap (Advocacy Law Art. 56)
    # ------------------------------------------------------------------
    def test_cap_mixed_currency_several_matters(self):
        engagement = self.engagement(currency_id=self.usd.id, amount=3000)
        self.make_matter(name="Claim in dinars", law_branch="civil", matter_value=10_000_000,
                         currency_id=self.cur.id, engagement_id=engagement.id)
        self.make_matter(name="Claim in the second currency", law_branch="commercial", matter_value=5000,
                         currency_id=self.usd.id, engagement_id=engagement.id)
        expected_base = 10_000_000 / RATE + 5000
        self.assertAlmostEqual(engagement.cap_base, expected_base, delta=0.02)
        self.assertAlmostEqual(engagement.cap_limit, 0.2 * expected_base, delta=0.02)
        self.assertTrue(engagement.cap_exceeded, "3000 is above 20% of about 12,634")
        engagement.amount = 2000
        self.assertFalse(engagement.cap_exceeded)

    def test_success_percent_counts_against_the_cap(self):
        engagement = self.engagement(fee_type="success", amount=0, success_percent=25)
        self.make_matter(name="Debt", law_branch="civil", matter_value=8_000_000, engagement_id=engagement.id)
        self.assertAlmostEqual(engagement.cap_fee, 2_000_000, delta=1)
        self.assertTrue(engagement.cap_exceeded)
        engagement.success_percent = 15
        self.assertFalse(engagement.cap_exceeded)

    def test_criminal_matters_are_exempt(self):
        engagement = self.engagement(amount=5_000_000)
        self.make_matter(name="Complaint", law_branch="criminal", matter_value=1_000_000, engagement_id=engagement.id)
        self.assertTrue(engagement.cap_exempt)
        self.assertFalse(engagement.cap_exceeded)
        # A civil matter joins: only its value counts.
        self.make_matter(name="Civil claim", law_branch="civil", matter_value=10_000_000, engagement_id=engagement.id)
        self.assertFalse(engagement.cap_exempt)
        self.assertAlmostEqual(engagement.cap_base, 10_000_000, delta=1)
        self.assertTrue(engagement.cap_exceeded, "5,000,000 is above 20% of the civil value only")

    def test_activation_over_the_cap_needs_a_manager_and_a_reason(self):
        engagement = self.engagement(amount=3_000_000)
        self.make_matter(name="Claim", law_branch="civil", matter_value=10_000_000, engagement_id=engagement.id)
        with self.assertRaises(UserError):
            engagement.with_user(self.lawyer).action_ldm_activate()
        with self.assertRaises(UserError):
            engagement.with_user(self.manager).action_ldm_activate()
        engagement.with_user(self.manager).write({"cap_override_reason": "Complex matter agreed with the client."})
        engagement.with_user(self.manager).action_ldm_activate()
        self.assertEqual(engagement.state, "active")
        # The check also holds when the state is written directly.
        other = self.engagement(amount=3_000_000)
        self.make_matter(name="Claim 2", law_branch="civil", matter_value=10_000_000, engagement_id=other.id)
        with self.assertRaises(UserError):
            other.with_user(self.lawyer).write({"state": "active"})

    def test_cap_check_can_be_switched_off(self):
        self.env.company.ldm_fee_cap_check = False
        engagement = self.engagement(amount=3_000_000)
        self.make_matter(name="Claim", law_branch="civil", matter_value=10_000_000, engagement_id=engagement.id)
        self.assertFalse(engagement.cap_exceeded)

    # ------------------------------------------------------------------
    # Retainers (Bar order 3021 of 2021)
    # ------------------------------------------------------------------
    def test_monthly_retainer_generates_twelve_lines(self):
        start = self.d("2026-01-01")
        engagement = self.engagement(fee_type="retainer", amount=400_000, date_start=start)
        self.assertEqual(engagement.retainer_period, "monthly")
        engagement.action_ldm_activate()
        lines = engagement.line_ids.sorted("date")
        self.assertEqual(len(lines), 12)
        self.assertEqual(lines[0].date, start)
        self.assertEqual(lines[-1].date, start + relativedelta(months=11))
        self.assertTrue(all(line.amount == 400_000 for line in lines))
        self.assertEqual(engagement.retainer_next_date, start + relativedelta(years=1))
        # Dated lines in the past fall due on activation.
        self.assertTrue(all(line.state == "due" for line in lines if line.date <= self.today))

    def test_yearly_retainer_is_one_line(self):
        engagement = self.engagement(fee_type="retainer", retainer_period="yearly", amount=500_000,
                                     date_start=self.today + timedelta(days=10))
        engagement.action_ldm_activate()
        self.assertEqual(len(engagement.line_ids), 1)
        self.assertEqual(engagement.line_ids.amount, 6_000_000)
        self.assertEqual(engagement.line_ids.state, "planned")

    def test_retainer_renews_by_cron(self):
        engagement = self.engagement(fee_type="retainer", amount=400_000,
                                     date_start=self.today - relativedelta(years=1, days=5))
        engagement.action_ldm_activate()
        self.assertEqual(len(engagement.line_ids), 12)
        self.env["legal.engagement"]._cron_ldm_fee_schedule()
        self.assertEqual(len(engagement.line_ids), 24, "the next year is generated when the first ends")

    def test_bar_minimum_warning_by_client_kind(self):
        local = self.engagement(fee_type="retainer", amount=250_000)
        self.assertTrue(local.retainer_below_minimum)
        local.amount = 300_000
        self.assertFalse(local.retainer_below_minimum)
        self.client_b.company_type = "foreign_branch"
        foreign = self.engagement(client=self.client_b, fee_type="retainer", amount=500_000)
        self.assertEqual(foreign.retainer_minimum, 600_000)
        self.assertTrue(foreign.retainer_below_minimum)
        in_usd = self.engagement(client=self.client_b, fee_type="retainer", amount=500, currency_id=self.usd.id)
        self.assertFalse(in_usd.retainer_below_minimum, "500 in the second currency is 655,000")

    # ------------------------------------------------------------------
    # Schedule events
    # ------------------------------------------------------------------
    def _staged(self):
        engagement = self.engagement(fee_type="installments", amount=7_000_000)
        events = ["signing", "filing", "judgment_first_instance", "judgment_final", "execution_opened",
                  "collection", "closing"]
        engagement.line_ids = [(0, 0, {"name": e, "trigger_event": e, "amount": 1_000_000}) for e in events]
        matter = self.started(self.make_matter(name="Lawsuit", engagement_id=engagement.id,
                                                template_id=self.t_lawsuit.id))
        engagement.action_ldm_activate()
        return engagement, matter

    def state_of(self, engagement, event):
        return engagement.line_ids.filtered(lambda l: l.trigger_event == event).state

    def test_events_make_lines_due(self):
        engagement, matter = self._staged()
        self.assertEqual(self.state_of(engagement, "signing"), "planned")
        engagement.signed = True
        self.assertEqual(self.state_of(engagement, "signing"), "due")
        self.assertTrue(engagement.signed_date)

        self.env["legal.court.stage"].create({"task_id": matter.id, "stage": "first_instance",
                                              "case_number": "12/b/2026"})
        self.assertEqual(self.state_of(engagement, "filing"), "due")

        judgment = self.env["legal.judgment"].create({"task_id": matter.id, "date": self.today,
                                                      "court_stage": "first_instance", "result": "for"})
        self.assertEqual(self.state_of(engagement, "judgment_first_instance"), "due")
        self.assertEqual(self.state_of(engagement, "judgment_final"), "planned")
        judgment.final_date = self.today
        self.assertEqual(self.state_of(engagement, "judgment_final"), "due")

        self.env["legal.court.stage"].create({"task_id": matter.id, "stage": "execution"})
        self.assertEqual(self.state_of(engagement, "execution_opened"), "due")

        self.env["legal.client.fund.line"].create({
            "legal_company_id": self.client_a.id, "task_id": matter.id, "kind": "execution_collection",
            "amount": 2_000_000, "currency_id": self.cur.id})
        self.assertEqual(self.state_of(engagement, "collection"), "due")

        self.assertEqual(self.state_of(engagement, "closing"), "planned")
        self.close(matter)
        self.assertEqual(self.state_of(engagement, "closing"), "due")
        self.assertEqual(engagement.amount_due, 7_000_000)

    def test_signing_before_activation_fires_on_activation(self):
        engagement = self.engagement(signed=True)
        engagement.line_ids = [(0, 0, {"name": "On signing", "trigger_event": "signing", "amount": 500_000})]
        self.assertEqual(engagement.line_ids.state, "planned", "a draft agreement makes nothing due")
        engagement.action_ldm_activate()
        self.assertEqual(engagement.line_ids.state, "due")

    def test_success_fee_on_collection(self):
        engagement = self.engagement(fee_type="success", amount=0, success_percent=10)
        matter = self.make_matter(name="Debt", law_branch="civil", engagement_id=engagement.id)
        engagement.action_ldm_activate()
        self.env["legal.client.fund.line"].create({
            "legal_company_id": self.client_a.id, "task_id": matter.id, "kind": "execution_collection",
            "amount": 5_000_000, "currency_id": self.cur.id})
        line = engagement.line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.state, "due")
        self.assertEqual(line.amount, 500_000)

    def test_per_transaction_and_per_hearing(self):
        per_matter = self.engagement(fee_type="per_transaction", amount=150_000)
        per_matter.action_ldm_activate()
        matter = self.started(self.make_matter(name="Renewal", engagement_id=per_matter.id))
        self.close(matter, outcome="completed")
        self.assertEqual(len(per_matter.line_ids), 1)
        self.assertEqual(per_matter.line_ids.state, "due")
        self.assertEqual(per_matter.line_ids.task_id, matter)

        per_session = self.engagement(fee_type="per_hearing", amount=75_000)
        per_session.action_ldm_activate()
        lawsuit = self.make_matter(name="Lawsuit", engagement_id=per_session.id)
        hearing = self.env["legal.hearing"].create({"task_id": lawsuit.id, "date": self.today})
        self.assertFalse(per_session.line_ids)
        hearing.state = "held"
        self.assertEqual(len(per_session.line_ids), 1)
        self.assertEqual(per_session.line_ids.amount, 75_000)
        hearing.write({"outcome": "adjourned"})
        self.assertEqual(len(per_session.line_ids), 1, "writing a held session again bills nothing more")

    def test_cron_makes_dated_lines_due(self):
        engagement = self.engagement(fee_type="installments")
        engagement.line_ids = [
            (0, 0, {"name": "Past", "trigger_event": "date", "date": self.today + timedelta(days=5), "amount": 1}),
        ]
        engagement.action_ldm_activate()
        line = engagement.line_ids
        self.assertEqual(line.state, "planned")
        line.date = self.today - timedelta(days=1)
        self.env["legal.engagement"]._cron_ldm_fee_schedule()
        self.assertEqual(line.state, "due")

    # ------------------------------------------------------------------
    # Close dialog in billing mode (Art. 58)
    # ------------------------------------------------------------------
    def test_close_dialog_proposes_remaining_lines(self):
        engagement = self.engagement(fee_type="installments")
        engagement.line_ids = [
            (0, 0, {"name": "At judgment", "trigger_event": "judgment_first_instance", "amount": 400_000}),
            (0, 0, {"name": "At execution", "trigger_event": "execution_opened", "amount": 600_000}),
        ]
        matter = self.started(self.make_matter(name="Settled lawsuit", engagement_id=engagement.id))
        engagement.action_ldm_activate()
        Wizard = self.env["legal.task.decision.wizard"]
        context = {"default_task_ids": matter.ids, "default_mode": "close"}
        values = Wizard.with_context(context).default_get(["task_ids", "mode", "outcome", "ldm_remaining_action"])
        wizard = Wizard.with_context(context).new(values)
        wizard.outcome = "settled"
        self.assertTrue(wizard.ldm_billing)
        self.assertEqual(len(wizard.ldm_remaining_line_ids), 2)
        self.assertEqual(wizard.ldm_remaining_action, "due")
        wizard.outcome = "won"
        self.assertEqual(wizard.ldm_remaining_action, "keep")
        self.close(matter, outcome="settled")
        self.assertEqual(set(engagement.line_ids.mapped("state")), {"due"})

    def test_close_dialog_waive_needs_a_reason(self):
        engagement = self.engagement(fee_type="installments")
        engagement.line_ids = [(0, 0, {"name": "At judgment", "trigger_event": "judgment_first_instance",
                                       "amount": 400_000})]
        matter = self.started(self.make_matter(name="Withdrawn", engagement_id=engagement.id))
        engagement.action_ldm_activate()
        with self.assertRaises(UserError):
            self.close(matter, outcome="client_revoked", ldm_remaining_action="waive")
        self.close(matter, outcome="client_revoked", ldm_remaining_action="waive",
                   ldm_waive_reason="Agreed with the client when the mandate ended.")
        self.assertEqual(engagement.line_ids.state, "waived")
        self.assertIn("Agreed", engagement.line_ids.waive_reason)

    def test_engagement_of_another_client_is_refused(self):
        engagement = self.engagement(client=self.client_b)
        with self.assertRaises(ValidationError):
            self.make_matter(name="Wrong client", engagement_id=engagement.id)

    def test_invoiced_line_is_locked(self):
        engagement = self.engagement(fee_type="installments")
        engagement.line_ids = [(0, 0, {"name": "Fee", "trigger_event": "manual", "amount": 100})]
        line = engagement.line_ids
        line.sudo().state = "invoiced"
        with self.assertRaises(UserError):
            line.with_user(self.billing).write({"amount": 200})
        with self.assertRaises(UserError):
            line.with_user(self.billing).unlink()
