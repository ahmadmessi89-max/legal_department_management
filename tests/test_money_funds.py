# -*- coding: utf-8 -*-
"""Client money that never goes below zero, expenses paid from it, runner
advances and their settlement, and the recharge defaults of expenses."""
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .test_money_common import MoneyCase


@tagged("post_install", "-at_install", "ldm")
class TestMoneyFunds(MoneyCase):

    def fund(self, user=None, **vals):
        values = {"legal_company_id": self.client_a.id, "kind": "deposit", "amount": 100_000,
                  "currency_id": self.cur.id}
        values.update(vals)
        return self.env["legal.client.fund.line"].with_user(user or self.env.user).create(values)

    def balance(self, client=None, currency=None):
        balances = self.env["legal.client.fund.line"]._ldm_balances(client or self.client_a)
        return balances.get((client or self.client_a).id, {}).get(currency or self.cur, 0.0)

    # ------------------------------------------------------------------
    # Client money
    # ------------------------------------------------------------------
    def test_balance_never_goes_below_zero(self):
        self.fund(user=self.lawyer)
        self.assertEqual(self.balance(), 100_000)
        with self.assertRaises(ValidationError):
            self.fund(user=self.lawyer, kind="disbursement", amount=150_000)
        self.fund(user=self.lawyer, kind="disbursement", amount=60_000)
        self.assertEqual(self.balance(), 40_000)
        # Per currency: money held in one currency does not cover another.
        with self.assertRaises(ValidationError):
            self.fund(user=self.lawyer, kind="refund", amount=10, currency_id=self.usd.id)

    def test_deleting_a_deposit_cannot_leave_a_hole(self):
        deposit = self.fund()
        self.fund(kind="disbursement", amount=80_000)
        with self.assertRaises(ValidationError):
            deposit.with_user(self.manager).unlink()

    def test_manager_may_override_with_a_reason(self):
        with self.assertRaises(AccessError):
            self.fund(user=self.lawyer, kind="disbursement", amount=50_000, override_reason="urgent")
        with self.assertRaises(ValidationError):
            self.fund(user=self.manager, kind="disbursement", amount=50_000)
        line = self.fund(user=self.manager, kind="disbursement", amount=50_000,
                         override_reason="Court fee paid before the client's transfer arrived.")
        self.assertEqual(self.balance(), -50_000)
        with self.assertRaises(AccessError):
            line.with_user(self.lawyer).write({"override_reason": "changed"})

    def test_fund_dialog(self):
        self.fund()
        Wizard = self.env["legal.fund.move.wizard"].with_user(self.lawyer)
        context = {"default_kind": "disbursement", "default_legal_company_id": self.client_a.id}
        values = Wizard.with_context(context).default_get(list(Wizard._fields))
        draft = Wizard.with_context(context).new(dict(values, amount=150_000))
        self.assertEqual(draft.balance, 100_000)
        self.assertEqual(draft.balance_after, -50_000)
        self.assertTrue(draft.goes_negative)
        self.assertFalse(Wizard.new({}).goes_negative)
        wizard = Wizard.with_context(context).create(dict(values, amount=150_000))
        with self.assertRaises(UserError):
            wizard.action_confirm()
        wizard.amount = 30_000
        wizard.action_confirm()
        self.assertEqual(self.balance(), 70_000)

    def test_expense_from_client_money_writes_one_disbursement(self):
        self.fund(amount=300_000)
        matter = self.make_matter(name="Registration")
        expense = self.env["legal.task.expense"].with_user(self.lawyer).create({
            "task_id": matter.id, "name": "Registration fee", "category_id": self.cat_gov.id, "amount": 120_000,
            "currency_id": self.cur.id, "paid_by": "client_funds", "receipt_number": "4471"})
        line = expense.sudo().fund_line_id
        self.assertEqual(line.kind, "disbursement")
        self.assertEqual(line.amount, 120_000)
        self.assertEqual(line.receipt_number, "4471")
        self.assertFalse(expense.recoverable, "paid with the client's own money: nothing to recharge")
        self.assertEqual(self.balance(), 180_000)
        expense.with_user(self.lawyer).amount = 100_000
        self.assertEqual(self.balance(), 200_000)
        with self.assertRaises(UserError):
            line.with_user(self.lawyer).write({"amount": 1})
        expense.with_user(self.lawyer).paid_by = "office"
        self.assertFalse(expense.sudo().fund_line_id)
        self.assertEqual(self.balance(), 300_000)
        with self.assertRaises(ValidationError):
            self.env["legal.task.expense"].with_user(self.lawyer).create({
                "task_id": matter.id, "name": "Too much", "amount": 400_000, "currency_id": self.cur.id,
                "paid_by": "client_funds"})

    # ------------------------------------------------------------------
    # Runner advances
    # ------------------------------------------------------------------
    def test_advance_settlement(self):
        Advance = self.env["legal.advance"]
        advance = Advance.with_user(self.billing).create({
            "name": "Tax clearance fees", "user_id": self.clerk.id, "amount": 200_000, "currency_id": self.cur.id})
        with self.assertRaises(AccessError):
            advance.with_user(self.clerk).action_ldm_hand_over()
        advance.with_user(self.billing).action_ldm_hand_over()
        self.assertEqual(advance.state, "paid")
        self.assertEqual(Advance.with_user(self.clerk).ldm_my_balance()["lines"][0]["balance"], 200_000)

        matter = self.make_matter(name="Clearance", lawyer_ids=[(6, 0, [self.lawyer.id, self.clerk.id])])
        first = self.env["legal.task.expense"].with_user(self.clerk).create({
            "task_id": matter.id, "name": "Stamp", "amount": 70_000, "currency_id": self.cur.id,
            "paid_by": "employee"})
        self.assertEqual(first.employee_user_id, self.clerk)
        self.assertEqual(first.advance_id, advance, "the open advance is used automatically")
        second = self.env["legal.task.expense"].with_user(self.clerk).create({
            "task_id": matter.id, "name": "Fee", "amount": 100_000, "currency_id": self.cur.id,
            "paid_by": "employee"})
        self.assertEqual(advance.balance, 30_000)
        self.assertEqual(Advance.with_user(self.clerk).ldm_my_balance()["lines"][0]["balance"], 30_000)

        Wizard = self.env["legal.advance.settle.wizard"].with_user(self.billing)
        context = {"default_advance_id": advance.id}
        values = Wizard.with_context(context).default_get(list(Wizard._fields))
        self.assertEqual(values["returned_amount"], 30_000)
        draft = Wizard.with_context(context).new(values)
        self.assertEqual(draft.expense_ids._origin, first | second)
        self.assertEqual(draft.balance, 0)
        wizard = Wizard.with_context(context).create(dict(values, returned_amount=10_000))
        with self.assertRaises(UserError):
            wizard.action_confirm()
        wizard.returned_amount = 30_000
        wizard.action_confirm()
        self.assertEqual(advance.state, "settled")
        self.assertEqual(advance.balance, 0)
        self.assertEqual(Advance.with_user(self.clerk).ldm_my_balance()["count"], 0)
        with self.assertRaises(UserError):
            first.with_user(self.clerk).write({"amount": 1})

    def test_overspent_advance_settles_with_the_office_owing(self):
        advance = self.env["legal.advance"].create({"name": "Fees", "user_id": self.clerk.id, "amount": 50_000,
                                                    "currency_id": self.cur.id})
        advance.action_ldm_hand_over()
        matter = self.make_matter(name="Clearance", lawyer_ids=[(6, 0, [self.lawyer.id, self.clerk.id])])
        expense = self.env["legal.task.expense"].with_user(self.clerk).create({
            "task_id": matter.id, "name": "Fee", "amount": 65_000, "currency_id": self.cur.id, "paid_by": "employee"})
        advance._ldm_settle(expense, 0)
        self.assertEqual(advance.state, "settled")
        self.assertEqual(advance.balance, -15_000)

    def test_advance_must_be_the_employees_own(self):
        advance = self.env["legal.advance"].create({"name": "Fees", "user_id": self.clerk.id, "amount": 50_000,
                                                    "currency_id": self.cur.id})
        advance.action_ldm_hand_over()
        matter = self.make_matter(name="Clearance")
        with self.assertRaises(ValidationError):
            self.env["legal.task.expense"].create({
                "task_id": matter.id, "name": "Fee", "amount": 1_000, "currency_id": self.cur.id,
                "paid_by": "employee", "employee_user_id": self.lawyer.id, "advance_id": advance.id})

    # ------------------------------------------------------------------
    # Recharge defaults
    # ------------------------------------------------------------------
    def test_recoverable_defaults_by_mode_and_category(self):
        matter = self.make_matter(name="Any")
        Expense = self.env["legal.task.expense"]
        base = {"task_id": matter.id, "name": "x", "amount": 1, "currency_id": self.cur.id}
        self.assertTrue(Expense.create(dict(base, category_id=self.cat_court.id)).recoverable)
        self.assertFalse(Expense.create(dict(base, category_id=self.cat_transport.id)).recoverable)
        self.assertFalse(Expense.create(dict(base, category_id=self.cat_court.id, paid_by="client")).recoverable)
        self.env["res.config.settings"]._ldm_apply_preset("department")
        self.assertFalse(Expense.create(dict(base, category_id=self.cat_court.id)).recoverable,
                         "a department recharges nothing by default")

    def test_only_managers_delete_expenses(self):
        matter = self.make_matter(name="Any")
        expense = self.env["legal.task.expense"].with_user(self.lawyer).create({
            "task_id": matter.id, "name": "x", "amount": 1, "currency_id": self.cur.id})
        with self.assertRaises(UserError):
            expense.with_user(self.lawyer).unlink()
        expense.with_user(self.manager).unlink()
