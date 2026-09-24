# -*- coding: utf-8 -*-
"""The conflict-of-interest check: matching, the partner hierarchy,
redaction across teams, the manager's final decision, and a pending check
holding the matter in New."""
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from ..models.money_conflict import conflict_key, names_match
from .test_money_common import MoneyCase


@tagged("post_install", "-at_install", "ldm")
class TestMoneyConflict(MoneyCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.rafidain = cls.env["legal.company"].create({
            "name": "شركة الرافدين للمقاولات", "lawyer_id": cls.lawyer2.id, "lawyer_ids": [(6, 0, [cls.lawyer2.id])]})
        cls.opponent = Partner.create({"name": "مصرف الشمال التجاري", "is_company": True})
        # lawyer2's matter for client B against the northern bank: lawyer cannot open it.
        cls.hidden = cls.make_matter(client=cls.client_b, name="Debt recovery")
        cls.env["legal.task.party"].create({"task_id": cls.hidden.id, "partner_id": cls.opponent.id,
                                            "role": "defendant"})

    def check(self, names, user=None, client=None, task=None):
        Task = self.env["legal.task"].with_user(user or self.lawyer)
        return Task.ldm_conflict_check(names, task_id=task.id if task else False,
                                       client_id=(client or self.client_a).id)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def test_arabic_normalisation(self):
        self.assertEqual(conflict_key("أحمد عبد الله"), conflict_key("احمد عبدالله"))
        self.assertEqual(conflict_key("شركة الرافدين"), conflict_key("شركه رافدين"))
        self.assertEqual(conflict_key("مصطفى"), conflict_key("مصطفي"))
        self.assertEqual(conflict_key("مُحَمَّد"), conflict_key("محمد"))
        self.assertEqual(conflict_key("محـــمد"), conflict_key("محمد"))
        self.assertEqual(conflict_key("فرع ١٢"), conflict_key("فرع 12"))
        self.assertTrue(names_match("شركة الرافدين للمقاولات العامة", "شركة الرافدين للمقاولات"))
        self.assertFalse(names_match("الرافدين", "الشمال"))

    def test_opponent_who_is_our_client_is_a_conflict(self):
        result = self.check(["شركه الرافدين للمقاولات"])
        self.assertEqual(result["decision"], "pending")
        conflicts = [h for h in result["hits"] if h["conflict"]]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["role_code"], "client")
        self.assertEqual(result["policy"], "warn")

    def test_archived_client_and_closed_matter_still_count(self):
        self.rafidain.active = False
        result = self.check(["شركة الرافدين للمقاولات"])
        self.assertEqual([h["role_code"] for h in result["hits"] if h["conflict"]], ["former_client"])
        self.hidden.sudo().write({"active": False})
        result = self.check(["مصرف الشمال التجاري"])
        self.assertTrue(result["hits"], "a party of an archived matter is still found")

    def test_retainer_client_is_named_as_such(self):
        retainer = self.engagement(client=self.rafidain, fee_type="retainer", amount=400_000)
        retainer.action_ldm_activate()
        result = self.check(["شركة الرافدين للمقاولات"])
        self.assertEqual([h["role_code"] for h in result["hits"] if h["conflict"]], ["retainer_client"])

    def test_same_opponent_again_is_seen_not_a_conflict(self):
        result = self.check(["مصرف الشمال التجاري"])
        self.assertEqual(result["decision"], "clear")
        self.assertEqual(result["conflict_count"], 0)
        self.assertEqual([h["role_code"] for h in result["hits"]], ["opponent"])

    def test_new_client_who_was_an_opponent_is_a_conflict(self):
        bank = self.env["legal.company"].create({"name": "مصرف الشمال التجاري", "partner_id": self.opponent.id,
                                                  "lawyer_id": self.lawyer.id})
        result = self.check(["شخص آخر"], client=bank)
        self.assertEqual(result["decision"], "pending")
        self.assertEqual([h["role_code"] for h in result["hits"] if h["conflict"]], ["opponent"])

    def test_subsidiary_found_through_the_group(self):
        """Research 06 F1, test 5: the Basra branch of our client's group is
        found through the partner hierarchy, not by its name."""
        group = self.rafidain.partner_id
        self.env["res.partner"].create({"name": "فرع البصرة للإنشاءات", "parent_id": group.id,
                                        "type": "other"})
        self.assertFalse(names_match("فرع البصرة للإنشاءات", self.rafidain.name))
        result = self.check(["فرع البصرة للإنشاءات"])
        self.assertEqual(result["decision"], "pending",
                         "the check must expand through commercial_partner_id / the parent company")
        subsidiary = self.env["res.partner"].create({"name": "شركة دجلة للتجارة", "is_company": True,
                                                     "parent_id": group.id})
        self.assertEqual(self.check([subsidiary.name])["decision"], "pending")

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------
    def test_hits_are_redacted_for_those_who_cannot_open_them(self):
        bank = self.env["legal.company"].create({"name": "مصرف الشمال التجاري", "partner_id": self.opponent.id,
                                                  "lawyer_id": self.lawyer.id})
        seen_by_lawyer = self.check(["شخص آخر"], client=bank)["hits"]
        self.assertTrue(seen_by_lawyer[0]["redacted"])
        self.assertFalse(seen_by_lawyer[0]["id"])
        self.assertNotIn("Debt recovery", seen_by_lawyer[0]["label"])
        self.assertIn(self.lawyer2.name, seen_by_lawyer[0]["label"])
        check = self.env["legal.conflict.check"].search([], limit=1)
        self.assertNotIn("Debt recovery", check.with_user(self.lawyer).hit_html)
        self.assertIn("Debt recovery", check.with_user(self.manager).hit_html)

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    def test_decision_is_for_managers_with_a_reason_and_final(self):
        result = self.check(["شركة الرافدين للمقاولات"])
        check = self.env["legal.conflict.check"].browse(result["check_id"])
        with self.assertRaises(AccessError):
            check.with_user(self.lawyer).ldm_decide("override", "fine")
        with self.assertRaises(UserError):
            check.with_user(self.manager).ldm_decide("override", "  ")
        Wizard = self.env["legal.conflict.decision.wizard"].with_user(self.manager)
        values = Wizard.with_context(default_check_id=check.id).default_get(list(Wizard._fields))
        Wizard.new(values)
        wizard = Wizard.create(dict(values, decision="override", reason="Different project, client informed."))
        wizard.action_confirm()
        self.assertEqual(check.decision, "override")
        self.assertEqual(check.decided_by_id, self.manager)
        with self.assertRaises(UserError):
            check.with_user(self.manager).ldm_decide("declined", "changed my mind")
        with self.assertRaises(AccessError):
            check.with_user(self.manager).write({"decision": "declined"})
        with self.assertRaises(UserError):
            check.with_user(self.manager).unlink()
        with self.assertRaises(AccessError):
            self.env["legal.conflict.check"].with_user(self.lawyer).create(
                {"query": "x", "decision": "clear", "company_id": self.env.company.id})

    def test_block_policy_refuses_an_override(self):
        self.env.company.ldm_conflict_policy = "block"
        result = self.check(["شركة الرافدين للمقاولات"])
        self.assertEqual(result["policy"], "block")
        check = self.env["legal.conflict.check"].browse(result["check_id"])
        with self.assertRaises(UserError):
            check.with_user(self.manager).ldm_decide("override", "reason")
        check.with_user(self.manager).ldm_decide("clear", "Another company with a similar name.")
        self.assertEqual(check.decision, "clear")

    # ------------------------------------------------------------------
    # On the matter
    # ------------------------------------------------------------------
    def test_pending_check_keeps_the_matter_new(self):
        matter = self.make_matter(name="Against Rafidain")
        self.env["legal.task.party"].create({"task_id": matter.id, "partner_id": self.rafidain.partner_id.id,
                                             "role": "defendant"})
        self.assertEqual(matter.ldm_conflict_state, "pending")
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).write({"state": "in_progress"})
        check = matter.sudo().ldm_conflict_check_id
        self.assertTrue(check)
        self.assertTrue(matter.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref("legal_department_management.ldm_activity_conflict")))
        check.with_user(self.manager).ldm_decide("override", "The client consented in writing.")
        self.assertEqual(matter.ldm_conflict_state, "override")
        matter.with_user(self.lawyer).write({"state": "in_progress"})
        self.assertEqual(matter.state, "in_progress")

    def test_declined_matter_cannot_start(self):
        matter = self.make_matter(name="Against Rafidain")
        self.env["legal.task.party"].create({"task_id": matter.id, "partner_id": self.rafidain.partner_id.id})
        matter.sudo().ldm_conflict_check_id.with_user(self.manager).ldm_decide("declined", "We act for them.")
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).write({"state": "in_progress"})

    def test_rerun_when_the_other_side_changes(self):
        matter = self.make_matter(name="Two opponents")
        self.env["legal.task.party"].create({"task_id": matter.id, "partner_id": self.rafidain.partner_id.id})
        first = matter.sudo().ldm_conflict_check_id
        self.env["legal.task.party"].create({"task_id": matter.id, "partner_id": self.opponent.id})
        second = matter.sudo().ldm_conflict_check_id
        self.assertNotEqual(first, second)
        self.assertEqual(first.decision, "superseded", "the complete check replaces the partial one")
        self.assertEqual(second.decision, "pending")
        # Removing a name does not clear a pending decision.
        matter.party_ids.filtered(lambda p: p.partner_id == self.rafidain.partner_id).unlink()
        self.assertEqual(matter.ldm_conflict_state, "pending")
        matter.counterparty_id = self.env["res.partner"].create({"name": "طرف ثالث"})
        self.assertEqual(len(matter.sudo().ldm_conflict_check_ids), 3)

    def test_quick_create_with_a_conflict_stays_new(self):
        result = self.check(["شركة الرافدين للمقاولات"])
        task_id = self.env["legal.task"].with_user(self.lawyer).create_from_template({
            "template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
            "opponent_name": "شركة الرافدين للمقاولات", "key_date": "2026-11-01"})
        matter = self.env["legal.task"].browse(task_id)
        self.assertEqual(matter.state, "draft")
        self.assertEqual(matter.ldm_conflict_state, "pending")
        self.assertEqual(matter.sudo().ldm_conflict_check_id.id, result["check_id"],
                         "the dialog's check is adopted, not run twice")

    def test_quick_create_without_a_conflict_starts(self):
        task_id = self.env["legal.task"].with_user(self.lawyer).create_from_template({
            "template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
            "opponent_name": "خصم جديد تماما", "key_date": "2026-11-01"})
        matter = self.env["legal.task"].browse(task_id)
        self.assertEqual(matter.ldm_conflict_state, "clear")
        self.assertEqual(matter.state, "in_progress")

    def test_nothing_runs_with_the_switch_off(self):
        self.env["res.config.settings"]._ldm_apply_preset("department")
        result = self.check(["شركة الرافدين للمقاولات"])
        self.assertFalse(result["check_id"])
        matter = self.make_matter(name="Against Rafidain")
        self.env["legal.task.party"].create({"task_id": matter.id, "partner_id": self.rafidain.partner_id.id})
        self.assertEqual(matter.ldm_conflict_state, "none")
