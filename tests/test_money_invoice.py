# -*- coding: utf-8 -*-
"""To invoice, the invoice dialog, the statement of account, and reading a
billed matter without accounting rights."""
from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .test_money_common import MoneyCase


@tagged("post_install", "-at_install", "ldm")
class TestMoneyInvoice(MoneyCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.config.settings"]._ldm_apply_preset("office")
        time_group = cls.env.ref("legal_department_management.group_ldm_time")
        cls.env.ref("base.group_user").sudo()._apply_group(time_group)
        cls.eng = cls.engagement(fee_type="installments", amount=2_000_000, hourly_rate=100_000)
        cls.eng.line_ids = [
            Command.create({"name": "On signing", "trigger_event": "signing", "amount": 1_000_000}),
            Command.create({"name": "At judgment", "trigger_event": "judgment_first_instance", "amount": 1_000_000}),
        ]
        cls.matter = cls.make_matter(name="Contract dispute", engagement_id=cls.eng.id)
        cls.eng.write({"signed": True})
        cls.eng.action_ldm_activate()
        cls.time = cls.env["legal.time.entry"].create({
            "task_id": cls.matter.id, "user_id": cls.lawyer.id, "duration": 2.5, "description": "Drafted the claim"})
        cls.time.action_ldm_approve()
        cls.expense = cls.env["legal.task.expense"].create({
            "task_id": cls.matter.id, "name": "Court fee", "category_id": cls.cat_court.id, "amount": 250_000,
            "currency_id": cls.cur.id, "receipt_number": "R-1"})
        cls.expense_usd = cls.env["legal.task.expense"].create({
            "task_id": cls.matter.id, "name": "Expert", "category_id": cls.cat_court.id, "amount": 300,
            "currency_id": cls.usd.id})

    def open_wizard(self, user, items):
        Wizard = self.env["legal.invoice.wizard"].with_user(user)
        context = {"active_model": "legal.billable", "active_ids": items.ids}
        values = Wizard.with_context(context).default_get(["billable_ids", "journal_id", "invoice_date"])
        return Wizard.with_context(context).create(values)

    def test_to_invoice_lists_the_three_sources(self):
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        self.assertEqual(set(items.mapped("kind")), {"fee", "time", "expense"})
        self.assertEqual(len(items), 4, "one due instalment, the time, two expenses")
        self.assertEqual(sum(items.filtered(lambda i: i.kind == "time").mapped("amount")), 250_000)
        self.assertEqual(self.matter.billing_state, "to_invoice")

    def test_wizard_default_get_and_new(self):
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        Wizard = self.env["legal.invoice.wizard"].with_user(self.billing)
        context = {"active_model": "legal.billable", "active_ids": items.ids}
        values = Wizard.with_context(context).default_get(["billable_ids", "journal_id", "invoice_date"])
        self.assertTrue(values.get("journal_id"))
        draft = Wizard.with_context(context).new(values)
        self.assertEqual(draft.invoice_count, 2, "one invoice per currency")
        self.assertEqual(Wizard.new({}).invoice_count, 0)

    def test_one_invoice_per_client_and_currency_with_links(self):
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        wizard = self.open_wizard(self.billing, items)
        wizard.action_create()
        moves = self.env["account.move"].search([("ldm_task_ids", "in", self.matter.id)])
        self.assertEqual(len(moves), 2)
        local = moves.filtered(lambda m: m.currency_id == self.cur)
        foreign = moves.filtered(lambda m: m.currency_id == self.usd)
        self.assertEqual(local.move_type, "out_invoice")
        self.assertEqual(local.partner_id, self.client_a.partner_id)
        self.assertEqual(local.invoice_user_id, self.eng.lawyer_id)
        self.assertEqual(local.amount_total, 1_000_000 + 250_000 + 250_000)
        self.assertEqual(foreign.amount_total, 300)
        fee_line = self.eng.line_ids.filtered(lambda l: l.trigger_event == "signing")
        self.assertEqual(fee_line.state, "invoiced")
        self.assertEqual(fee_line.invoice_line_id.move_id, local)
        self.assertEqual(self.time.state, "invoiced")
        self.assertEqual(self.time.invoice_line_id.move_id, local)
        self.assertEqual(self.time.invoice_line_id.quantity, 2.5)
        self.assertTrue(self.expense.billed)
        self.assertEqual(self.expense_usd.invoice_line_id.move_id, foreign)
        self.assertFalse(self.env["legal.billable"].search([("task_id", "=", self.matter.id)]))
        self.matter.invalidate_recordset(["billing_state", "invoice_ids"])
        self.assertEqual(self.matter.billing_state, "invoiced")
        self.assertEqual(self.matter.sudo().invoice_ids, moves)

    def test_cancelling_the_invoice_frees_the_sources(self):
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        self.open_wizard(self.billing, items).action_create()
        moves = self.env["account.move"].search([("ldm_task_ids", "in", self.matter.id)])
        moves.button_cancel()
        self.assertEqual(self.time.state, "approved")
        self.assertFalse(self.expense.billed)
        self.assertEqual(self.eng.line_ids.filtered(lambda l: l.trigger_event == "signing").state, "due")
        self.assertEqual(len(self.env["legal.billable"].search([("task_id", "=", self.matter.id)])), 4)

    def test_invoicing_needs_invoicing_rights(self):
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        with self.assertRaises(AccessError):
            self.env["legal.invoice.wizard"].with_user(self.lawyer).ldm_open(billables=items)

    def test_bar_withholding_on_retainers(self):
        retainer = self.engagement(client=self.client_b, fee_type="retainer", amount=400_000, bar_withholding=True,
                                   date_start=self.today)
        retainer.action_ldm_activate()
        items = self.env["legal.billable"].search([("engagement_id", "=", retainer.id)])
        self.assertEqual(len(items), 1)
        self.open_wizard(self.billing, items).action_create()
        move = retainer.line_ids.filtered(lambda l: l.state == "invoiced").invoice_line_id.move_id
        self.assertEqual(move.amount_total, 400_000 * 0.95)

    def test_statement_totals_per_currency(self):
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        self.open_wizard(self.billing, items).action_create()
        moves = self.env["account.move"].search([("ldm_task_ids", "in", self.matter.id)])
        moves.action_post()
        local = moves.filtered(lambda m: m.currency_id == self.cur)
        register = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=local.ids).create({"amount": 500_000})
        register._create_payments()
        self.env["legal.client.fund.line"].create({"legal_company_id": self.client_a.id, "kind": "deposit",
                                                   "amount": 75_000, "currency_id": self.cur.id})
        future = self.eng.line_ids.filtered(lambda l: l.state == "planned")
        self.assertTrue(future)
        report = self.env["report.legal_department_management.report_ldm_statement"].with_user(self.billing)
        values = report._get_report_values(self.client_a.ids, {"date_from": "2000-01-01",
                                                               "date_to": str(self.today)})
        sections = {s["currency"]: s for s in values["sections"][self.client_a.id]}
        self.assertEqual(sections[self.cur]["invoiced"], 1_500_000)
        self.assertEqual(sections[self.cur]["paid"], 500_000)
        self.assertEqual(sections[self.cur]["closing"], 1_000_000)
        self.assertEqual(sections[self.cur]["funds"], 75_000)
        self.assertEqual(sections[self.cur]["schedule_total"], 1_000_000)
        self.assertEqual(sections[self.usd]["closing"], 300)
        self.assertEqual(sections[self.usd]["paid"], 0)
        # The PDF renders.
        html = self.env["ir.actions.report"].with_user(self.billing)._render_qweb_html(
            "legal_department_management.report_ldm_statement", self.client_a.ids,
            data={"date_from": "2000-01-01", "date_to": str(self.today)})[0]
        self.assertIn(b"Statement of account", html)

    def test_statement_needs_accounting_rights(self):
        report = self.env["report.legal_department_management.report_ldm_statement"].with_user(self.lawyer)
        with self.assertRaises(AccessError):
            report._get_report_values(self.client_a.ids, {})
        with self.assertRaises(AccessError):
            self.client_a.with_user(self.lawyer).action_ldm_statement()

    def test_fee_agreement_prints(self):
        html = self.env["ir.actions.report"]._render_qweb_html(
            "legal_department_management.report_ldm_engagement", self.eng.ids)[0]
        self.assertIn(b"Payment schedule", html)

    def test_billed_matter_opens_for_every_role(self):
        """Clerks, lawyers, billing and auditors open a billed matter and its
        client without tripping over the accounting fields."""
        items = self.env["legal.billable"].search([("task_id", "=", self.matter.id)])
        self.open_wizard(self.billing, items).action_create()
        self.env["account.move"].search([("ldm_task_ids", "in", self.matter.id)]).action_post()
        self.matter.lawyer_ids = [Command.link(self.clerk.id)]
        for user in (self.clerk, self.lawyer, self.billing, self.auditor, self.manager):
            # The clerk reads fee agreements too (SPEC 14.2).
            for model, record in (("legal.task", self.matter), ("legal.company", self.client_a),
                                  ("legal.task.expense", self.expense), ("legal.engagement", self.eng)):
                Model = self.env[model].with_user(user)
                views = Model.get_views([(False, "form")])
                arch = etree.fromstring(views["views"]["form"]["arch"])
                names = {node.get("name") for node in arch.iter("field")
                         if node.getparent() is not None and node.get("name") in Model._fields}
                spec = {name: {} for name in names if Model._fields[name].type not in ("one2many", "many2many")}
                Model.browse(record.id).web_read(spec)
                self.matter.with_user(user).read(["billing_state", "ldm_fund_balance_text", "ldm_conflict_state"])
