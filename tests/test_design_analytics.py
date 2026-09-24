# -*- coding: utf-8 -*-
"""The managers' analytics board: who may read it, that it is bounded, that
every number is the count of the records it opens, and that it reads as the
user (record rules apply)."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import M, LdmCase


@tagged("post_install", "-at_install", "ldm")
class TestDesignAnalytics(LdmCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["legal.task"])
        cls.suit = cls.make_matter(name="LDM Analytics suit", kind="litigation", state="in_progress",
                                   department_id=cls.court.id, our_role="plaintiff", matter_value=5_000_000)
        cls.defence = cls.make_matter(client=cls.client_b, name="LDM Analytics defence", kind="litigation",
                                      state="in_progress", department_id=cls.court.id, our_role="defendant",
                                      matter_value=2_000_000)
        cls.filing = cls.make_matter(name="LDM Analytics filing", kind="government", state="pending_docs",
                                     department_id=cls.registry_body.id)
        cls.env["legal.task.expense"].create({"task_id": cls.suit.id, "name": "Court fee", "amount": 150_000,
                                              "date": cls.today})

    def board(self, user, period="12m"):
        return self.env["legal.task"].with_user(user).ldm_analytics(period)

    def test_only_managers_and_auditors_read_it(self):
        for user in (self.lawyer, self.clerk, self.approver, self.billing):
            with self.assertRaises(AccessError, msg=user.login):
                self.board(user)
        self.assertTrue(self.board(self.manager)["charts"])
        self.assertTrue(self.board(self.auditor)["charts"])

    def test_the_board_offers_nothing_but_lists_to_open(self):
        """Read-only for everyone: every clickable thing is a list of records."""
        payload = self.board(self.auditor)
        actions = [f["action"] for f in payload["figures"]]
        for chart in payload["charts"].values():
            actions += [item["action"] for item in chart.get("items", [])]
            for serie in chart.get("series", []):
                actions += serie["actions"]
        self.assertTrue(actions)
        for action in actions:
            self.assertEqual(set(action), {"model", "domain", "name"})
        menu = self.env.ref(f"{M}.menu_ldm_analytics")
        self.assertEqual(set(menu.group_ids.mapped(lambda g: g.get_external_id()[g.id])),
                         {f"{M}.group_legal_manager", f"{M}.group_ldm_auditor"})

    def test_every_count_is_the_count_of_what_it_opens(self):
        payload = self.board(self.manager)
        env = self.env(user=self.manager)
        for figure in payload["figures"]:
            action = figure["action"]
            self.assertEqual(figure["value"], env[action["model"]].search_count(action["domain"]), figure["key"])
        for key, chart in payload["charts"].items():
            if chart["unit"] != "count":
                continue
            for item in chart.get("items", []):
                action = item["action"]
                self.assertEqual(item["value"], env[action["model"]].search_count(action["domain"]), key)
            for serie in chart.get("series", []):
                for value, action in zip(serie["values"], serie["actions"]):
                    self.assertEqual(value, env[action["model"]].search_count(action["domain"]), key)

    def test_money_is_the_sum_of_what_it_opens(self):
        payload = self.board(self.manager)
        env = self.env(user=self.manager)
        expenses = payload["charts"]["expenses"]
        for serie in expenses["series"]:
            for value, action in zip(serie["values"], serie["actions"]):
                lines = env[action["model"]].search(action["domain"])
                self.assertAlmostEqual(value, sum(lines.mapped("amount_company")), places=2)
        exposure = {i["label"]: i for i in payload["charts"]["exposure"]["items"]}
        for item in exposure.values():
            matters = env["legal.task"].search(item["action"]["domain"])
            self.assertEqual(item["count"], len(matters))
        self.assertGreaterEqual(payload["charts"]["exposure"]["total_for"], 5_000_000)
        self.assertGreaterEqual(payload["charts"]["exposure"]["total_against"], 2_000_000)

    def test_it_is_bounded(self):
        payload = self.board(self.manager, "12m")
        charts = payload["charts"]
        self.assertLessEqual(len(charts["by_body"]["items"]), 11)
        self.assertLessEqual(len(charts["time_to_close"]["items"]), 10)
        self.assertLessEqual(len(charts["past_target"]["items"]), 10)
        self.assertLessEqual(len(charts["workload"]["labels"]), 15)
        self.assertLessEqual(len(charts["expenses"]["series"]), 6)
        self.assertLessEqual(len(charts["expenses"]["labels"]), 12)
        self.assertLessEqual(len(charts["deadlines"]["labels"]), 12)
        self.assertEqual(len(self.board(self.manager, "month")["charts"]["deadlines"]["labels"]), 1)
        self.assertEqual(self.board(self.manager, "anything")["period"], "year")

    def test_it_reads_as_the_user(self):
        """A record rule that hides a client's matters from the auditor hides
        them from the board too: nothing is counted with sudo."""
        # A global rule (group rules are OR-ed with the auditor's "see all"),
        # restricting only this auditor.
        self.env["ir.rule"].create({
            "name": "LDM test: this auditor does not see client B",
            "model_id": self.env.ref(f"{M}.model_legal_task").id,
            "domain_force": f"[(1, '=', 1)] if user.id != {self.auditor.id} "
                            f"else [('legal_company_id', '!=', {self.client_b.id})]",
        })
        seen = self.board(self.auditor)
        open_figure = next(f for f in seen["figures"] if f["key"] == "open")
        self.assertEqual(open_figure["value"], self.env["legal.task"].with_user(self.auditor).search_count(
            [("company_id", "=", self.env.company.id), ("state", "in", ["draft", "in_progress", "pending_docs"])]))
        manager = self.board(self.manager)
        self.assertAlmostEqual(
            manager["charts"]["exposure"]["total_against"] - seen["charts"]["exposure"]["total_against"],
            self.defence.matter_value, places=2, msg="The defence belongs to client B, hidden from this auditor")

    def test_time_to_close_is_the_median_in_working_days(self):
        template = self.env["legal.task.template"].create({"name": "LDM Analytics type", "kind": "government"})
        company = self.env.company
        opened = self.today - timedelta(days=60)
        durations = (3, 7, 12)
        matters = self.env["legal.task"]
        for days in durations:
            matters |= self.make_matter(name=f"LDM closed {days}", template_id=template.id, date_opened=opened)
        self.env.flush_all()
        for matter, days in zip(matters, durations):
            closed = company.ldm_add_working_days(opened, days)
            self.assertLessEqual(closed, self.today)
            self.env.cr.execute("UPDATE legal_task SET state = 'done', date_closed = %s WHERE id = %s",
                                [closed, matter.id])
        self.env.invalidate_all()
        items = {i["label"]: i for i in self.board(self.manager, "12m")["charts"]["time_to_close"]["items"]}
        self.assertEqual(items["LDM Analytics type"]["value"], 7)
        self.assertEqual(items["LDM Analytics type"]["count"], 3)
