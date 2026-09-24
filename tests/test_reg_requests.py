# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegRequests(RegCase):

    def ask(self, user=None, **values):
        vals = {"name": "Review the supply contract", "request_type": "contract",
                "description": "Supplier is Al-Nahrain; signature on Sunday"}
        vals.update(values)
        return self.Request.with_user(user or self.requester).create(vals)

    def accept(self, request, user=None, **values):
        action = request.with_user(user or self.lawyer).action_ldm_accept()
        Wizard = self.env["legal.reg.matter.wizard"].with_user(user or self.lawyer).with_context(action["context"])
        wizard = Wizard.create(dict({"legal_company_id": self.client_a.id}, **values))
        result = wizard.action_create()
        return self.env["legal.task"].browse(result["res_id"])

    def test_requester_asks_for_themself(self):
        request = self.ask(requester_id=self.requester2.id, legal_company_id=self.client_b.id)
        self.assertEqual(request.requester_id, self.requester)
        self.assertFalse(request.legal_company_id)
        self.assertEqual(request.state, "new")
        # The legal managers follow new requests.
        self.assertIn(self.manager.partner_id, request.message_partner_ids)

    def test_requester_write_limits(self):
        request = self.ask()
        request.write({"name": "Review the supply contract (v2)", "needed_by": self.d("2031-01-10"),
                       "description": "Updated"})
        for values in ({"request_type": "opinion"}, {"legal_company_id": self.client_a.id},
                       {"requester_id": self.requester2.id}):
            with self.assertRaises(AccessError):
                request.write(values)
        for values in ({"state": "accepted"}, {"task_id": self.make_matter().id},
                       {"assigned_user_id": self.requester.id}, {"return_reason": "x"}):
            with self.assertRaises(AccessError):
                request.write(values)
        request.with_user(self.lawyer).action_ldm_take()
        with self.assertRaises(UserError):
            request.write({"description": "Too late"})

    def test_requesters_see_only_their_own(self):
        request = self.ask()
        with self.assertRaises(AccessError):
            request.with_user(self.requester2).read(["name"])
        self.assertEqual(self.Request.with_user(self.requester2).search_count([("id", "=", request.id)]), 0)
        self.assertEqual(request.with_user(self.clerk).name, "Review the supply contract")

    def test_clerks_do_not_triage(self):
        request = self.ask()
        with self.assertRaises(AccessError):
            request.with_user(self.clerk).action_ldm_take()
        with self.assertRaises(AccessError):
            request.with_user(self.clerk).action_ldm_accept()
        with self.assertRaises(AccessError):
            request.with_user(self.requester)._ldm_return("no")

    def test_accept_opens_and_links_a_matter(self):
        attachment = self.env["ir.attachment"].with_user(self.requester).create({
            "name": "draft-contract.pdf", "datas": base64.b64encode(b"%PDF-1.4 draft"),
            "res_model": "legal.request", "res_id": 0})
        request = self.ask(needed_by=self.d("2031-02-01"), attachment_ids=[(6, 0, attachment.ids)])
        # Uploaded before the request existed; now the legal team can open it.
        self.assertEqual((attachment.sudo().res_model, attachment.sudo().res_id), ("legal.request", request.id))
        self.assertEqual(attachment.with_user(self.lawyer).read(["name"])[0]["name"], "draft-contract.pdf")
        request.with_user(self.lawyer).action_ldm_take()
        self.assertEqual(request.state, "in_review")
        self.assertEqual(request.assigned_user_id, self.lawyer)
        action = request.with_user(self.lawyer).action_ldm_accept()
        Wizard = self.env["legal.reg.matter.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["request_id", "template_id", "name", "key_date", "lawyer_id",
                                       "legal_company_id"])
        self.assertEqual(defaults["template_id"], self.env.ref(f"{M}.ldm_template_contract_review").id)
        self.assertEqual(defaults["name"], "Review the supply contract")
        self.assertEqual(defaults["key_date"], self.d("2031-02-01"))
        self.assertEqual(Wizard.new(defaults).request_id, request)
        with self.assertRaises(UserError):
            Wizard.create({}).action_create()
        matter = self.accept(request)
        self.assertEqual(request.state, "accepted")
        self.assertEqual(request.task_id, matter)
        self.assertEqual(request.legal_company_id, self.client_a)
        self.assertEqual(matter.request_id, request)
        self.assertEqual(matter.requester_id, self.requester)
        self.assertEqual(matter.kind, "contract")
        self.assertEqual(matter.due_date, self.d("2031-02-01"))
        self.assertEqual(matter.attachment_ids.mapped("name"), ["draft-contract.pdf"])
        self.assertEqual(matter.attachment_ids.res_model, "legal.task")
        # The requester follows the matter's status without opening it.
        mine = request.with_user(self.requester)
        self.assertEqual(mine.matter_number, matter.task_number)
        self.assertEqual(mine.matter_state, matter.state)
        with self.assertRaises(AccessError):
            matter.with_user(self.requester).read(["name"])

    def test_return_and_resubmit(self):
        request = self.ask()
        with self.assertRaises(UserError):
            request.with_user(self.lawyer)._ldm_return(" ")
        action = request.with_user(self.lawyer).action_ldm_return()
        Wizard = self.env["legal.request.reason.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["request_id", "mode", "reason"])
        self.assertEqual(defaults["mode"], "return")
        Wizard.create({"reason": "Attach the signed draft"}).action_confirm()
        self.assertEqual(request.state, "returned")
        self.assertEqual(request.return_reason, "Attach the signed draft")
        request.write({"description": "Signed draft attached"})
        with self.assertRaises(AccessError):
            request.with_user(self.requester2).action_ldm_resubmit()
        request.action_ldm_resubmit()
        self.assertEqual(request.state, "new")
        self.assertFalse(request.return_reason)

    def test_decline_needs_a_reason(self):
        request = self.ask()
        action = request.with_user(self.lawyer).action_ldm_decline()
        Wizard = self.env["legal.request.reason.wizard"].with_user(self.lawyer).with_context(action["context"])
        with self.assertRaises(UserError):
            Wizard.create({"reason": " "}).action_confirm()
        Wizard.create({"reason": "A commercial decision, not a legal question"}).action_confirm()
        self.assertEqual(request.state, "rejected")
        with self.assertRaises(UserError):
            request.with_user(self.lawyer).action_ldm_accept()

    def test_send_result_to_requester(self):
        request = self.ask()
        matter = self.accept(request)
        memo = self.env["ir.attachment"].create({"name": "opinion.pdf", "datas": base64.b64encode(b"%PDF"),
                                                 "res_model": "legal.task", "res_id": matter.id})
        action = request.with_user(self.lawyer).action_ldm_send_result()
        Wizard = self.env["legal.request.result.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["request_id", "message"])
        wizard = Wizard.create({"attachment_ids": [(6, 0, memo.ids)]})
        self.assertIn(memo, wizard.available_attachment_ids)
        self.assertTrue(defaults["message"])
        wizard.action_send()
        sent = request.attachment_ids.filtered(lambda a: a.name == "opinion.pdf")
        self.assertEqual(sent.res_model, "legal.request")
        self.assertEqual(sent.with_user(self.requester).read(["name"])[0]["name"], "opinion.pdf")
        stranger = self.env["ir.attachment"].create({"name": "other.pdf", "datas": base64.b64encode(b"x"),
                                                     "res_model": "legal.company", "res_id": self.client_a.id})
        wizard = Wizard.create({"attachment_ids": [(6, 0, stranger.ids)]})
        with self.assertRaises(UserError):
            wizard.action_send()

    def test_request_type_maps_to_a_template(self):
        for kind, xmlid in (("opinion", "ldm_template_opinion"), ("dispute", "ldm_template_civil_lawsuit"),
                            ("government", "ldm_template_government")):
            request = self.ask(request_type=kind)
            self.assertEqual(request.with_user(self.lawyer)._ldm_default_template(), self.env.ref(f"{M}.{xmlid}"))
