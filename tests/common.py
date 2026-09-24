# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, new_test_user

M = "legal_department_management"


class LdmCase(TransactionCase):
    """Users for every role, one client per lawyer, a court and a government
    body, and the shipped matter types. Every stream's tests build on this."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # English on purpose: the assertions read English text, and the template
        # database's default language is Arabic now that the module ships ar.po.
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, mail_create_nolog=True,
                                       mail_notrack=True, no_reset_password=True, lang="en_US"))
        cls.company = cls.env.company
        cls.calendar = cls.env.ref(f"{M}.ldm_calendar_iraq")
        cls.company.ldm_calendar_id = cls.calendar
        Settings = cls.env["res.config.settings"]
        Settings._ldm_apply_preset("hybrid")

        def user(login, *groups):
            return new_test_user(cls.env, login=login, groups=",".join(("base.group_user",) + groups),
                                 name=login.replace("_", " ").title(), tz="Asia/Baghdad", lang="en_US")

        cls.clerk = user("ldm_clerk", f"{M}.group_ldm_clerk")
        cls.lawyer = user("ldm_lawyer", f"{M}.group_legal_user")
        cls.lawyer2 = user("ldm_lawyer2", f"{M}.group_legal_user")
        cls.approver = user("ldm_approver", f"{M}.group_ldm_approver")
        cls.manager = user("ldm_manager", f"{M}.group_legal_manager")
        cls.auditor = user("ldm_auditor", f"{M}.group_ldm_auditor")
        cls.billing = user("ldm_billing", f"{M}.group_ldm_billing_user")

        cls.council = cls.env["legal.ministry"].create({"name": "LDM Test Judicial Council", "body_kind": "judicial"})
        cls.court = cls.env["legal.department"].create({
            "name": "LDM Test First Instance Court", "ministry_id": cls.council.id, "body_kind": "court",
            "court_degree": "first_instance"})
        cls.ministry = cls.env["legal.ministry"].create({"name": "LDM Test Ministry of Trade"})
        cls.registry_body = cls.env["legal.department"].create({
            "name": "LDM Test Companies Registry", "ministry_id": cls.ministry.id})

        cls.client_a = cls.env["legal.company"].create({
            "name": "LDM Client A", "lawyer_id": cls.lawyer.id, "lawyer_ids": [(6, 0, [cls.lawyer.id])]})
        cls.client_b = cls.env["legal.company"].create({
            "name": "LDM Client B", "lawyer_id": cls.lawyer2.id, "lawyer_ids": [(6, 0, [cls.lawyer2.id])]})
        cls.t_government = cls.env.ref(f"{M}.ldm_template_government")
        cls.t_lawsuit = cls.env.ref(f"{M}.ldm_template_civil_lawsuit")

    @classmethod
    def make_matter(cls, client=None, lawyer=None, **vals):
        client = client or cls.client_a
        lawyer = lawyer or client.lawyer_id
        values = {"name": "Matter", "legal_company_id": client.id, "lawyer_id": lawyer.id,
                  "lawyer_ids": [(6, 0, [lawyer.id])]}
        values.update(vals)
        return cls.env["legal.task"].create(values)

    @staticmethod
    def d(text):
        return date.fromisoformat(text)
