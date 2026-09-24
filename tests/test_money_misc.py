# -*- coding: utf-8 -*-
"""WhatsApp numbers and messages, time and the timer, whole dinars, posting
expenses to accounting, and the fee-agreement warnings."""
from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from ..models.money_whatsapp import normalize_iraqi_phone, render_placeholders, wa_link
from .test_money_common import MoneyCase


@tagged("post_install", "-at_install", "ldm")
class TestMoneyMisc(MoneyCase):

    # ------------------------------------------------------------------
    # WhatsApp and client messages
    # ------------------------------------------------------------------
    def test_iraqi_phone_normalisation(self):
        expected = "9647701234567"
        for typed in ("07701234567", "0770 123 4567", "+964 770 123 4567", "00964 770 123 4567",
                      "964-770-123-4567", "+964 0770 123 4567", "٠٧٧٠١٢٣٤٥٦٧", "7701234567", "(0770) 123-4567"):
            self.assertEqual(normalize_iraqi_phone(typed), expected, typed)
        self.assertEqual(normalize_iraqi_phone("+1 202 555 0100"), "12025550100")
        for bad in ("", False, "123", "abc", "55512"):
            self.assertFalse(normalize_iraqi_phone(bad), bad)
        self.assertEqual(wa_link("07701234567", "مرحبا"), "https://wa.me/9647701234567?text=%D9%85%D8%B1%D8%AD%D8%A8%D8%A7")

    def test_placeholders_never_reach_attributes(self):
        values = {"client": "Rafidain", "amount": "IQD 1,000"}
        self.assertEqual(render_placeholders("Dear {client}, {amount} due.", values), "Dear Rafidain, IQD 1,000 due.")
        text = "{client.__class__} {client[0]} {unknown} {client!r} {0}"
        self.assertEqual(render_placeholders(text, values), text)

    def test_session_result_message(self):
        self.client_a.phone = "0770 123 4567"
        matter = self.make_matter(name="Lawsuit", department_id=self.court.id)
        hearing = self.env["legal.hearing"].create({"task_id": matter.id, "date": "2026-10-04",
                                                    "department_id": self.court.id})
        following = self.env["legal.hearing"].create({"task_id": matter.id, "date": "2026-11-08"})
        hearing.write({"state": "held", "outcome": "adjourned", "next_hearing_id": following.id,
                       "needed_before": "Bring the original contract"})
        action = hearing.with_user(self.lawyer).action_ldm_client_message()
        Wizard = self.env["legal.client.message.wizard"].with_user(self.lawyer).with_context(action["context"])
        values = Wizard.default_get(list(Wizard._fields))
        draft = Wizard.new(values)
        self.assertEqual(draft.template_id, self.env.ref("legal_department_management.ldm_message_hearing_result"))
        self.assertTrue(draft.phone_ok)
        self.assertIn(self.client_a.name, draft.body)
        self.assertIn(self.court.name, draft.body)
        self.assertIn("Bring the original contract", draft.body)
        self.assertNotIn("{", draft.body)
        wizard = Wizard.create(values)
        result = wizard.action_whatsapp()
        self.assertTrue(result["url"].startswith("https://wa.me/9647701234567?text="))
        self.assertIn("WhatsApp", matter.message_ids[0].body)
        Wizard.new({}).body  # an empty dialog draws

    def test_messages_follow_the_switch_and_the_role(self):
        matter = self.make_matter(name="Any")
        self.assertTrue(matter.with_user(self.lawyer).ldm_can_message)
        self.assertFalse(matter.with_user(self.auditor).ldm_can_message)
        with self.assertRaises(AccessError):
            self.env["legal.client.message.wizard"].with_user(self.auditor).ldm_open("hearing_reminder", task=matter)
        self.env["res.config.settings"]._ldm_apply_preset("department")
        matter.invalidate_recordset(["ldm_can_message"])
        self.assertFalse(matter.with_user(self.lawyer).ldm_can_message)
        with self.assertRaises(UserError):
            self.env["legal.client.message.wizard"].with_user(self.lawyer).ldm_open("hearing_reminder", task=matter)

    def test_bad_number_is_refused(self):
        matter = self.make_matter(name="Any")
        Wizard = self.env["legal.client.message.wizard"].with_user(self.lawyer)
        wizard = Wizard.with_context(default_task_id=matter.id, default_legal_company_id=self.client_a.id).create(
            {"phone": "123", "body": "Hello"})
        with self.assertRaises(UserError):
            wizard.action_whatsapp()

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------
    def _time_on(self):
        self.env.ref("base.group_user").sudo()._apply_group(self.env.ref("legal_department_management.group_ldm_time"))

    def test_time_approval(self):
        self._time_on()
        matter = self.make_matter(name="Advice", lawyer_ids=[(6, 0, [self.lawyer.id, self.clerk.id])])
        entry = self.env["legal.time.entry"].with_user(self.clerk).create({
            "task_id": matter.id, "duration": 1.5, "description": "Called the registry", "state": "approved"})
        self.assertEqual(entry.state, "draft", "nobody creates approved time")
        with self.assertRaises(AccessError):
            entry.with_user(self.clerk).action_ldm_approve()
        with self.assertRaises(UserError):
            entry.with_user(self.clerk).write({"state": "approved"})
        entry.with_user(self.lawyer).action_ldm_approve()
        self.assertEqual(entry.state, "approved")
        with self.assertRaises(UserError):
            entry.with_user(self.clerk).write({"duration": 3})
        with self.assertRaises(UserError):
            entry.with_user(self.clerk).unlink()

    def test_timer(self):
        self._time_on()
        matter = self.make_matter(name="Advice")
        Time = self.env["legal.time.entry"].with_user(self.lawyer)
        self.assertFalse(Time.ldm_timer_state()["running"])
        state = Time.ldm_timer_start(matter.id)
        self.assertTrue(state["running"])
        self.assertEqual(state["task_id"], matter.id)
        other = self.make_matter(name="Other")
        with self.assertRaises(UserError):
            Time.ldm_timer_start(other.id)
        with self.assertRaises(UserError):
            Time.ldm_timer_stop("  ")
        result = Time.ldm_timer_stop("Reviewed the contract", billable=False, duration=0.75)
        entry = self.env["legal.time.entry"].browse(result["id"])
        self.assertEqual(entry.duration, 0.75)
        self.assertFalse(entry.billable)
        self.assertEqual(entry.user_id, self.lawyer)
        self.assertFalse(Time.ldm_timer_state()["running"])
        Time.ldm_timer_start(matter.id)
        Time.ldm_timer_discard()
        self.assertFalse(Time.ldm_timer_state()["running"])
        self.assertTrue(Time.ldm_timer_recent_matters())

    def test_timer_needs_the_switch(self):
        matter = self.make_matter(name="Advice")
        Time = self.env["legal.time.entry"].with_user(self.lawyer)
        self.assertEqual(Time.ldm_timer_state(), {"running": False, "enabled": False})
        with self.assertRaises(AccessError):
            Time.ldm_timer_start(matter.id)

    def test_timer_state_is_not_shipped_to_the_client(self):
        settings = self.env["res.users.settings"]._find_or_create_for_user(self.lawyer)
        self.assertNotIn("ldm_timer_task_ref", settings._res_users_settings_format())

    # ------------------------------------------------------------------
    # Whole dinars
    # ------------------------------------------------------------------
    def test_whole_dinars_only_before_posted_entries(self):
        iqd = self.env.ref("base.IQD")
        iqd.active = True
        Settings = self.env["res.config.settings"]
        with self.assertRaises(AccessError):
            Settings.with_user(self.manager).create({}).action_ldm_iqd_whole_dinars()
        if Settings._ldm_iqd_used():
            with self.assertRaises(UserError):
                Settings.create({}).action_ldm_iqd_whole_dinars()
            return
        iqd.rounding = 0.001
        self.assertTrue(Settings.create({}).ldm_iqd_can_round)
        Settings.create({}).action_ldm_iqd_whole_dinars()
        self.assertEqual(iqd.rounding, 1.0)
        self.assertEqual(iqd.decimal_places, 0)
        self.assertFalse(Settings.create({}).ldm_iqd_can_round)

    # ------------------------------------------------------------------
    # Accounting links
    # ------------------------------------------------------------------
    def test_expense_posted_as_entry_and_as_payment(self):
        self.env.ref("base.group_user").sudo()._apply_group(
            self.env.ref("legal_department_management.group_ldm_accounting_links"))
        account = self.env["account.account"].search(
            [("account_type", "=", "expense"), *self.env["account.account"]._check_company_domain(self.env.company)],
            limit=1)
        self.cat_court.with_company(self.env.company).account_id = account
        matter = self.make_matter(name="Any")
        Expense = self.env["legal.task.expense"]
        first = Expense.create({"task_id": matter.id, "name": "Court fee", "category_id": self.cat_court.id,
                                "amount": 50_000, "currency_id": self.cur.id})
        second = Expense.create({"task_id": matter.id, "name": "Court fee", "category_id": self.cat_court.id,
                                 "amount": 20_000, "currency_id": self.cur.id})
        self.assertFalse(first.with_user(self.lawyer).ldm_can_post)
        self.assertTrue(first.with_user(self.billing).ldm_can_post)
        with self.assertRaises(AccessError):
            first.with_user(self.lawyer).action_ldm_post()
        Wizard = self.env["legal.expense.post.wizard"].with_user(self.billing)
        action = first.with_user(self.billing).action_ldm_post()
        values = Wizard.with_context(action["context"]).default_get(list(Wizard._fields))
        self.assertTrue(values.get("journal_id"))
        Wizard.with_context(action["context"]).create(values).action_post()
        self.assertEqual(first.sudo().move_id.state, "posted")
        self.assertEqual(first.sudo().move_id.amount_total, 50_000)
        Wizard.with_context(default_expense_ids=second.ids).create(dict(values, mode="payment",
                                                                        expense_ids=[Command.set(second.ids)])
                                                                   ).action_post()
        self.assertIn(second.sudo().payment_id.state, ("in_process", "paid"))
        self.assertFalse(first.with_user(self.billing).ldm_can_post, "posted once only")

    # ------------------------------------------------------------------
    # Fee agreements on the matter
    # ------------------------------------------------------------------
    def test_no_signed_agreement_chip_and_report(self):
        matter = self.started(self.make_matter(name="Unsigned"))
        self.assertTrue(matter.ldm_no_signed_agreement)
        self.assertIn(matter, self.env["legal.task"].search([("ldm_no_signed_agreement", "=", True)]))
        engagement = self.engagement(signed=True)
        engagement.action_ldm_activate()
        matter.engagement_id = engagement
        self.assertFalse(matter.ldm_no_signed_agreement)
        self.assertNotIn(matter, self.env["legal.task"].search([("ldm_no_signed_agreement", "=", True)]))
        self.assertIn(matter, self.env["legal.task"].search([("ldm_no_signed_agreement", "=", False)]))

    def test_office_preset_warns_when_work_starts_unsigned(self):
        self.assertTrue(self.env.company.ldm_engagement_required, "the law-office preset asks for agreements")
        matter = self.started(self.make_matter(name="Unsigned"))
        activity_type = self.env.ref("legal_department_management.ldm_activity_fee_agreement")
        self.assertTrue(matter.activity_ids.filtered(lambda a: a.activity_type_id == activity_type))
        self.env["res.config.settings"]._ldm_apply_preset("hybrid")
        self.assertFalse(self.env.company.ldm_engagement_required)

    def test_instalments_due_are_reminded(self):
        engagement = self.engagement(fee_type="installments")
        matter = self.make_matter(name="Lawsuit", engagement_id=engagement.id)
        engagement.line_ids = [Command.create({"name": "Now", "trigger_event": "manual", "amount": 10,
                                               "task_id": matter.id})]
        engagement.action_ldm_activate()
        engagement.line_ids.action_ldm_mark_due()
        self.env["legal.task"]._ldm_run_reminders()
        activity_type = self.env.ref("legal_department_management.ldm_activity_fee_agreement")
        reminders = matter.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
        self.assertEqual(len(reminders), 1)
        self.env["legal.task"]._ldm_run_reminders()
        self.assertEqual(len(matter.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)), 1)

    def test_client_money_summary_on_the_dossier(self):
        self.env["legal.client.fund.line"].create({"legal_company_id": self.client_a.id, "kind": "deposit",
                                                   "amount": 250_000, "currency_id": self.cur.id})
        self.env["legal.client.fund.line"].create({"legal_company_id": self.client_a.id, "kind": "deposit",
                                                   "amount": 100, "currency_id": self.usd.id})
        text = self.client_a.ldm_fund_balance_text
        self.assertTrue(text)
        self.assertEqual(text.count("·"), 1, "one amount per currency")
        matter = self.make_matter(name="Any")
        self.assertEqual(matter.ldm_fund_balance_text, text)
