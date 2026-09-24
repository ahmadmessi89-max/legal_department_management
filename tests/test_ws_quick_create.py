# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import M
from .ws_common import WsCase

WIZARD = "legal.task.create.wizard"


@tagged("post_install", "-at_install", "ldm")
class TestWsQuickCreate(WsCase):

    def wizard_env(self, user=None, **context):
        return self.env[WIZARD].with_user(user or self.lawyer).with_context(**context)

    def test_default_get_and_new_draw_the_dialog(self):
        Wizard = self.wizard_env(default_legal_company_id=self.client_a.id)
        fields_list = list(Wizard._fields)
        defaults = Wizard.default_get(fields_list)
        self.assertEqual(defaults["legal_company_id"], self.client_a.id)
        self.assertEqual(defaults["fee_agreement"], "none")
        wizard = Wizard.new({})
        self.assertEqual(wizard.kind, "other")
        self.assertFalse(wizard.show_body)
        self.assertFalse(wizard.recent_template_ids)
        # The type fills the kind, shows the body input and suggests a title.
        wizard = Wizard.new({"template_id": self.t_government.id, "legal_company_id": self.client_a.id})
        wizard._onchange_suggest()
        self.assertEqual(wizard.kind, "government")
        self.assertTrue(wizard.show_body)
        self.assertEqual(wizard.name, f"{self.t_government.name} — {self.client_a.name}")
        # A title the user typed is kept when the client changes.
        wizard.name = "My own title"
        wizard.legal_company_id = self.env["legal.company"].create({
            "name": "LDM Client C", "lawyer_id": self.lawyer.id, "lawyer_ids": [(6, 0, [self.lawyer.id])]})
        wizard._onchange_suggest()
        self.assertEqual(wizard.name, "My own title")

    def test_create_and_open_generates_the_work(self):
        wizard = self.wizard_env().create({
            "template_id": self.t_government.id, "legal_company_id": self.client_a.id,
            "department_id": self.registry_body.id, "name": "Annual tax clearance"})
        result = wizard.action_create_open()
        self.assertEqual(result["tag"], "display_notification")
        next_action = result["params"]["next"]
        self.assertEqual(next_action["res_model"], "legal.task")
        task = self.env["legal.task"].browse(next_action["res_id"])
        self.assertEqual(task.name, "Annual tax clearance")
        self.assertEqual(task.state, "in_progress")
        self.assertEqual(len(task.step_ids), len(self.t_government.step_ids))
        self.assertIn(task.task_number, result["params"]["message"])
        self.assertIn(self.lawyer, task.lawyer_ids)

    def test_lawsuit_adds_session_role_and_opponent(self):
        wizard = self.wizard_env().create({
            "template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
            "department_id": self.court.id, "key_date": self.day(5), "our_role": "plaintiff",
            "opponent_name": "LDM Opponent Trading"})
        task = self.env["legal.task"].browse(wizard.action_create_open()["params"]["next"]["res_id"])
        self.assertEqual(task.kind, "litigation")
        self.assertEqual(task.our_role, "plaintiff")
        self.assertEqual(task.hearing_ids.date, self.day(5))
        self.assertEqual(task.party_ids.partner_id.name, "LDM Opponent Trading")

    def test_create_another_and_recents(self):
        first = self.wizard_env().create({"template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
                                          "department_id": self.court.id})
        result = first.action_create_another()
        self.assertEqual(result["params"]["next"]["res_model"], WIZARD)
        self.assertEqual(result["params"]["next"]["context"]["default_legal_company_id"], self.client_a.id)
        second = self.wizard_env().create({"template_id": self.t_government.id, "legal_company_id": self.client_a.id,
                                           "department_id": self.registry_body.id})
        second.action_create_open()
        recents = self.wizard_env().new({}).recent_template_ids
        self.assertEqual(recents.ids[:2], [self.t_government.id, self.t_lawsuit.id])
        # Recents are the user's own.
        self.assertFalse(self.wizard_env(self.lawyer2).new({}).recent_template_ids)

    def test_fee_agreement_existing_or_new(self):
        engagement = self.env["legal.engagement"].create({"name": "Retainer", "legal_company_id": self.client_a.id,
                                                          "state": "active"})
        wizard = self.wizard_env().create({"legal_company_id": self.client_a.id, "name": "Advice",
                                           "fee_agreement": "existing", "engagement_id": engagement.id})
        task = self.env["legal.task"].browse(wizard.action_create_open()["params"]["next"]["res_id"])
        self.assertEqual(task.engagement_id, engagement)
        wizard = self.wizard_env().create({"legal_company_id": self.client_a.id, "name": "New case",
                                           "fee_agreement": "new"})
        task = self.env["legal.task"].browse(wizard.action_create_open()["params"]["next"]["res_id"])
        self.assertEqual(task.engagement_id.state, "draft")
        self.assertEqual(task.engagement_id.legal_company_id, self.client_a)

    def _conflicts_on(self):
        self.env["res.config.settings"]._ldm_apply_preset("office")

    def test_conflict_hits_show_a_banner_and_keep_the_matter_new(self):
        self._conflicts_on()
        hits = {"hits": [{"label": "LDM Opponent", "role": "former client"}], "policy": "warn", "check_id": False}
        Task = type(self.env["legal.task"])
        with patch.object(Task, "ldm_conflict_check", autospec=True, return_value=hits) as check:
            wizard = self.wizard_env().create({"template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id,
                                               "department_id": self.court.id, "opponent_name": "LDM Opponent"})
            again = wizard.action_create_open()
            self.assertEqual(again["res_model"], WIZARD)
            self.assertEqual(again["res_id"], wizard.id)
            self.assertEqual(wizard.conflict_state, "hits")
            self.assertIn("LDM Opponent", wizard.conflict_summary)
            self.assertFalse(self.env["legal.task"].search([("opponent_name", "=", "LDM Opponent")]))
            result = wizard.action_create_despite_conflict()
            task = self.env["legal.task"].browse(result["params"]["next"]["res_id"])
            self.assertEqual(task.state, "draft")
            # The check is run again with the new matter so it is recorded against it.
            self.assertEqual(check.call_args.kwargs.get("task_id"), task.id)

    def test_conflict_block_policy_blocks(self):
        self._conflicts_on()
        hits = {"hits": [{"label": "LDM Opponent", "role": "opponent"}], "policy": "block", "check_id": False}
        Task = type(self.env["legal.task"])
        with patch.object(Task, "ldm_conflict_check", autospec=True, return_value=hits):
            wizard = self.wizard_env().create({"legal_company_id": self.client_a.id, "name": "Blocked",
                                               "opponent_name": "LDM Opponent"})
            wizard.action_create_open()
            self.assertEqual(wizard.conflict_state, "blocked")
            with self.assertRaises(UserError):
                wizard._ldm_create_matter()

    def test_no_conflict_check_without_the_switch(self):
        Task = type(self.env["legal.task"])
        with patch.object(Task, "ldm_conflict_check", autospec=True) as check:
            wizard = self.wizard_env().create({"legal_company_id": self.client_a.id, "name": "Quiet"})
            wizard.action_create_open()
            check.assert_not_called()

    def test_the_action_and_views_open(self):
        action = self.env.ref(f"{M}.action_legal_task_create_wizard")
        self.assertEqual(action.type, "ir.actions.act_window")
        self.assertEqual(action.target, "new")
        arch = self.env[WIZARD].with_user(self.lawyer).get_views([(False, "form")])["views"]["form"]["arch"]
        # The dialog opens with four inputs: type, client, key date and title.
        self.assertIn('widget="ldm_template_picker"', arch)
        self.assertIn('name="action_create_open"', arch)
        # The client label follows the organisation's words.
        self.assertIn("Client or company", arch)

    def test_suggested_target_date(self):
        self.registry_body.target_days = 4
        wizard = self.wizard_env().new({"template_id": self.t_government.id, "legal_company_id": self.client_a.id,
                                        "department_id": self.registry_body.id})
        total = self.t_government.duration_days + 4
        expected = self.company.ldm_add_working_days(self.today, total, self.registry_body._ldm_calendar())
        self.assertEqual(wizard.suggested_date, expected)
        self.assertIn("4", wizard.suggested_note)
        # A lawsuit's key date is its first session: nothing is suggested.
        lawsuit = self.wizard_env().new({"template_id": self.t_lawsuit.id, "legal_company_id": self.client_a.id})
        self.assertFalse(lawsuit.suggested_date)
