# -*- coding: utf-8 -*-
"""Shared set-up for the money stream's tests: the law-office preset, a second
currency with a known rate, fee agreements and expense categories."""
from odoo import fields

from .common import M, LdmCase

RATE = 1310.0  # company currency units for one unit of the second currency


class MoneyCase(LdmCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.config.settings"]._ldm_apply_preset("office")
        cls.cur = cls.env.company.currency_id
        other = cls.env.ref("base.USD") if cls.cur != cls.env.ref("base.USD") else cls.env.ref("base.EUR")
        other.active = True
        cls.env["res.currency.rate"].search([("currency_id", "in", (other | cls.cur).ids)]).unlink()
        cls.env["res.currency.rate"].create({
            "name": "2020-01-01", "currency_id": other.id, "rate": 1.0 / RATE, "company_id": cls.env.company.id})
        cls.usd = other
        cls.cat_court = cls.env.ref(f"{M}.ldm_expense_category_court_fee")
        cls.cat_transport = cls.env.ref(f"{M}.ldm_expense_category_transport")
        cls.cat_gov = cls.env.ref(f"{M}.ldm_expense_category_government_fee")
        cls.today = fields.Date.context_today(cls.env["legal.task"])

    @classmethod
    def engagement(cls, client=None, **vals):
        client = client or cls.client_a
        values = {"legal_company_id": client.id, "lawyer_id": client.lawyer_id.id, "fee_type": "lump_sum",
                  "amount": 1000000, "currency_id": cls.cur.id}
        values.update(vals)
        return cls.env["legal.engagement"].create(values)

    @classmethod
    def started(cls, matter):
        matter.write({"state": "in_progress"})
        return matter

    def close(self, matter, outcome="won", user=None, **extra):
        wizard = self.env["legal.task.decision.wizard"].with_user(user or self.env.user).create(
            dict({"task_ids": [(6, 0, matter.ids)], "mode": "close", "outcome": outcome}, **extra))
        wizard.action_confirm()
        return wizard
