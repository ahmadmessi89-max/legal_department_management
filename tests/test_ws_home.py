# -*- coding: utf-8 -*-
"""The first screen as a dashboard with actions: every role is offered what it
starts from, and every figure opens exactly what it counted."""
from odoo.tests import tagged

from .common import M
from .ws_common import WsCase

TARGETS = {"wizard", "action", "list", "form", "band", "anchor"}


@tagged("post_install", "-at_install", "ldm")
class TestWsHome(WsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.suit = cls.open_matter(name="Supply contract claim", kind="litigation", department_id=cls.court.id)
        cls.step(cls.suit, "Draft the petition", -2)
        cls.session = cls.Hearing.create({"task_id": cls.suit.id, "date": cls.today, "time": 10.0,
                                          "attending_user_id": cls.lawyer.id})
        cls.Deadline.create({"task_id": cls.suit.id, "name": "Reply due", "date_safe": cls.day(3),
                             "user_id": cls.lawyer.id, "company_id": cls.company.id})
        cls.gov = cls.open_matter(name="Tax clearance", kind="government", department_id=cls.registry_body.id,
                                  lawyer_ids=[(6, 0, [cls.lawyer.id, cls.clerk.id])])
        cls.step(cls.gov, "Submit the file at the counter", 0, user=cls.clerk, is_visit=True,
                 department_id=cls.registry_body.id)
        cls.roles = {"manager": cls.manager, "lawyer": cls.lawyer, "clerk": cls.clerk, "approver": cls.approver,
                     "auditor": cls.auditor, "billing": cls.billing}

    def home(self, user, scope=None):
        self.env.invalidate_all()
        return self.env["legal.task"].with_user(user).get_my_day(scope)

    def test_every_role_starts_from_its_actions(self):
        for role, user in self.roles.items():
            payload = self.home(user)
            actions = payload["actions"]
            self.assertTrue(actions, role)
            self.assertLessEqual(len(actions), 6, role)
            # One primary action, and it comes first.
            self.assertEqual([a["primary"] for a in actions], [True] + [False] * (len(actions) - 1), role)
            for action in actions:
                self.assertIn(action["target"]["type"], TARGETS, (role, action["key"]))
                self.assertTrue(action["label"], (role, action["key"]))
                if action["target"]["type"] in ("action", "wizard"):
                    self.assertTrue(self.env.ref(f"{M}.{action['target']['xmlid']}"), (role, action["key"]))
        keys = lambda user: [a["key"] for a in self.home(user)["actions"]]  # noqa: E731
        self.assertEqual(keys(self.lawyer)[0], "new_matter")
        self.assertEqual(keys(self.manager)[0], "new_matter")
        self.assertIn("outcome", keys(self.lawyer))
        self.assertNotIn("outcome", keys(self.clerk), "a clerk does not record a court session")

    def test_the_auditor_is_offered_nothing_that_creates(self):
        payload = self.home(self.auditor)
        types = {a["target"]["type"] for a in payload["actions"]}
        self.assertFalse(types & {"wizard", "form"})
        self.assertNotIn("new_matter", {a["key"] for a in payload["actions"]})

    def test_every_tile_opens_what_it_counted(self):
        for role, user in self.roles.items():
            payload = self.home(user)
            self.assertTrue(payload["tiles"], role)
            self.assertLessEqual(len(payload["tiles"]), 6, role)
            for tile in payload["tiles"]:
                target = tile["target"]
                self.assertIn(target["type"], TARGETS, (role, tile["key"]))
                if target["type"] == "list" and tile.get("count") is not None:
                    counted = self.env[target["model"]].with_user(user).search_count(target["domain"])
                    self.assertEqual(counted, tile["count"], (role, tile["key"]))
                elif target["type"] == "band":
                    self.assertEqual(tile["count"], self.band(payload, target["band"])["count"], (role, tile["key"]))

    def test_record_a_session_counts_the_sessions_to_record(self):
        payload = self.home(self.lawyer)
        outcome = next(a for a in payload["actions"] if a["key"] == "outcome")
        self.assertGreaterEqual(outcome["count"], 1)
        target = outcome["target"]
        sessions = self.env["legal.hearing"].with_user(self.lawyer).search(target["domain"])
        self.assertIn(self.session, sessions)
        self.assertEqual(len(sessions), outcome["count"])

    def test_the_clerks_visits_lead_to_the_route(self):
        payload = self.home(self.clerk)
        visits = sum(len(group["visits"]) for group in payload["by_body"])
        action = next(a for a in payload["actions"] if a["key"] == "visits")
        self.assertEqual(action["count"], visits)
        self.assertEqual(action["target"], {"type": "anchor", "ref": "route"})
        tile = next(t for t in payload["tiles"] if t["key"] == "visits")
        self.assertEqual(tile["count"], visits)

    def test_where_the_work_is_for_those_who_oversee(self):
        self.assertFalse(self.home(self.lawyer)["glance"])
        self.assertFalse(self.home(self.billing)["glance"])
        for user in (self.manager, self.auditor):
            glance = {panel["key"]: panel for panel in self.home(user, "all")["glance"]}
            self.assertIn("kind", glance)
            self.assertIn("lawyer", glance)
            Task = self.env["legal.task"].with_user(user)
            for panel in glance.values():
                self.assertEqual(max(row["share"] for row in panel["rows"]), 100.0)
                for row in panel["rows"]:
                    self.assertEqual(Task.search_count(row["domain"]), row["count"], (panel["key"], row["label"]))
            late = {row["key"]: row["late"] for row in glance["lawyer"]["rows"]}
            self.assertGreaterEqual(late.get(self.lawyer.id, 0), 1, "the lawyer's late step shows on his bar")

    def test_an_arabic_reader_gets_every_label_in_arabic(self):
        if "ar_001" not in {code for code, _name in self.env["res.lang"].get_installed()}:
            self.skipTest("Arabic is not installed in this database")
        arabic = lambda text: any("\u0600" <= char <= "\u06ff" for char in text or "")  # noqa: E731
        for role in ("manager", "lawyer", "clerk", "approver", "auditor", "billing"):
            # A web request reads in the user's language; the test context is
            # English, so the language is asked for as a request would carry it.
            self.env.invalidate_all()
            payload = self.env["legal.task"].with_user(self.roles[role]).with_context(lang="ar_001").get_my_day()
            for part in ("actions", "tiles"):
                for item in payload[part]:
                    self.assertTrue(arabic(item["label"]), (role, part, item["key"], item["label"]))
                    if item.get("hint"):
                        self.assertTrue(arabic(item["hint"]), (role, part, item["key"], item["hint"]))
            for panel in payload["glance"]:
                self.assertTrue(arabic(panel["title"]), (role, panel["key"]))

    def test_every_role_has_my_day_in_its_menu(self):
        menu = self.env.ref(f"{M}.menu_legal_dashboard_main")
        for role, user in self.roles.items():
            self.assertIn(menu.id, self.env["ir.ui.menu"].with_user(user)._visible_menu_ids(), role)

    def test_billing_starts_from_money_not_the_teams_work(self):
        payload = self.home(self.billing)
        self.assertFalse(payload["work"])
        self.assertFalse(payload["agenda"])
        self.assertFalse(payload["all_clear"])
        kinds = {row["kind"] for row in self.rows(payload)}
        self.assertFalse(kinds & {"step", "visit", "hearing", "deadline", "target", "idle", "waiting"})
        keys = [action["key"] for action in payload["actions"]]
        if "to_invoice" in keys:
            self.assertEqual(keys[0], "to_invoice")
        self.assertTrue(self.home(self.lawyer)["work"])

    def test_every_role_but_managers_keeps_to_seven_top_menus(self):
        root = self.env.ref(f"{M}.menu_legal_root")
        for role, user in self.roles.items():
            visible = self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()
            top = root.child_id.filtered(lambda menu: menu.id in visible)
            if role != "manager":
                self.assertLessEqual(len(top), 7, (role, top.mapped("name")))
        # The auditor still reads approvals, under Reports, when they are switched on.
        if self.env["legal.task"]._ldm_feature("group_ldm_approvals"):
            visible = self.env["ir.ui.menu"].with_user(self.auditor)._visible_menu_ids()
            self.assertIn(self.env.ref(f"{M}.menu_ldm_audit_decided").id, visible)
            self.assertNotIn(self.env.ref(f"{M}.menu_legal_approvals_root").id, visible)
